import yfinance as yf
import pandas as pd
import numpy as np

def analyze_market_regime(ticker="SPY", period="10y"):
    """
    Analyzes the 'Broad Market' regime using a benchmark ticker (SPY).
    Regime is defined by price relative to SMA200.
    
    Returns:
        dict: {
            "regime": "BULL" | "BEAR",
            "sma200": float,
            "current_price": float,
            "volatility": float (annualized std dev)
        }
    """
    try:
        # Fetch history
        stock = yf.Ticker(ticker)
        # We need enough data for 200 SMA, so 1y minimum, but user requested 10y for robust backtesting context
        hist = stock.history(period=period)
        
        if len(hist) < 200:
            return {"regime": "NEUTRAL", "reason": "Insufficient Data"}
        
        # Calculate SMA 200
        hist['SMA200'] = hist['Close'].rolling(window=200).mean()
        
        current_price = hist['Close'].iloc[-1]
        sma200 = hist['SMA200'].iloc[-1]
        
        # Calculate Volatility (Standard Deviation of Daily Returns * sqrt(252))
        hist['Daily_Return'] = hist['Close'].pct_change()
        volatility = hist['Daily_Return'].std() * np.sqrt(252) * 100 # Percentage
        
        regime = "BULL" if current_price > sma200 else "BEAR"
        
        return {
            "regime": regime,
            "sma200": sma200,
            "current_price": current_price,
            "volatility": volatility
        }
    except Exception as e:
        print(f"Error in analyze_market_regime: {e}")
        return {"regime": "NEUTRAL", "error": str(e)}

def generate_signals(portfolio, market_regime_data):
    """
    Generates basic trend-following signals for the portfolio.
    
    Rule:
    - If Market is BULL: Look for Uptrends (Price > SMA50). Buy/Hold.
    - If Market is BEAR: Look for Downtrends. Sell/Caution.
    """
    signals = {}
    
    regime = market_regime_data.get("regime", "NEUTRAL")
    
    for asset in portfolio:
        symbol = asset.symbol
        try:
            # Quick fetch for individual asset trend
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")
            
            if len(hist) < 50:
                 signals[symbol] = {"action": "HOLD", "reason": "New listing / Insufficient Data"}
                 continue
                 
            sma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            price = hist['Close'].iloc[-1]
            
            if regime == "BULL":
                if price > sma50:
                    action = "BUY/HOLD"
                    reason = "Strong Uptrend in Bull Market"
                else:
                    action = "HOLD"
                    reason = "Pullback in Bull Market"
            elif regime == "BEAR":
                if price < sma50:
                    action = "SELL/HEDGE"
                    reason = "Downtrend in Bear Market"
                else:
                    action = "CAUTION"
                    reason = "Counter-trend Rally (Bull Trap?)"
            else:
                action = "HOLD"
                reason = "Market Neutral"
                
            signals[symbol] = {"action": action, "reason": reason, "sma50": sma50}
            
        except Exception as e:
            signals[symbol] = {"action": "ERROR", "reason": str(e)}
            
    return signals

def backtest_strategy(ticker="SPY", period="5y", initial_capital=10000):
    """
    Simulates a simple Trend Following strategy (SMA200) vs Buy & Hold.
    
    Strategy:
    - Long when Price > SMA200
    - Cash (0% return) when Price < SMA200
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        
        if len(df) < 200:
            return None
            
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['Pct_Change'] = df['Close'].pct_change()
        
        # Strategy Logic: If Prev Close > Prev SMA200, we are invested today.
        # Shift(1) to avoid lookahead bias.
        df['Signal'] = np.where(df['Close'].shift(1) > df['SMA200'].shift(1), 1, 0)
        
        df['Strategy_Return'] = df['Signal'] * df['Pct_Change']
        df['BuyHold_Return'] = df['Pct_Change']
        
        # Cumulative Returns
        df['Strategy_Equity'] = initial_capital * (1 + df['Strategy_Return']).cumprod()
        df['BuyHold_Equity'] = initial_capital * (1 + df['BuyHold_Return']).cumprod()
        
        total_return_strat = (df['Strategy_Equity'].iloc[-1] / initial_capital) - 1
        total_return_bh = (df['BuyHold_Equity'].iloc[-1] / initial_capital) - 1
        
        return {
            "strategy_return": total_return_strat * 100,
            "buy_hold_return": total_return_bh * 100,
            "final_equity": df['Strategy_Equity'].iloc[-1],
            "ticker": ticker
        }
    except Exception as e:
        print(f"Backtest failed: {e}")
        return None
