import pandas as pd
import numpy as np
import time
from quant.policy_engine import PolicyBacktester

def test_full_grind():
    # 1. Generate Synthetic Volatile Data (Good for active management)
    np.random.seed(42)
    days = 1000
    dates = pd.date_range("2020-01-01", periods=days)
    
    # Create a "Wave" pattern: Up, Down, Up, Crash, Rocket
    x = np.linspace(0, 100, days)
    trend = x * 0.5 
    wave = np.sin(x * 0.2) * 50
    noise = np.random.normal(0, 2, days)
    
    prices = 100 + trend + wave + noise
    # Ensure no negative prices
    prices = np.maximum(prices, 10)
    
    df = pd.DataFrame({
        "Close": prices,
        "Open": prices,
        "High": prices * 1.01,
        "Low": prices * 0.99,
        "Volume": 1000
    }, index=dates)
    
    print("\n--- 🧪 STARTING FULL OPTIMIZATION TEST ---")
    print(f"Data: {days} days of volatile price action.")
    
    engine = PolicyBacktester("SYNTHETIC_TEST", df)
    
    start_t = time.time()
    result = engine.run_exhaustive_optimization()
    duration = time.time() - start_t
    
    print("\n" + "="*60)
    print(f"✅ DONE! Checked {result['total_calculated']} strategies in {duration:.2f} seconds.")
    print(f"🚀 Speed: {result['total_calculated']/duration:.0f} strats/sec")
    print("="*60)
    print(f"🏆 BEST RETURN: {result['best_return']*100:.2f}%")
    print("📋 WINNING DNA:")
    params = result['best_params']
    print(f"   ► Sell {params['scale_out_amt']*100}% of shares when price rises {params['scale_out_trigger']*100}%")
    print(f"   ► Buy with {params['scale_in_amt']*100}% of cash when price drops {params['scale_in_trigger']*100}%")
    print("="*60)

if __name__ == "__main__":
    test_full_grind()
