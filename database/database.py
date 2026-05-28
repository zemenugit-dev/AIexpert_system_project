import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

def init_db():
    # ?? FORCE RESET: Render ?? ???? ???? ?? ??? ????? ?? ??? ????? ?????
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print('Old database file cleared successfully.')
        except Exception as e:
            print(f'Warning: Could not remove old DB file: {e}')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. USERS TABLE
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # 2. QUESTIONS TABLE
    cur.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        symptom_key TEXT NOT NULL
    )''')

    # 3. TREATMENTS TABLE
    cur.execute('''
    CREATE TABLE IF NOT EXISTS treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        disease TEXT NOT NULL,
        drug_name TEXT,
        advice TEXT
    )''')

    # 4. DIAGNOSIS_HISTORY TABLE
    cur.execute('''
    CREATE TABLE IF NOT EXISTS diagnosis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        disease TEXT,
        confidence INTEGER,
        drug_name TEXT,
        advice TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # ?? 100% FIXED PASSWORD HASHES FOR RENDER
    admin_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
    user_hash = generate_password_hash('user123', method='pbkdf2:sha256')

    cur.execute('INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)', ('System Admin', 'admin@example.com', admin_hash, 'admin'))
    cur.execute('INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)', ('Sample User', 'user@example.com', user_hash, 'user'))

    # Default Questions & Treatments
    questions_data = [('Do you have a high fever?', 'fever'), ('Are you experiencing severe chills and shaking?', 'chills'), ('Do you have a headache?', 'headache'), ('Are you experiencing muscle pain or fatigue?', 'muscle_pain'), ('Do you have a persistent cough?', 'cough'), ('Are you experiencing a loss of taste or smell?', 'loss_of_taste'), ('Do you have a sore throat?', 'sore_throat'), ('Do you have a runny or stuffy nose?', 'runny_nose')]
    for q_text, s_key in questions_data: cur.execute('INSERT INTO questions (question_text, symptom_key) VALUES (?, ?)', (q_text, s_key))

    treatments_data = [('malaria', 'Artemether-Lumefantrine (Coartem)', 'Take with fatty food. Complete full course.'), ('flu', 'Oseltamivir (Tamiflu)', 'Rest and hydration.'), ('covid19', 'Paxlovid / Rest', 'Isolate and monitor oxygen.'), ('common_cold', 'Antihistamines', 'Stay warm and rest.')]
    for dis, drug, adv in treatments_data: cur.execute('INSERT INTO treatments (disease, drug_name, advice) VALUES (?, ?, ?)', (dis, drug, adv))

    conn.commit()
    conn.close()

def get_connection():
    import sqlite3, os
    DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
