import datetime
import time
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from core.models import Base
# from quant.policy_engine import optimize_portfolio_job # Future import?

class SchedulerService:
    """
    Manages automated background jobs.
    Policy: 'Bi-Weekly Deep Grind'
    """
    
    def __init__(self, db_url="sqlite:///finance_ai.db"):
        self.engine = create_engine(db_url)
    
    def check_optimization_due(self, ticker: str) -> bool:
        """
        Checks if the asset needs re-optimization (Last run > 14 days ago).
        """
        # For MVP, we might store this in a 'optimization_logs' table.
        # Here is a mock implementation:
        try:
           with self.engine.connect() as conn:
               # Create table if not exists (Mock)
               conn.execute(text('''
                   CREATE TABLE IF NOT EXISTS optimization_schedule (
                       ticker TEXT PRIMARY KEY,
                       last_run_date TIMESTAMP
                   )
               '''))
               
               result = conn.execute(text(
                   "SELECT last_run_date FROM optimization_schedule WHERE ticker = :ticker"
               ), {"ticker": ticker}).fetchone()
               
               if not result:
                   return True # Never run
                   
               last_run = datetime.datetime.strptime(str(result[0]), '%Y-%m-%d %H:%M:%S.%f')
               delta = datetime.datetime.now() - last_run
               
               return delta.days >= 14
               
        except Exception as e:
            print(f"Scheduler DB Error: {e}")
            return True # Fail-safe: Optimize if weird error
            
    def mark_optimization_complete(self, ticker: str):
        with self.engine.connect() as conn:
             conn.execute(text('''
                INSERT OR REPLACE INTO optimization_schedule (ticker, last_run_date)
                VALUES (:ticker, :date)
             '''), {"ticker": ticker, "date": datetime.datetime.now()})
             conn.commit()

    def run_scheduler_loop(self):
        """
        The heartbeat function. To be called by cron or async worker.
        """
        print("⏰ Scheduler: Checking portfolio status...")
        # In a real app, fetch all tickers from DB
        # tickers = get_all_tickers()
        # for t in tickers: ...
        pass

if __name__ == "__main__":
    scheduler = SchedulerService()
    print("Optimization needed for TSLA?", scheduler.check_optimization_due("TSLA"))
    scheduler.mark_optimization_complete("TSLA")
    print("Optimization needed for TSLA (after mark)?", scheduler.check_optimization_due("TSLA"))
