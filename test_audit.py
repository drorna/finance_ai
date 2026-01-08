import pandas as pd
import numpy as np
from quant.policy_engine import PolicyBacktester

def test_audit_mode():
    # 1. Generate Synthetic Volatile Data
    np.random.seed(42)
    days = 200
    dates = pd.date_range("2020-01-01", periods=days)
    prices = 100 + np.cumsum(np.random.normal(0, 2, days))
    prices = np.maximum(prices, 10)
    
    df = pd.DataFrame({
        "Close": prices,
        "Open": prices,
        "High": prices * 1.01,
        "Low": prices * 0.99,
        "Volume": 1000
    }, index=dates)
    
    print("\n--- 🧪 STARTING AUDIT MODE TEST ---")
    engine = PolicyBacktester("AUDIT_TEST", df)
    
    # Run with audit_mode=True
    result = engine.run_exhaustive_optimization(audit_mode=True)
    
    audit_df = result.get('audit_df')
    if audit_df is not None:
        print(f"✅ Audit DataFrame received with {len(audit_df)} rows.")
        print("Top 5 Strategies:")
        print(audit_df.head(5).to_string())
        
        # Verify columns exist
        print("\nColumns:", audit_df.columns.tolist())
    else:
        print("❌ FAILED: No audit_df returned.")

if __name__ == "__main__":
    test_audit_mode()
