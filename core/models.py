from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String)
    gemini_api_key = Column(String, nullable=True)  # User specific API key override
    cash_balance = Column(Float, default=100000.0)

    portfolio = relationship("Portfolio", back_populates="owner")
    signals = relationship("Signal", back_populates="owner")
    transactions = relationship("Transaction", back_populates="owner")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, index=True)
    transaction_type = Column(String) # BUY, SELL, DEPOSIT, WITHDRAWAL
    quantity = Column(Float)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    profit_loss = Column(Float, nullable=True) # Only for sells

    owner = relationship("User", back_populates="transactions")


class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    purchase_date = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="portfolio")

class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    signal_type = Column(String, nullable=False)  # BUY / SELL / HOLD
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="signals")
