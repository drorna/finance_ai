import time
from core.database import get_db, engine, Base
from core.models import User, Portfolio, Signal
from quant.strategy import analyze_position, get_market_regime
from analyst.gemini_client import generate_daily_report
from notifier.mailer import send_daily_flash, send_weekly_deep_dive

def run_daily_cycle():
    print("Starting Daily Cycle...")
    db = next(get_db())
    
    # 1. Global Market Regime
    regime = get_market_regime()
    print(f"Market Regime: {regime}")
    
    users = db.query(User).all()
    
    for user in users:
        print(f"Processing User: {user.email}")
        portfolio = db.query(Portfolio).filter(Portfolio.user_id == user.id).all()
        
        daily_signals = []
        
        # 2. Analyze Portfolio
        for position in portfolio:
            signal_type, reason = analyze_position(position.symbol, position.quantity, position.avg_price)
            
            if signal_type != "HOLD":
                # Create Signal in DB
                new_signal = Signal(
                    user_id=user.id,
                    symbol=position.symbol,
                    signal_type=signal_type,
                    reason=reason
                )
                db.add(new_signal)
                daily_signals.append(new_signal)
                print(f"  -> Signal: {position.symbol} {signal_type}")
        
        db.commit()
        
        # 3. AI Analysis & Report
        # Only generating if there are signals or user requests it (simplified to always/smart logic)
        # For this scaler, let's say we send update if there are signals OR it's Friday (Weekly).
        # Assume today is daily run.
        
        if daily_signals:
            print("  -> Generating AI Report...")
            report = generate_daily_report(portfolio, daily_signals, regime)
            
            # 4. Notify
            print("  -> Sending Email...")
            send_daily_flash(user.email, report)
        else:
            print("  -> No significant changes, skipping report.")
            
    print("Daily Cycle Completed.")

if __name__ == "__main__":
    # Ensure tables exist
    # import models to register them with Base
    import core.models 
    Base.metadata.create_all(bind=engine)
    
    run_daily_cycle()
