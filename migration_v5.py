import sqlite3

def migrate():
    import os
    db_path = os.path.join(os.path.dirname(__file__), "finance_ai.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column needs renaming (SQLite doesn't support RENAME COLUMN in older versions easily, but let's try or add new)
        # Check if 'transaction_type' exists using PRAGMA
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'type' in columns and 'transaction_type' not in columns:
            print("Renaming column 'type' to 'transaction_type'...")
            cursor.execute("ALTER TABLE transactions RENAME COLUMN type TO transaction_type")
        elif 'transaction_type' not in columns:
            print("Adding transaction_type column...")
            cursor.execute("ALTER TABLE transactions ADD COLUMN transaction_type VARCHAR")
            
    except Exception as e:
        print(f"Migration error: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
