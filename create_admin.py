from database.database import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT * FROM questions")
print(cur.fetchall())

conn.close()