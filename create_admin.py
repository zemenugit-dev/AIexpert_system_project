import sqlite3

# CONNECT TO REAL DATABASE FILE
conn = sqlite3.connect("database/app.db")

cur = conn.cursor()

# INSERT ADMIN
cur.execute("""
INSERT INTO users (name, email, password, role)
VALUES (?, ?, ?, ?)
""", ("John Doe", "admin@gmail.com", "Zed1929@!@!", "admin"))

conn.commit()
conn.close()

print("✅ User inserted successfully by admin!")