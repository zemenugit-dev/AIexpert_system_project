import sqlite3
# If your Flask app uses Werkzeug for password hashing, uncomment the line below:
# from werkzeug.security import generate_password_hash

def seed_database():
    # Connect directly to your application's database file
    conn = sqlite3.connect('database/app.db')
    cursor = conn.cursor()

    # Create users (Make sure to hash the passwords if your app requires it)
    # Example: generate_password_hash("admin123")
    admin_password = "admin123" 
    user_password = "user123"

    sample_users = [
        ('Admin', 'admin@gmail.com', admin_password, 'Admin'),
        ('User', 'user@gmail.com', user_password, 'User')
    ]

    try:
        # Update the column names (email, password, role) to match your actual database schema
        cursor.executemany('''
            INSERT INTO users (name, email, password, role) 
            VALUES (?, ?, ?, ?)
        ''', sample_users)
        
        conn.commit()
        print("🎉 Success: Admin and User roles have been inserted!")
    except sqlite3.IntegrityError:
        print("⚠️ Note: Sample users might already exist in the database.")
    except sqlite3.OperationalError as e:
        print(f"❌ Error: Could not find or access the users table. Details: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_database()