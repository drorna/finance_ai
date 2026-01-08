import numpy as np
import pandas as pd
import itertools
from typing import Dict, List, Tuple

class VectorizedBacktester:
    """
    High-performance vectorized backtester using NumPy for massive grid searching.
    Algorithms designed by 'The Quant Architect'.
    Implemented by 'Core Dev'.
    """
    
    def __init__(self, ticker: str, data: pd.DataFrame):
        self.ticker = ticker
        self.data = data.sort_index()
        self.verify_data_integrity()
        
        # Pre-compute NumPy arrays for speed
        self.closes = self.data['Close'].to_numpy()
        self.opens = self.data['Open'].to_numpy()
        self.highs = self.data['High'].to_numpy()
        self.lows = self.data['Low'].to_numpy()
        self.volumes = self.data['Volume'].to_numpy()
        self.dates = self.data.index
        
    def verify_data_integrity(self):
        """
        Controller Agent Checkpoint: Data Sanity.
        """
        if self.data.isnull().values.any():
            # Fill small gaps or raise error
            self.data = self.data.ffill().bfill()
        
        if len(self.data) < 200:
             raise ValueError(f"Insufficient data points for {self.ticker}. Needed > 200.")

    def run_sma_crossover_batch(self, fast_range, slow_range) -> pd.DataFrame:
        """
        Vectorized calculation of SMA Cross strategies.
        Returns a DataFrame of results for all combinations.
        """
        results = []
        
        # Calculate all necessary SMAs first to avoid re-calculation
        # dict of window -> array
        unique_windows = sorted(list(set(fast_range + slow_range)))
        sma_cache = {}
        
        closes_s = pd.Series(self.closes)
        for w in unique_windows:
            sma_cache[w] = closes_s.rolling(window=w).mean().to_numpy()
            
        param_grid = list(itertools.product(fast_range, slow_range))
        
        for fast, slow in param_grid:
            if fast >= slow: continue
            
            sma_fast = sma_cache[fast]
            sma_slow = sma_cache[slow]
            
            # 1. Generate Signal (1 = Buy, 0 = Cash)
            # Market Position: Long if Fast > Slow
            position = np.where(sma_fast > sma_slow, 1, 0)
            
            # 2. Shift Signal (CRITICAL: Lookahead Bias Prevention)
            # We trade at Open/Close of NEXT day based on TODAY's signal
            # effectively, returns are shifted.
            # Strategy Returns = Signal[t-1] * PctChange[t]
            
            # Using simple Close-to-Close returns for approximation speed
            # (Can detailed to Open-to-Close later)
            pct_change = np.diff(self.closes) / self.closes[:-1]
            pct_change = np.insert(pct_change, 0, 0) # align length
            
            # Shift position array to align with next day's return
            # Position at [t] dictates return at [t+1]
            # So Strategy Return at [t] = Position [t-1] * Pct_Change[t]
            
            pos_shifted = np.roll(position, 1)
            pos_shifted[0] = 0 # No position on day 0
            
            strategy_returns = pos_shifted * pct_change
            
            # 3. Calculate Metrics
            # Cumulative Return
            equity_curve = np.cumprod(1 + strategy_returns)
            total_return = equity_curve[-1] - 1
            
            # Max Drawdown
            running_max = np.maximum.accumulate(equity_curve)
            drawdown = (equity_curve - running_max) / running_max
            max_dd = np.min(drawdown)
            
            # Sharpe (Annualized) - Simplified, assuming risk_free=0
            if np.std(strategy_returns) == 0:
                sharpe = 0
            else:
                sharpe = np.mean(strategy_returns) / np.std(strategy_returns) * np.sqrt(252)
                
            trades_count = np.sum(np.abs(np.diff(position)))
            
            results.append({
                "Fast": fast,
                "Slow": slow,
                "Return": total_return,
                "MaxDD": max_dd,
                "Sharpe": sharpe,
                "Trades": trades_count
            })
            
        return pd.DataFrame(results)

    def run_dca_simulation_fast(self, drop_step=0.05, take_profit=0.15, max_adds=3):
        """
        Semi-vectorized DCA engine. Harder to fully vectorize due to path dependence (cash state),
        but we can optimize using Numba if needed. 
        For now, this is a refined loop optimized for speed.
        """
        # Optimized loop construction
        # ... (Implementation pending Numba integration for speed)
        pass 
