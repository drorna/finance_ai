import numpy as np
import pandas as pd
import itertools
from typing import Dict, List, Tuple

# Try to import Numba for JIT compilation, fallback to Python if missing
try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    # Dummy decorator if Numba is missing
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

class PolicyBacktester:
    HAS_NUMBA = HAS_NUMBA # Expose for debug
    """
    The 'Heavy Artillery' Engine.
    Simulates complex, path-dependent strategies (Scaling In/Out) using optimized loops.
    Designed by: The Quant Architect.
    Implemented by: The Core Developer.
    """
    
    def __init__(self, ticker: str, data: pd.DataFrame):
        self.ticker = ticker
        self.data = data.sort_index()
        
        # Data Integrity Check (The Controller's Requirement)
        if self.data.isnull().values.any():
            self.data = self.data.ffill().bfill()
        
        # Pre-compute arrays for speed
        self.closes = self.data['Close'].to_numpy()
        self.opens = self.data['Open'].to_numpy() # For realistic entry
        self.dates = self.data.index
        
    def generate_policy_grid(self):
        """
        Generates the massive grid of parameters for the 'Deep Grind'.
        """
        pass

    @staticmethod
    @jit(nopython=True)
    def simulate_policy_fast(closes, initial_cash, entry_signal_indices, 
                           scale_out_triggers, scale_out_amts,
                           scale_in_triggers, scale_in_amts, max_drawdown_limit):
        """
        Numba-optimized simulation loop.
        Supports MULTI-TIER strategies (Arrays).
        """
        cash = initial_cash
    @staticmethod
    @jit(nopython=True)
    def simulate_policy_fast(closes, initial_cash, entry_signal_indices, 
                           scale_out_triggers, scale_out_amts,
                           scale_in_triggers, scale_in_amts, max_drawdown_limit):
        """
        Numba-optimized simulation loop.
        Updated Logic: 
        1. Scale In is % of CURRENT POSITION (Pyramiding/Averaging), not % of Cash.
        2. Supports "Negative Scale Out" (Stop Loss) if triggers are negative? 
           - Current Implementation: simplified for speed. 
           - We will add standard Stop Loss logic here? 
           - Users asked for "Selling on Drops". 
           - Let's treat 'scale_out_triggers' as absolute change targets.
             If user passes [-0.05], it implies Stop Loss.
        """
        cash = initial_cash
        shares = 0.0
        avg_cost = 0.0
        
        equity_curve = np.zeros(len(closes))
        peak_equity = initial_cash
        
        # We need to track executed tiers to avoid repeating them endlessly in the same zone
        # Ideally we use a bitmask or boolean array, but for simple scalar tiers:
        # We use 'idx' pointers.
        
        current_out_idx = 0
        current_in_idx = 0
        
        n_out_levels = len(scale_out_triggers)
        n_in_levels = len(scale_in_triggers)

        for t in range(len(closes)):
            price = closes[t]
            
            # 1. Entry Logic
            if shares == 0:
                if t == 0:
                    shares = cash / price
                    cash = 0.0
                    avg_cost = price
                    
                    current_out_idx = 0
                    current_in_idx = 0
                    
                    equity_curve[t] = cash + (shares * price)
                    continue
            
            current_equity = cash + (shares * price)
            equity_curve[t] = current_equity
            
            if current_equity > peak_equity:
                peak_equity = current_equity
                
            # Global Safety Net (Portfolio Level Stop)
            dd = (current_equity - peak_equity) / peak_equity
            if dd < -max_drawdown_limit:
                cash = current_equity
                shares = 0
                avg_cost = 0
                continue
                
            # 2. Position Management
            if shares > 0:
                pct_change = (price - avg_cost) / avg_cost
                
                # A. Scale Out (Profit Taking OR Stop Loss)
                # To support Stop Loss in the array, we must handle checking logic carefully.
                # Standard grid assumes positive triggers (Profit).
                # If we want "Selling on Drop", we check "if pct_change <= negative_trigger".
                
                # For Deep Grind V2, we focus on Profit Taking here.
                # Stop Loss is practically handled by "Max Drawdown" or specific Stop params?
                # The user asked for "Selling on Drops".
                # Let's check the triggers:
                # If trigger is POSITIVE -> Sell if pct_change >= trigger
                # If trigger is NEGATIVE -> Sell if pct_change <= trigger (Stop Loss)
                
                if current_out_idx < n_out_levels:
                    trig = scale_out_triggers[current_out_idx]
                    amt_pct = scale_out_amts[current_out_idx]
                    
                    triggered = False
                    if trig > 0:
                        if pct_change >= trig: triggered = True
                    elif trig < 0:
                        if pct_change <= trig: triggered = True
                        
                    if triggered:
                        # SELL
                        sell_shares = shares * amt_pct
                        cash += sell_shares * price
                        shares -= sell_shares
                        current_out_idx += 1
                        
                # B. Scale In (Buy Dip OR Momentum)
                if current_in_idx < n_in_levels:
                    trig = scale_in_triggers[current_in_idx]
                    amt_pct = scale_in_amts[current_in_idx]
                    
                    triggered = False
                    # Current logic: 'trig' passed as positive for DIP (legacy). 
                    # e.g. 0.05 means "Drop of 5%". So pct_change <= -0.05
                    # Momentum: If we want to buy on +5%, we pass -0.05? No.
                    # Let's standardize: 
                    # Trig > 0: Momentum Buy (Buy when UP X%)
                    # Trig < 0: Dip Buy (Buy when DOWN X%)  <-- User inputs POSITIVE for dip usually?
                    # Let's keep legacy: "Dip Triggers" are positives meaning drop.
                    # But for "Momentum", we need a negative sign? Confusing.
                    
                    # Let's stick to: "Scale In Trigger" is a signed float.
                    # -0.05 = Buy at -5%
                    # +0.05 = Buy at +5%
                    # THIS REQUIRES UPDATING THE GRID GENERATION TO PASS NEGATIVES FOR DIPS.
                    
                    # ADAPTING LOGIC:
                    # We will update grid gen to pass negative numbers for Dips.
                    
                    if trig < 0: # Dip
                        if pct_change <= trig: triggered = True
                    elif trig > 0: # Momentum
                        if pct_change >= trig: triggered = True
                        
                    if triggered:
                        # BUY
                        # NEW LOGIC: % of POSITION SIZE (Not Cash)
                        current_pos_val = shares * price
                        cost_to_buy = current_pos_val * amt_pct
                        
                        # Fallback: If position is 0 (shouldn't be), use % of cash?
                        if current_pos_val == 0: cost_to_buy = cash * amt_pct
                        
                        # Cap at available cash
                        if cost_to_buy > cash:
                            cost_to_buy = cash 
                            
                        if cost_to_buy > 0:
                            new_shares = cost_to_buy / price
                            
                            total_val = (shares * avg_cost) + cost_to_buy
                            shares += new_shares
                            avg_cost = total_val / shares
                            cash -= cost_to_buy
                            
                            current_in_idx += 1
                            # Reset Profit Levels?
                            # If we Average Down, our Avg Cost drops, so we might be closer to profit targets.
                            # Usually we reset levels to capture the new "cycle".
                            current_out_idx = 0 
        
        final_eq = cash + (shares * closes[-1])
        return final_eq, equity_curve

    @staticmethod
    def simulate_policy_debug(closes, dates, initial_cash, 
                           scale_out_triggers, scale_out_amts,
                           scale_in_triggers, scale_in_amts, max_drawdown_limit):
        """
        Pure Python version for auditing and visualization.
        """
        # Convert scalars to list if necessary
        if not isinstance(scale_out_triggers, (list, np.ndarray)): scale_out_triggers = [scale_out_triggers]
        if not isinstance(scale_out_amts, (list, np.ndarray)): scale_out_amts = [scale_out_amts]
        if not isinstance(scale_in_triggers, (list, np.ndarray)): scale_in_triggers = [scale_in_triggers]
        if not isinstance(scale_in_amts, (list, np.ndarray)): scale_in_amts = [scale_in_amts]

        cash = initial_cash
        shares = 0.0
        avg_cost = 0.0
        peak_equity = initial_cash
        trade_logs = []
        
        current_out_idx = 0
        current_in_idx = 0
        
        for t in range(len(closes)):
            price = closes[t]
            date = dates[t].strftime('%Y-%m-%d')
            
            # 1. Entry Logic
            if t == 0:
                shares = int((cash * 0.5) / price)
                cost = shares * price
                cash -= cost
                avg_cost = price
                peak_equity = cost + cash
                
                trade_logs.append({
                    "Date": date,
                    "Action": "ENTRY",
                    "Price": price,
                    "Shares": shares,
                    "Value": cost,
                    "Reason": "Initial Entry"
                })
                continue

            current_equity = cash + (shares * price)
            if current_equity > peak_equity: 
                peak_equity = current_equity
            
            # Drawdown check
            pct_from_peak = (current_equity - peak_equity) / peak_equity if peak_equity > 0 else 0
            if pct_from_peak < -max_drawdown_limit:
                trade_logs.append({
                    "Date": date,
                    "Action": "STOP LOSS",
                    "Price": price,
                    "Shares": -shares,
                    "Value": shares * price,
                    "Reason": f"Max Drawdown {pct_from_peak*100:.1f}%"
                })
                cash += shares * price
                shares = 0
                break

            if shares > 0:
                price_change = (price - avg_cost) / avg_cost
                
                # Scale Out logic (Support Negative/Stop Loss)
                if current_out_idx < len(scale_out_triggers):
                    trig = scale_out_triggers[current_out_idx]
                    amt_pct = scale_out_amts[current_out_idx]
                    
                    triggered = False
                    reason_str = ""
                    if trig > 0:
                        if price_change >= trig: 
                            triggered = True
                            reason_str = f"Profit Target (+{trig*100:.0f}%)"
                    elif trig < 0:
                        if price_change <= trig: 
                            triggered = True
                            reason_str = f"Stop Loss ({trig*100:.0f}%)"
                            
                    if triggered:
                        sell_shares = int(shares * amt_pct)
                        if sell_shares > 0:
                            proceeds = sell_shares * price
                            shares -= sell_shares
                            cash += proceeds
                            trade_logs.append({
                                "Date": date,
                                "Action": "TAKE PROFIT" if trig > 0 else "PARTIAL STOP",
                                "Price": price,
                                "Shares": -sell_shares,
                                "Value": proceeds,
                                "Reason": reason_str
                            })
                            current_out_idx += 1

                # Scale In logic (Support Positive/Momentum)
                if current_in_idx < len(scale_in_triggers):
                    trig = scale_in_triggers[current_in_idx]
                    amt_pct = scale_in_amts[current_in_idx]
                    
                    triggered = False
                    reason_str = ""
                    
                    if trig < 0: # Dip
                         if price_change <= trig: 
                             triggered = True
                             reason_str = f"Buy Dip ({trig*100:.0f}%)"
                    elif trig > 0: # Momentum
                         if price_change >= trig:
                             triggered = True
                             reason_str = f"Momentum Add (+{trig*100:.0f}%)"
                             
                    if triggered:
                        # NEW LOGIC: % of POSITION
                        current_pos_val = shares * price
                        buy_amt = current_pos_val * amt_pct
                        
                        if buy_amt > cash: buy_amt = cash
                        
                        if buy_amt > 10:
                            new_shares = int(buy_amt / price)
                            if new_shares > 0:
                                cost = new_shares * price
                                total_cost = (shares * avg_cost) + cost
                                shares += new_shares
                                avg_cost = total_cost / shares
                                cash -= cost
                                
                                trade_logs.append({
                                    "Date": date,
                                    "Action": "BUY DIP" if trig < 0 else "PYRAMID UP",
                                    "Price": price,
                                    "Shares": new_shares,
                                    "Value": cost,
                                    "Reason": reason_str
                                })
                                current_in_idx += 1
                                current_out_idx = 0
                            
        final_val = cash + (shares * closes[-1])
        return final_val, trade_logs

    def run_exhaustive_optimization(self, entry_type="sma_crossover", audit_mode=False):
        """
        Multi-Tier + Relative Buys + Stop Loss Support
        """
        # --- GENERATE SMART TIERS ---
        
        # A. Scale Out (Profit) - Positive Triggers
        ladder_sells = [
            (np.array([0.10, 0.20, 0.30]), np.array([0.20, 0.20, 0.20])),
            (np.array([0.15, 0.30, 0.50]), np.array([0.30, 0.30, 0.30])),
            (np.array([0.25]), np.array([0.5])), # Moonbag
            (np.array([1.00]), np.array([0.5])), # Moonbag Extreme
        ]
        
        # B. Scale In (Dips) - NEGATIVE Triggers
        # We must convert old positive logic to negative here
        martingale_buys = [
            (np.array([-0.05, -0.10, -0.15]), np.array([0.20, 0.50, 1.00])), # 20% of pos, then 50% of pos...
            (np.array([-0.05, -0.10, -0.15, -0.20]), np.array([0.10, 0.10, 0.10, 0.10])),
        ]
        
        # C. Brute Force Single-Tier
        bf_sell_trigs = [0.03, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
        bf_sell_amts = [0.10, 0.20, 0.33, 0.50, 1.00]
        
        bf_buy_trigs = [-0.03, -0.05, -0.08, -0.10, -0.15, -0.20] # Negatives for drops
        bf_buy_amts = [0.10, 0.20, 0.30, 0.50, 1.00] # % of Position
        
        # [NEW] Stop Loss Strategies?
        # Maybe add a "Fast Cut" strategy: Sell 100% at -5%
        stop_loss_strats = [
             (np.array([-0.05]), np.array([1.0])), # Cut all at -5%
             (np.array([-0.08]), np.array([1.0])), # Cut all at -8%
        ]
        
        # Convert BF to list of tuples
        brute_force_sells = []
        for t, a in itertools.product(bf_sell_trigs, bf_sell_amts):
            brute_force_sells.append((np.array([t]), np.array([a])))
            
        brute_force_buys = []
        for t, a in itertools.product(bf_buy_trigs, bf_buy_amts):
            brute_force_buys.append((np.array([t]), np.array([a])))
            
        # Combine All
        all_sell_strats = ladder_sells + brute_force_sells + stop_loss_strats
        all_buy_strats = martingale_buys + brute_force_buys
        
        # Cartesian Product
        param_grid = list(itertools.product(all_sell_strats, all_buy_strats))
        total_combos = len(param_grid)
        
        print(f"🔬 Deep Grind: Analyzing {total_combos} strategies (Inc. Stop Loss & Relative Buys)...")
        
        best_ret = -999.0
        best_params = None
        audit_results = []
        max_drawdown = 0.40
        initial_cash = 10000.0
        
        # JIT Warmup
        if self.HAS_NUMBA:
            d_s_t, d_s_a = ladder_sells[0]
            d_b_t, d_b_a = martingale_buys[0]
            self.simulate_policy_fast(self.closes, initial_cash, None, d_s_t, d_s_a, d_b_t, d_b_a, max_drawdown)
            
        for sell_strat, buy_strat in param_grid:
            s_trigs, s_amts = sell_strat
            b_trigs, b_amts = buy_strat
            
            final_val, curve = self.simulate_policy_fast(
                self.closes, 
                initial_cash, 
                None, 
                s_trigs, s_amts, 
                b_trigs, b_amts, 
                max_drawdown
            )
            
            ret = (final_val / initial_cash) - 1
            
            if ret > best_ret:
                best_ret = ret
                best_params = {
                    "scale_out_triggers": s_trigs.tolist(),
                    "scale_out_amts": s_amts.tolist(),
                    "scale_in_triggers": b_trigs.tolist(),
                    "scale_in_amts": b_amts.tolist()
                }
            
            if audit_mode:
                # Stringify for ID
                s_id = "/".join([f"{t*100:.0f}%" for t in s_trigs])
                b_id = "/".join([f"-{t*100:.0f}%" for t in b_trigs])
                
                audit_results.append({
                    "strategy_name": f"Sell[{s_id}] / Buy[{b_id}]",
                    "return_pct": ret * 100,
                    "final_equity": final_val,
                    "scale_out_triggers": s_trigs.tolist(), # For audit inspect
                    "scale_in_triggers": b_trigs.tolist()
                })

        result_payload = {
            "best_return": best_ret,
            "best_params": best_params,
            "total_calculated": total_combos
        }
        
        if audit_mode:
            result_payload["audit_df"] = pd.DataFrame(audit_results).sort_values(by="return_pct", ascending=False)
            
        return result_payload
