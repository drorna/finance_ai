from core.database import engine, Base
from core.models import Transaction

print("Creating transactions table...")
Base.metadata.create_all(bind=engine)
print("Done.")
