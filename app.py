
from flask import Flask, render_template, request, redirect, session, url_for, make_response
from database.database import init_db, seed_questions, seed_treatments, get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from pyswip import Prolog
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from io import BytesIO
import os
import pandas as pd



# =========================
# APP
# =========================
app = Flask(__name__)
app.secret_key = "medical_ai_secret"

# =========================
# DB INIT
# =========================
init_db()
seed_questions()
seed_treatments()

# =========================
# PROLOG
# =========================
prolog = Prolog()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
rules_path = os.path.join(BASE_DIR, "prolog_engine", "rules.pl")
prolog.consult(rules_path)

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
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin/dashboard")
            else:
                return redirect("/dashboard")

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

# =========================
# ADMIN DASHBOARD
# =========================
@app.route("/admin/dashboard")
def admin_dashboard():

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    # =========================
    # BASIC STATS
    # =========================
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM diagnosis_history")
    total_diagnoses = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT disease) FROM diagnosis_history")
    total_diseases = cur.fetchone()[0]

    # =========================
    # CHART 1: DISEASE FREQUENCY
    # =========================
    cur.execute("""
        SELECT disease, COUNT(*) as count
        FROM diagnosis_history
        GROUP BY disease
        ORDER BY count DESC
        LIMIT 5
    """)
    disease_data = cur.fetchall()

    # =========================
    # CHART 2: DAILY DIAGNOSIS TREND
    # =========================
    cur.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM diagnosis_history
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 7
    """)
    trend_data = cur.fetchall()

    conn.close()

    return render_template(
        "admin/admin_dashboard.html",
        name=session["name"],
        total_users=total_users,
        total_diagnoses=total_diagnoses,
        total_diseases=total_diseases,
        disease_data=disease_data,
        trend_data=trend_data
    )
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
# DIAGNOSIS ENGINE (FIXED)
# =========================
@app.route("/submit_answers", methods=["POST"])
def submit_answers():

    if not is_logged_in():
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_connection()
    cur = conn.cursor()

    list(prolog.query("retractall(symptom(_))"))

    symptoms_list = []

    cur.execute("SELECT * FROM questions")
    questions = cur.fetchall()

    for q in questions:
        answer = request.form.get(f"q{q['id']}")

        if answer == "yes":
            symptom = q["symptom_key"]
            symptoms_list.append(symptom)
            prolog.assertz(f"symptom('{symptom}')")

    disease_list = ["malaria", "flu", "covid19", "common_cold"]

    results = []

    for d in disease_list:
        try:
            q = list(prolog.query(f"disease_score({d}, Score)"))
            if q:
                score = int(q[0]["Score"])
                results.append({"disease": d, "score": score})
        except:
            continue

    disease = "Unknown"

    if results:
        results.sort(key=lambda x: x["score"], reverse=True)
        # Ensure the string is normalized to lowercase to match the seeded treatments table
        disease = results[0]["disease"].lower().strip()

    # 💡 FIX: Query using the strictly lowercase disease name
    cur.execute("SELECT drug_name, advice FROM treatments WHERE LOWER(disease)=?", (disease,))
    t = cur.fetchone()

    # Capitalize the disease name for a beautiful UI display (e.g., 'malaria' -> 'Malaria')
    display_disease = disease.capitalize() if disease != "Unknown" else "Unknown"

    drug = t["drug_name"] if t else "Not found"
    advice = t["advice"] if t else "No advice"

    cur.execute("""
        INSERT INTO diagnosis_history
        (user_id, disease, confidence, drug_name, advice)
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
# HISTORY
# =========================
@app.route("/history")
def history():

    if not is_logged_in():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM diagnosis_history
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],))

    history = cur.fetchall()
    conn.close()

    return render_template("history.html", history=history)

# =========================
# ADMIN USERS (FULL FIXED CRUD)
# =========================
@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    # ======================
    # CREATE USER (POST)
    # ======================
    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password_raw = request.form.get("password")

        # safety check
        if not name or not email or not password_raw:
            return redirect("/admin/users?error=empty")

        # duplicate check
        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        if cur.fetchone():
            return redirect("/admin/users?error=email_exists")

        password = generate_password_hash(password_raw)

        cur.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, 'user')
        """, (name, email, password))

        conn.commit()
        return redirect("/admin/users?success=1")

    # ======================
    # LOAD USERS (GET)
    # ======================
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()

    conn.close()

    return render_template("admin/users.html", users=users)
# DELETE USER
# =========================
@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/admin/users")

# =========================
# EDIT USER
# =========================
@app.route("/admin/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    # ======================
    # UPDATE USER (POST)
    # ======================
    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()

        cur.execute("""
            UPDATE users
            SET name=?, email=?
            WHERE id=?
        """, (name, email, user_id))

        conn.commit()
        conn.close()

        return redirect("/admin/users")

    # ======================
    # LOAD USER (GET)
    # ======================
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()

    conn.close()

    if not user:
        return "User not found"

    return render_template("admin/edit_user.html", user=user)

# =========================
# DOWNLOAD PDF
# =========================
@app.route("/download_report/<int:history_id>")
def download_report(history_id):

    if not is_logged_in():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM diagnosis_history
        WHERE id=? AND user_id=?
    """, (history_id, session["user_id"]))

    report = cur.fetchone()
    conn.close()

    if not report:
        return "Not found"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    elements = [
        Paragraph("Medical Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Disease: {report['disease']}", styles["BodyText"]),
        Paragraph(f"Advice: {report['advice']}", styles["BodyText"]),
    ]

    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=report.pdf"

    return response





@app.route('/admin/create_user', methods=['GET', 'POST'])
def create_user():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        #  hash password (important)
        hashed_password = generate_password_hash(password)

        # connect DB
        conn = get_connection()
        cursor = conn.cursor()

        #  insert user
        cursor.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (name, email, hashed_password, role))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_users'))

    return render_template('admin/create_users.html')
#add routes for editing and deleting questions here (similar to above)

# =========================
# ADMIN QUESTIONS
# =========================

@app.route("/admin/questions")
def admin_questions():

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM questions")
    questions = cur.fetchall()

    conn.close()

    return render_template(
        "admin/questions.html",
        questions=questions
    )


# =========================
# ADD QUESTION
# =========================
@app.route("/admin/add_question", methods=["GET", "POST"])
def add_question():

    if not is_admin():
        return redirect("/login")

    if request.method == "POST":

        question_text = request.form["question_text"]
        symptom_key = request.form["symptom_key"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO questions
            (question_text, symptom_key)
            VALUES (?, ?)
        """, (question_text, symptom_key))

        conn.commit()
        conn.close()

        return redirect("/admin/questions")

    return render_template("admin/add_question.html")


# =========================
# EDIT QUESTION
# =========================
@app.route("/admin/edit_question/<int:id>", methods=["GET", "POST"])
def edit_question(id):

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":

        question_text = request.form["question_text"]
        symptom_key = request.form["symptom_key"]

        cur.execute("""
            UPDATE questions
            SET question_text=?, symptom_key=?
            WHERE id=?
        """, (question_text, symptom_key, id))

        conn.commit()
        conn.close()

        return redirect("/admin/questions")

    cur.execute("SELECT * FROM questions WHERE id=?", (id,))
    question = cur.fetchone()

    conn.close()

    return render_template(
        "admin/edit_question.html",
        question=question
    )


# =========================
# DELETE QUESTION
# =========================
@app.route("/admin/delete_question/<int:id>")
def delete_question(id):

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM questions WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin/questions")


# =========================
# ADMIN DISEASES
# =========================
@app.route("/admin/diseases")
def admin_diseases():

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM treatments")
    diseases = cur.fetchall()

    conn.close()

    return render_template(
        "admin/diseases.html",
        diseases=diseases
    )
    
    # =========================
# ADD DISEASE
# =========================
@app.route("/admin/add_disease", methods=["GET", "POST"])
def add_disease():

    if not is_admin():
        return redirect("/login")

    if request.method == "POST":

        disease = request.form["disease"]
        drug_name = request.form["drug_name"]
        advice = request.form["advice"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO treatments
            (disease, drug_name, advice)
            VALUES (?, ?, ?)
        """, (disease, drug_name, advice))

        conn.commit()
        conn.close()

        return redirect("/admin/diseases")

    return render_template("admin/add_disease.html")

# =========================
# EDIT DISEASE
# =========================
@app.route("/admin/edit_disease/<int:id>", methods=["GET", "POST"])
def edit_disease(id):

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":

        disease = request.form["disease"]
        drug_name = request.form["drug_name"]
        advice = request.form["advice"]

        cur.execute("""
            UPDATE treatments
            SET disease=?,
                drug_name=?,
                advice=?
            WHERE id=?
        """, (disease, drug_name, advice, id))

        conn.commit()
        conn.close()

        return redirect("/admin/diseases")

    cur.execute("SELECT * FROM treatments WHERE id=?", (id,))
    disease = cur.fetchone()

    conn.close()

    return render_template(
        "admin/edit_disease.html",
        disease=disease
    )
    
    
    # =========================
# DELETE DISEASE
# =========================
@app.route("/admin/delete_disease/<int:id>")
def delete_disease(id):

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM treatments WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin/diseases")



# =========================
# ADMIN REPORTS
# =========================
@app.route("/admin/reports")
def admin_reports():

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT dh.id,
               u.name AS user_name,
               dh.disease,
               dh.confidence,
               dh.drug_name,
               dh.advice,
               dh.created_at
        FROM diagnosis_history dh
        JOIN users u ON dh.user_id = u.id
        ORDER BY dh.created_at DESC
    """)

    reports = cur.fetchall()
    conn.close()

    return render_template("admin/reports.html", reports=reports)



@app.route("/admin/export_all_reports_pdf")
def export_all_reports_pdf():

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT dh.id,
               u.name AS user_name,
               dh.disease,
               dh.confidence,
               dh.drug_name,
               dh.advice,
               dh.created_at
        FROM diagnosis_history dh
        JOIN users u ON dh.user_id = u.id
        ORDER BY dh.created_at DESC
    """)

    reports = cur.fetchall()
    conn.close()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()

    elements = []

    # TITLE
    elements.append(Paragraph("ALL DIAGNOSIS REPORTS", styles["Title"]))
    elements.append(Spacer(1, 12))

    # =========================
    # TABLE DATA
    # =========================
    table_data = []

    # HEADER ROW
    table_data.append([
        "ID",
        "User",
        "Disease",
        "Confidence",
        "Drug",
        "Advice",
        "Date"
    ])

    # DATA ROWS
    for r in reports:
        table_data.append([
            str(r["id"]),
            r["user_name"],
            r["disease"],
            str(r["confidence"]) + "%",
            r["drug_name"],
            r["advice"],
            str(r["created_at"])
        ])

    # TABLE STYLE
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b7cff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("ALIGN", (0, 0), (-1, -1), "CENTER"),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),

        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
    ]))

    elements.append(table)

    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=all_reports_table.pdf"

    return response

@app.route("/admin/export_reports_csv")
def export_reports_csv():

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT dh.id,
               u.name AS user_name,
               dh.disease,
               dh.confidence,
               dh.drug_name,
               dh.advice,
               dh.created_at
        FROM diagnosis_history dh
        JOIN users u ON dh.user_id = u.id
        ORDER BY dh.created_at DESC
    """)

    rows = cur.fetchall()
    conn.close()

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    # Convert to CSV string
    csv_data = df.to_csv(index=False)

    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=diagnosis_reports.csv"
    response.headers["Content-Type"] = "text/csv"

    return response

@app.route("/admin/export_report_pdf/<int:report_id>")
def export_report_pdf(report_id):

    if not is_admin():
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT dh.*, u.name AS user_name
        FROM diagnosis_history dh
        JOIN users u ON dh.user_id = u.id
        WHERE dh.id=?
    """, (report_id,))

    report = cur.fetchone()
    conn.close()

    if not report:
        return "Report not found"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()

    content = [
        Paragraph("AI Medical Diagnosis Report", styles["Title"]),
        Spacer(1, 12),

        Paragraph(f"User: {report['user_name']}", styles["Normal"]),
        Paragraph(f"Disease: {report['disease']}", styles["Normal"]),
        Paragraph(f"Confidence: {report['confidence']}%", styles["Normal"]),
        Paragraph(f"Drug: {report['drug_name']}", styles["Normal"]),
        Paragraph(f"Advice: {report['advice']}", styles["Normal"]),
        Paragraph(f"Date: {report['created_at']}", styles["Normal"]),
    ]

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
# RUN
# =========================
if __name__ == "__main__":
    import os
    # Render provides the port dynamically via an environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)