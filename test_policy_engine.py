import time
import pandas as pd
import numpy as np
from quant.policy_engine import PolicyBacktester

def create_dummy_data(days=1000):
    # Generate synthetic price data
    dates = pd.date_range(start="2020-01-01", periods=days)
    # Random walk
    returns = np.random.normal(0.001, 0.02, days)
    price_paths = np.cumprod(1 + returns) * 100
    
    df = pd.DataFrame({
        "Open": price_paths,
        "High": price_paths * 1.01,
        "Low": price_paths * 0.99,
        "Close": price_paths,
        "Volume": np.random.randint(1000, 100000, days)
    }, index=dates)
    return df

def run_benchmark():
    print("Generating synthetic data (1000 days)...")
    df = create_dummy_data()
    
    print("Initializing PolicyBacktester...")
    engine = PolicyBacktester("TEST_TICKER", df)
    print(f"DEBUG: Numba Installed? {engine.HAS_NUMBA}")
    if engine.HAS_NUMBA:
         print("DEBUG: JIT Compilation expected on first run...")
    
    print("\n--- Starting Numba Compilation (First Run is slower) ---")
    start_time = time.time()
    
    # Dummy parameters for compilation run
    closes = engine.closes
    initial_cash = 10000.0
    # Create empty signal array (always invested for stress test)
    # Actually logic in sim is: if shares=0 check entry. 
    # We'll rely on the manual call for now just to test speed of the loop.
    
    # We call the static method directly to test the JIT loop speed
    # scale_out_trigger=0.10, amt=0.5
    # scale_in_trigger=0.05, amt=0.2
    final_eq, curve = engine.simulate_policy_fast(
        closes, initial_cash, None, 0.10, 0.50, 0.05, 0.20, 0.20
    )
    
    compile_time = time.time() - start_time
    print(f"First Run (Compilation + Exec): {compile_time:.4f} seconds")
    print(f"Final Equity: {final_eq:.2f}")
    
    print("\n--- Starting High-Speed Grid Search (10,000 simulations) ---")
    
    # Simulate a loop of 10,000 iterations to measure throughput
    # This simulates checking 10k different parameter combinations
    start_bench = time.time()
    
    iterations = 10000
    for i in range(iterations):
         # Vary params slightly to simulate grid
         res, _ = engine.simulate_policy_fast(
            closes, initial_cash, None, 
            0.05 + (i%20)*0.01, # Trigger varies
            0.50, 
            0.05, 
            0.20, 
            0.20
        )
         
    total_time = time.time() - start_bench
    print(f"Completed {iterations} simulations in {total_time:.4f} seconds")
    print(f"Speed: {iterations / total_time:.0f} simulations/second")

if __name__ == "__main__":
    run_benchmark()
