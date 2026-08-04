import sqlite3
import hashlib

DB_NAME = "users.db"

def init_sqlite_db():
    """Initializes the local SQLite user table and seeds default accounts."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # Seed default admin & analyst accounts (SHA-256 hashed passwords)
    default_users = [
        ("admin_officer", hashlib.sha256("AdminSecret123!".encode()).hexdigest(), "ADMIN"),
        ("analyst_mira", hashlib.sha256("AnalystPass123!".encode()).hexdigest(), "ANALYST")
    ]
    
    for username, p_hash, role in default_users:
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
        """, (username, p_hash, role))
        
    conn.commit()
    conn.close()
    print("🗄️ [Database] SQLite User Database Initialized.")

def verify_user_credentials(username, password):
    """Verifies username and hashed password against SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    p_hash = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute("SELECT username, role FROM users WHERE username = ? AND password_hash = ?", (username, p_hash))
    user = cursor.fetchone()
    
    conn.close()
    if user:
        return {"username": user[0], "role": user[1]}
    return None

if __name__ == "__main__":
    init_sqlite_db()