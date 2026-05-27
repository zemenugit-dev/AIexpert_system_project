import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")


# =========================
# CONNECTION
# =========================
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# INIT DATABASE
# =========================
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # USERS TABLE
    cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

    # QUESTIONS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        symptom_key TEXT NOT NULL
    )
    """)

    # USER ANSWERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question_id INTEGER,
        answer TEXT
    )
    """)

    # =========================
    # DIAGNOSIS HISTORY (FIXED INDENTATION)
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS diagnosis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        disease TEXT,
        confidence INTEGER,
        drug_name TEXT,
        advice TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # TREATMENTS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        disease TEXT NOT NULL,
        drug_name TEXT,
        advice TEXT
    )
    """)
    # =========================
    # SEED DEFAULT USERS (ADMIN & USER)
    # =========================
    from werkzeug.security import generate_password_hash
    
    # Check if admin already exists
    cur.execute("SELECT COUNT(*) FROM users WHERE email='admin@example.com'")
    if cur.fetchone()[0] == 0:
        admin_pass = generate_password_hash("admin123")
        cur.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES ('System Admin', 'admin@example.com', ?, 'admin')
        """, (admin_pass,))
        
    # Check if standard user already exists    
    cur.execute("SELECT COUNT(*) FROM users WHERE email='user@example.com'")
    if cur.fetchone()[0] == 0:
        user_pass = generate_password_hash("user123")
        cur.execute("""
            INSERT INTO users (name, email, password, role)
            VALUES ('Sample User', 'user@example.com', ?, 'user')
        """, (user_pass,))
        
    print("✅ Sample Admin and User verified/inserted successfully")

    conn.commit()
    conn.close()


# =========================
# SEED QUESTIONS
# =========================
def seed_questions():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM questions")
    count = cur.fetchone()[0]

    if count == 0:
        cur.executemany("""
            INSERT INTO questions (question_text, symptom_key)
            VALUES (?, ?)
        """, [
            ("Do you have fever?", "fever"),
            ("Do you have chills?", "chills"),
            ("Do you have headache?", "headache"),
            ("Do you have cough?", "cough"),
            ("Do you feel tiredness?", "tiredness"),
            ("Do you have sore throat?", "sore_throat"),
            ("Do you have body pain?", "body_pain"),
            ("Do you have running nose?", "running_nose")
        ])

        print("✅ Questions inserted successfully")

    conn.commit()
    conn.close()


# =========================
# SEED TREATMENTS
# =========================
def seed_treatments():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM treatments")
    count = cur.fetchone()[0]

    if count == 0:
        cur.executemany("""
            INSERT INTO treatments (disease, drug_name, advice)
            VALUES (?, ?, ?)
        """, [
            ("malaria", "Artemether/Lumefantrine", "Take full dose and rest"),
            ("flu", "Paracetamol", "Drink fluids, rest, monitor fever"),
            ("covid19", "Paracetamol + Supportive care", "Isolate and monitor symptoms"),
            ("common_cold", "Antihistamines", "Rest and drink warm fluids")
        ])

        print("✅ Treatments inserted successfully")

    conn.commit()
    conn.close()