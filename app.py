
from flask import render_template, request, redirect, url_for
from database.database import get_connection
from werkzeug.security import generate_password_hash


from flask import Flask, render_template, request, redirect, session, url_for
from database.database import init_db, seed_questions, seed_treatments, get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from pyswip import Prolog
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from io import BytesIO
import os



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

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM diagnosis_history")
    total_diagnoses = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT disease) FROM diagnosis_history")
    total_diseases = cur.fetchone()[0]

    conn.close()

    return render_template(
        "admin/admin_dashboard.html",
        name=session["name"],
        total_users=total_users,
        total_diagnoses=total_diagnoses,
        total_diseases=total_diseases
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
        disease = results[0]["disease"]

    cur.execute("SELECT drug_name, advice FROM treatments WHERE disease=?", (disease,))
    t = cur.fetchone()

    drug = t["drug_name"] if t else "Not found"
    advice = t["advice"] if t else "No advice"

    cur.execute("""
        INSERT INTO diagnosis_history
        (user_id, disease, confidence, drug_name, advice)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, disease, 100, drug, advice))

    conn.commit()
    conn.close()

    return render_template("result.html",
        disease=disease,
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


@app.route('/admin/diseases')
def admin_diseases():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM diseases")
    diseases = cursor.fetchall()

    conn.close()

    return render_template("admin_diseases.html", diseases=diseases)


@app.route('/admin/create_user', methods=['GET', 'POST'])
def create_user():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        # 🔐 hash password (important)
        hashed_password = generate_password_hash(password)

        # 🗄️ connect DB
        conn = get_connection()
        cursor = conn.cursor()

        # 💾 insert user
        cursor.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (name, email, hashed_password, role))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_users'))

    return render_template('admin/create_users.html')
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
    app.run(debug=True)