import sqlite3

def migrate():
    import os
    db_path = os.path.join(os.path.dirname(__file__), "finance_ai.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add cash_balance column to users table
        cursor.execute("ALTER TABLE users ADD COLUMN cash_balance FLOAT DEFAULT 100000.0")
        print("Added cash_balance column to users table.")
    except Exception as e:
        print(f"Migration error (might already exist): {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
