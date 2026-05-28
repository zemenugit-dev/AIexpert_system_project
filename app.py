from flask import Flask, render_template, request, redirect, session, url_for, make_response
from database.database import init_db, get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from io import BytesIO
import os
import pandas as pd

# =========================
# APP CONFIG
# =========================
app = Flask(__name__)
app.secret_key = "medical_ai_secret"

# Initialize database seamlessly
init_db()

# =========================
# HELPERS
# =========================
def is_admin():
    return session.get("role") == "admin"

def is_logged_in():
    return "user_id" in session

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return render_template("index.html")

# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password_raw = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        if cur.fetchone():
            return render_template("register.html", error="Email already exists")

        password = generate_password_hash(password_raw)
        cur.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, 'user')
        """, (name, email, password))

        conn.commit()
        conn.close()
        return redirect("/login")

    return render_template("register.html")

# =========================
# LOGIN (FIXED HASH & CASE)
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        # 💡 የኬዝ ስሜትን ለመከላከል LOWER() ተጠቅመናል
        cur.execute("SELECT * FROM users WHERE LOWER(email)=?", (email,))
        user = cur.fetchone()
        conn.close()

        # 💡 ደህንነቱ በተጠበቀ ሁኔታ ሀሹን እና ፓስወርዱን ማመሳከር
        if user and check_password_hash(user["password"], password):
            session["user_id"] = int(user["id"])
            session["name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin/dashboard")
            else:
                return redirect("/dashboard")

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

# =========================
# USER DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect("/login")
    if is_admin():
        return redirect("/admin/dashboard")
    return render_template("dashboard.html", name=session["name"])

# =========================
# QUESTIONS (USER)
# =========================
@app.route("/questions")
def questions():
    if not is_logged_in():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions")
    questions = cur.fetchall()
    conn.close()

    return render_template("questions.html", questions=questions)

# =========================
# DIAGNOSIS ENGINE
# =========================
@app.route("/submit_answers", methods=["POST"])
def submit_answers():
    if not is_logged_in():
        return redirect("/login")
    
    user_id = int(session["user_id"])
    conn = get_connection()
    cur = conn.cursor()
    
    symptoms_list = []
    cur.execute("SELECT * FROM questions")
    questions = cur.fetchall()
    
    for q in questions:
        answer = request.form.get(f"q{q['id']}")
        if answer and answer.strip().lower() == "yes":
            symptoms_list.append(q["symptom_key"])
            
    scores = {"malaria": 0, "flu": 0, "covid19": 0, "common_cold": 0}
    
    for sym in ["fever", "chills", "headache", "muscle_pain"]:
        if sym in symptoms_list: scores["malaria"] += 1
    for sym in ["fever", "headache", "cough", "sore_throat", "runny_nose"]:
        if sym in symptoms_list: scores["flu"] += 1
    for sym in ["fever", "cough", "loss_of_taste", "sore_throat"]:
        if sym in symptoms_list: scores["covid19"] += 1
    for sym in ["cough", "sore_throat", "runny_nose"]:
        if sym in symptoms_list: scores["common_cold"] += 1
        
    detected_disease = "unknown"
    highest_score = 0
    
    for disease, score in scores.items():
        if score > highest_score:
            highest_score = score
            detected_disease = disease

    cur.execute("SELECT drug_name, advice FROM treatments WHERE LOWER(disease)=?", (detected_disease,))
    t = cur.fetchone()
    
    display_disease = detected_disease.capitalize() if detected_disease != "unknown" else "Unknown"
    drug = t["drug_name"] if t else "Not found"
    advice = t["advice"] if t else "No advice"
    
    cur.execute("""
        INSERT INTO diagnosis_history (user_id, disease, confidence, drug_name, advice)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, display_disease, 100, drug, advice))
    
    conn.commit()
    conn.close()
    
    return render_template("result.html",
        disease=display_disease,
        drug=drug,
        advice=advice,
        symptoms=symptoms_list
    )

# =========================
# HISTORY (🎯 FIXED: SHOWS EXACT USER HISTORY ONLY)
# =========================
@app.route("/history")
def history():
    if not is_logged_in():
        return redirect("/login")

    current_user_id = int(session["user_id"])
    conn = get_connection()
    cur = conn.cursor()
    
    # 💡 እዚህ ጋር የገባውን ሰው (current_user_id) ታሪክ ብቻ እንዲያወጣ ገድበነዋል!
    cur.execute("""
        SELECT * FROM diagnosis_history
        WHERE CAST(user_id AS INTEGER) = ?
        ORDER BY created_at DESC
    """, (current_user_id,))
    history = cur.fetchall()
    conn.close()

    return render_template("history.html", history=history)

# =========================
# ADMIN DASHBOARD & CRUD
# =========================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not is_admin(): return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM diagnosis_history")
    total_diagnoses = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT disease) FROM diagnosis_history")
    total_diseases = cur.fetchone()[0]
    cur.execute("SELECT disease, COUNT(*) as count FROM diagnosis_history GROUP BY disease ORDER BY count DESC LIMIT 5")
    disease_data = cur.fetchall()
    cur.execute("SELECT DATE(created_at) as date, COUNT(*) as count FROM diagnosis_history GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 7")
    trend_data = cur.fetchall()
    conn.close()

    return render_template("admin/admin_dashboard.html", name=session["name"], total_users=total_users, total_diagnoses=total_diagnoses, total_diseases=total_diseases, disease_data=disease_data, trend_data=trend_data)

@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password_raw = request.form.get("password")
        if name and email and password_raw:
            cur.execute("SELECT id FROM users WHERE email=?", (email,))
            if not cur.fetchone():
                password = generate_password_hash(password_raw)
                cur.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'user')", (name, email, password))
                conn.commit()
        return redirect("/admin/users")

    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    conn.close()
    return render_template("admin/users.html", users=users)

@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect("/admin/users")

@app.route("/admin/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        cur.execute("UPDATE users SET name=?, email=? WHERE id=?", (name, email, user_id))
        conn.commit()
        conn.close()
        return redirect("/admin/users")

    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return render_template("admin/edit_user.html", user=user)

@app.route('/admin/create_user', methods=['GET', 'POST'])
def create_user():
    if not is_admin(): return redirect("/login")
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", (name, email, hashed_password, role))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))
    return render_template('admin/create_users.html')

@app.route("/admin/questions")
def admin_questions():
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions")
    questions = cur.fetchall()
    conn.close()
    return render_template("admin/questions.html", questions=questions)

@app.route("/admin/add_question", methods=["GET", "POST"])
def add_question():
    if not is_admin(): return redirect("/login")
    if request.method == "POST":
        question_text = request.form["question_text"]
        symptom_key = request.form["symptom_key"]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO questions (question_text, symptom_key) VALUES (?, ?)", (question_text, symptom_key))
        conn.commit()
        conn.close()
        return redirect("/admin/questions")
    return render_template("admin/add_question.html")

@app.route("/admin/edit_question/<int:id>", methods=["GET", "POST"])
def edit_question(id):
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        question_text = request.form["question_text"]
        symptom_key = request.form["symptom_key"]
        cur.execute("UPDATE questions SET question_text=?, symptom_key=? WHERE id=?", (question_text, symptom_key, id))
        conn.commit()
        conn.close()
        return redirect("/admin/questions")
    cur.execute("SELECT * FROM questions WHERE id=?", (id,))
    question = cur.fetchone()
    conn.close()
    return render_template("admin/edit_question.html", question=question)

@app.route("/admin/delete_question/<int:id>")
def delete_question(id):
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/admin/questions")

@app.route("/admin/diseases")
def admin_diseases():
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM treatments")
    diseases = cur.fetchall()
    conn.close()
    return render_template("admin/diseases.html", diseases=diseases)
        
@app.route("/admin/add_disease", methods=["GET", "POST"])
def add_disease():
    if not is_admin(): return redirect("/login")
    if request.method == "POST":
        disease = request.form["disease"]
        drug_name = request.form["drug_name"]
        advice = request.form["advice"]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO treatments (disease, drug_name, advice) VALUES (?, ?, ?)", (disease, drug_name, advice))
        conn.commit()
        conn.close()
        return redirect("/admin/diseases")
    return render_template("admin/add_disease.html")

@app.route("/admin/edit_disease/<int:id>", methods=["GET", "POST"])
def edit_disease(id):
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    if request.method == "POST":
        disease = request.form["disease"]
        drug_name = request.form["drug_name"]
        advice = request.form["advice"]
        cur.execute("UPDATE treatments SET disease=?, drug_name=?, advice=? WHERE id=?", (disease, drug_name, advice, id))
        conn.commit()
        conn.close()
        return redirect("/admin/diseases")
    cur.execute("SELECT * FROM treatments WHERE id=?", (id,))
    disease = cur.fetchone()
    conn.close()
    return render_template("admin/edit_disease.html", disease=disease)
    
@app.route("/admin/delete_disease/<int:id>")
def delete_disease(id):
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM treatments WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/admin/diseases")

@app.route("/admin/reports")
def admin_reports():
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT dh.id, u.name AS user_name, dh.disease, dh.confidence, dh.drug_name, dh.advice, dh.created_at FROM diagnosis_history dh JOIN users u ON dh.user_id = u.id ORDER BY dh.created_at DESC")
    reports = cur.fetchall()
    conn.close()
    return render_template("admin/reports.html", reports=reports)

# =========================
# REPORTS DOWNLOAD (PDF & CSV)
# =========================
@app.route("/download_report/<int:history_id>")
def download_report(history_id):
    if not is_logged_in(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM diagnosis_history WHERE id=? AND user_id=?", (history_id, session["user_id"]))
    report = cur.fetchone()
    conn.close()
    if not report: return "Not found"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Medical Report", styles["Title"]), Spacer(1, 12), Paragraph(f"Disease: {report['disease']}", styles["BodyText"]), Paragraph(f"Advice: {report['advice']}", styles["BodyText"])]
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename=report_{history_id}.pdf"
    return response

@app.route("/admin/export_all_reports_pdf")
def export_all_reports_pdf():
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT dh.id, u.name AS user_name, dh.disease, dh.confidence, dh.drug_name, dh.advice, dh.created_at FROM diagnosis_history dh JOIN users u ON dh.user_id = u.id ORDER BY dh.created_at DESC")
    reports = cur.fetchall()
    conn.close()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph("ALL DIAGNOSIS REPORTS", styles["Title"]), Spacer(1, 12)]
    table_data = [["ID", "User", "Disease", "Confidence", "Drug", "Advice", "Date"]]
    for r in reports:
        table_data.append([str(r["id"]), r["user_name"], r["disease"], f"{r['confidence']}%", r["drug_name"], r["advice"], str(r["created_at"])])
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    table = Table(table_data)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b7cff")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    elements.append(table)
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=all_reports.pdf"
    return response

@app.route("/admin/export_reports_csv")
def export_reports_csv():
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT dh.id, u.name AS user_name, dh.disease, dh.confidence, dh.drug_name, dh.advice, dh.created_at FROM diagnosis_history dh JOIN users u ON dh.user_id = u.id ORDER BY dh.created_at DESC")
    rows = cur.fetchall()
    conn.close()
    df = pd.DataFrame(rows)
    csv_data = df.to_csv(index=False)
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=diagnosis_reports.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

@app.route("/admin/export_report_pdf/<int:report_id>")
def export_report_pdf(report_id):
    if not is_admin(): return redirect("/login")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT dh.*, u.name AS user_name FROM diagnosis_history dh JOIN users u ON dh.user_id = u.id WHERE dh.id=?", (report_id,))
    report = cur.fetchone()
    conn.close()
    if not report: return "Report not found"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    content = [Paragraph("AI Medical Diagnosis Report", styles["Title"]), Spacer(1, 12), Paragraph(f"User: {report['user_name']}", styles["Normal"]), Paragraph(f"Disease: {report['disease']}", styles["Normal"]), Paragraph(f"Confidence: {report['confidence']}%", styles["Normal"]), Paragraph(f"Drug: {report['drug_name']}", styles["Normal"]), Paragraph(f"Advice: {report['advice']}", styles["Normal"]), Paragraph(f"Date: {report['created_at']}", styles["Normal"])]
    doc.build(content)
    pdf = buffer.getvalue()
    buffer.close()
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=report.pdf"
    return response

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)