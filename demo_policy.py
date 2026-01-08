import pandas as pd
import numpy as np
from quant.policy_engine import PolicyBacktester

def run_demo():
    # 1. Create a "Drama" Scenario
    # Price: 100 -> 90 (Dip) -> 85 (Deep Dip) -> 105 (Recovery) -> 120 (Rocket)
    dates = pd.date_range("2024-01-01", periods=6)
    prices = [100, 95, 90, 85, 105, 120]
    
    df = pd.DataFrame({
        "Close": prices,
        "Open": prices, # Simplified
        "High": prices,
        "Low": prices,
        "Volume": 1000
    }, index=dates)

    print("\n🎥 SCENARIO: The Rollercoaster")
    print(df['Close'])
    print("\n" + "="*50)
    
    # Initialize Engine
    engine = PolicyBacktester("DEMO", df)
    
    # Define Policy:
    # Scale In: Buy 30% more shares every time price drops 5% from avg cost
    # Scale Out: Sell 50% shares every time price rises 10% above avg cost
    
    engine.simulate_policy_debug(
        closes=engine.closes,
        dates=engine.dates,
        initial_cash=10000.0,
        scale_out_trigger=0.10, # +10%
        scale_out_amt=0.50,     # Sell half
        scale_in_trigger=0.05,  # -5%
        scale_in_amt=0.30,      # Buy with 30% cash
        max_drawdown_limit=0.50 # Stop loss 50%
    )

if __name__ == "__main__":
    run_demo()
