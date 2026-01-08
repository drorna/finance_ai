from core.database import engine
from sqlalchemy import text

def migrate_v2():
    print("Migrating database v2: Adding purchase_date column...")
    with engine.connect() as conn:
        try:
            # Check if column exists to avoid error (basic check, simplified for this env)
            conn.execute(text("ALTER TABLE portfolio ADD COLUMN purchase_date DATETIME"))
            print("Column 'purchase_date' added successfully.")
        except Exception as e:
            if "duplicate column" in str(e) or "no such column" not in str(e): # SQLite might throw generic OperationalError
                 print(f"Migration note: {e}")
            else:
                 print(f"Migration failed: {e}")
    
if __name__ == "__main__":
    migrate_v2()
