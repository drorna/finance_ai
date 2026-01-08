import yfinance as yf
import pandas as pd
import numpy as np

def get_market_regime():
    """
    Determines if the market is Bull or Bear based on SPY SMA200.
    Returns: 'BULL' or 'BEAR'
    """
    try:
        spy = yf.Ticker("SPY")
        # Fetch enough data for 200 SMA
        hist = spy.history(period="1y") 
        if len(hist) < 200:
            return "UNKNOWN" # Not enough data
        
        sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        current_price = hist['Close'].iloc[-1]
        
        return "BULL" if current_price > sma200 else "BEAR"
    except Exception as e:
        print(f"Error getting market regime: {e}")
        return "UNKNOWN"

def calculate_atr(data, window=14):
    """
    Calculates Average True Range (ATR).
    """
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    atr = true_range.rolling(window=window).mean()
    return atr

def analyze_portfolio(portfolio_items):
    """
    Analyzes a list of portfolio items using yfinance.
    Returns a dictionary mapping symbol -> data dict.
    """
    if not portfolio_items:
        return {}

    symbols = [item.symbol for item in portfolio_items]
    results = {}
    
    try:
        # Batch fetch 1 month of data for ATR
        tickers = yf.Tickers(" ".join(symbols))
        
        for item in portfolio_items:
            symbol = item.symbol
            try:
                ticker = tickers.tickers.get(symbol)
                if not ticker:
                    ticker = yf.Ticker(symbol)
                
                # Get historical data
                hist = ticker.history(period="1mo")
                
                if hist.empty:
                    # Fallback to simple data if no history
                    info = ticker.fast_info
                    current_price = float(info.last_price) if info.last_price else float(item.avg_price)
                    results[symbol] = {
                        "price": current_price,
                        "change": 0.0,
                        "change_pct": 0.0,
                        "atr": 0.0,
                        "is_high_volatility": False,
                        "volatility_msg": "No Data"
                    }
                    continue

                # Calculate Metrics
                current_price = float(hist['Close'].iloc[-1])
                
                # Try to get previous close from history, fall back to fast_info
                if len(hist) > 1:
                    prev_close = float(hist['Close'].iloc[-2])
                else:
                    # If history is too short (e.g. today only), try fast_info
                    prev = ticker.fast_info.previous_close
                    prev_close = float(prev) if prev else current_price
                
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
                
                # ATR Calculation
                atr_series = calculate_atr(hist)
                current_atr = atr_series.iloc[-1] if not atr_series.empty and not pd.isna(atr_series.iloc[-1]) else 0
                
                # Volatility Check (Drop > 1.5 * ATR)
                drop = prev_close - current_price
                is_high_volatility = (drop > 1.5 * current_atr) if current_atr > 0 else False
                
                volatility_msg = ""
                if is_high_volatility:
                    volatility_msg = f"High Volatility! Drop {drop:.2f} > 1.5*ATR ({1.5*current_atr:.2f})"
                
                results[symbol] = {
                    "price": current_price,
                    "change": change,
                    "change_pct": change_pct,
                    "atr": current_atr,
                    "is_high_volatility": is_high_volatility,
                    "volatility_msg": volatility_msg
                }
                
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                results[symbol] = {
                    "price": item.avg_price,
                    "change": 0, 
                    "change_pct": 0,
                    "atr": 0, 
                    "is_high_volatility": False
                }
                
    except Exception as e:
        print(f"Global analysis error: {e}")
        
    return results
