import yfinance as yf
import pandas as pd
import numpy as np
import itertools

def get_asset_fundamentals(ticker):
    """
    Fetches fundamental data to categorize the asset.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Safe extraction with defaults
        market_cap = info.get('marketCap', 0)
        sector = info.get('sector', 'Unknown')
        beta = info.get('beta', 1.0)
        trailing_eps = info.get('trailingEps', 0)
        
        # Categorization Logic
        
        # 1. Size
        if market_cap > 200_000_000_000: size = "Mega Cap"
        elif market_cap > 10_000_000_000: size = "Large Cap"
        elif market_cap > 2_000_000_000: size = "Mid Cap"
        else: size = "Small/Micro Cap"
        
        # 2. Profitability
        health = "Profitable" if trailing_eps > 0 else "Speculative (Unprofitable)"
        
        # 3. Volatility Profile
        vol_profile = "High Volatility" if beta > 1.3 else "Low Volatility" if beta < 0.8 else "Moderate Volatility"
        
        return {
            "ticker": ticker,
            "sector": sector,
            "size": size,
            "health": health,
            "volatility": vol_profile,
            "beta": beta
        }
    except Exception as e:
        print(f"Error fetching fundamentals for {ticker}: {e}")
        return {"ticker": ticker, "sector": "Unknown", "size": "Unknown", "health": "Unknown", "volatility": "Unknown"}

def run_simulation_loop(hist, strategy_type, params):
    """
    Simulates a strategy row-by-row for complex logic (DCA, Partial Exits).
    Returns total return percentage.
    """
    cash = 10000.0
    initial_cash = 10000.0
    shares = 0
    avg_price = 0.0
    
    # Pre-calculated columns for speed
    closes = hist['Close'].values
    dates = hist.index
    
    # State variables
    entry_price = 0.0
    dca_count = 0
    
    # Params extraction
    if strategy_type == "DCA_Accumulator":
        drop_step = params['drop_step'] # e.g., 0.05 for 5% drop
        max_adds = params['max_adds']
        take_profit = params['take_profit']
        
        # Initial Buy at start
        shares = int(cash * 0.5 / closes[0]) # Start with 50% capital
        cash -= shares * closes[0]
        avg_price = closes[0]
        
        for i in range(1, len(closes)):
            price = closes[i]
            
            # DCA Logic: Buy more if price drops X% below avg cost
            if shares > 0 and dca_count < max_adds:
                if price < avg_price * (1 - drop_step):
                    # Buy more
                    invest_amount = 2000 # Fixed add amount for sim
                    if cash >= invest_amount:
                        new_shares = int(invest_amount / price)
                        total_cost = (shares * avg_price) + (new_shares * price)
                        shares += new_shares
                        avg_price = total_cost / shares
                        cash -= new_shares * price
                        dca_count += 1
            
            # Take Profit Logic
            if shares > 0 and price > avg_price * (1 + take_profit):
                # Sell All
                cash += shares * price
                shares = 0
                avg_price = 0
                dca_count = 0
                # Re-enter next day? For accumulation strategy, maybe wait or re-enter small.
                # Simplified: Re-enter 20%
                shares = int(cash * 0.2 / price)
                cash -= shares * price
                avg_price = price
                
    elif strategy_type == "Swing_Partial":
        tp1 = params['tp1']
        tp2 = params['tp2']
        stop_loss = params['stop_loss']
        
        in_trade = False
        tp1_hit = False
        
        for i in range(1, len(closes)):
            price = closes[i]
            prev_price = closes[i-1]
            
            # Simple Entry: RSI-like or Dip (Simplified as: Up day after down day)
            if not in_trade:
                # Buy Logic: Random entry or simple dip for Grid Search context
                # Let's assume we buy on a green day
                if price > prev_price:
                    shares = int(cash / price)
                    cash -= shares * price
                    entry_price = price
                    in_trade = True
                    tp1_hit = False
            
            else:
                # Manage Trade
                pct_change = (price - entry_price) / entry_price
                
                # Stop Loss
                if pct_change < -stop_loss:
                    cash += shares * price
                    shares = 0
                    in_trade = False
                    
                # TP1 (sell 50%)
                elif not tp1_hit and pct_change > tp1:
                    sell_shares = int(shares * 0.5)
                    cash += sell_shares * price
                    shares -= sell_shares
                    tp1_hit = True
                    
                # TP2 (Sell Rest)
                elif pct_change > tp2:
                    cash += shares * price
                    shares = 0
                    in_trade = False

    # Final Value
    final_value = cash + (shares * closes[-1])
    return (final_value / initial_cash) - 1

def run_grid_search(ticker, period="2y"):
    """
    Runs a simulation of multiple strategy parameters to find the best fit.
    """
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    
    if len(hist) < 100:
        return None
        
    best_result = {
        "strategy_name": "Hold",
        "return": 0,
        "params": {}
    }
    
    # --- Strategy 1: Trend Following (Vectorized SMA) ---
    sma_windows = [20, 50, 100]
    for w in sma_windows:
        df = hist.copy()
        df['SMA'] = df['Close'].rolling(window=w).mean()
        df['Signal'] = np.where(df['Close'] > df['SMA'], 1, 0)
        df['Strategy'] = df['Signal'].shift(1) * df['Close'].pct_change()
        cum_ret = (1 + df['Strategy']).cumprod().iloc[-1] - 1
        
        if cum_ret > best_result['return']:
            best_result = {"strategy_name": f"Trend Following (SMA{w})", "return": cum_ret, "params": {"window": w}}

    # --- Strategy 2: DCA Accumulator (Loop) ---
    dca_params = list(itertools.product([0.05, 0.10], [1, 3], [0.15, 0.30])) # Drop, Adds, TP
    for drop, adds, tp in dca_params:
        params = {'drop_step': drop, 'max_adds': adds, 'take_profit': tp}
        ret = run_simulation_loop(hist, "DCA_Accumulator", params)
        if ret > best_result['return']:
            best_result = {
                "strategy_name": f"DCA Builder (Add on -{drop*100}%, TP +{tp*100}%)",
                "return": ret,
                "params": params
            }

    # --- Strategy 3: Swing Partial Exit (Loop) ---
    swing_params = list(itertools.product([0.10, 0.15], [0.20, 0.30], [0.05, 0.08])) # TP1, TP2, SL
    for tp1, tp2, sl in swing_params:
        params = {'tp1': tp1, 'tp2': tp2, 'stop_loss': sl}
        ret = run_simulation_loop(hist, "Swing_Partial", params)
        if ret > best_result['return']:
            best_result = {
                "strategy_name": f"Swing Profit (Sell 50%@{tp1*100}%, Rest@{tp2*100}%)",
                "return": ret,
                "params": params
            }
            
    # Compare vs Buy & Hold
    bh_ret = (1 + hist['Close'].pct_change()).cumprod().iloc[-1] - 1
    best_result['buy_hold_return'] = bh_ret
    
    return best_result

def optimize_asset(ticker):
    """
    Orchestrator: Categorizes asset and runs grid search.
    """
    fundamentals = get_asset_fundamentals(ticker)
    optimization = run_grid_search(ticker)
    
    return {
        "fundamentals": fundamentals,
        "optimization": optimization
    }
