import bcrypt
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base

# הגדרת בסיס הנתונים
Base = declarative_base()
engine = create_engine('sqlite:///finance.db')

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password_hash = Column(String)

# יצירת הטבלה
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# יצירת משתמש
print("Creating Admin User...")
email = "admin@test.com"
raw_pass = "123456"
hashed = bcrypt.hashpw(raw_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

try:
    user = User(email=email, password_hash=hashed)
    session.add(user)
    session.commit()
    print(f"SUCCESS! User created: {email} / Password: {raw_pass}")
except Exception as e:
    print("User already exists or error:", e)