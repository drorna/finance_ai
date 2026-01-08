import yfinance as yf
import pandas as pd
import numpy as np
from quant.policy_engine import PolicyBacktester
import time

class MarketScanner:
    def __init__(self):
        try:
             self.tickers_df = pd.read_csv("sp500.csv", on_bad_lines='warn')
             self.tickers = [t.replace('.', '-') for t in self.tickers_df['Symbol'].tolist()]
        except Exception as e:
             print(f"Error loading CSV: {e}")
             self.tickers_df = pd.DataFrame(columns=['Symbol', 'Sector'])
             self.tickers = []
        
    def load_sp500_tickers(self):
        # Deprecated: Using local file
        return self.tickers

    def get_sector(self, ticker):
        """Looks up sector from the local DataFrame"""
        try:
            row = self.tickers_df[self.tickers_df['Symbol'] == ticker.replace('-', '.')]
            if not row.empty:
                return row.iloc[0]['Sector']
        except:
             pass
        return "Unknown"

    def fetch_data(self, ticker, period="2y"):
        """Fetches data with basic error handling"""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            if len(df) > 100:
                return df
            return None
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None

    def get_universe(self, sectors=None, volatility_level=None, limit=50):
        """
        Filters the universe based on criteria.
        sectors: List of sectors to include (e.g. ['Information Technology'])
        volatility_level: 'Low', 'Medium', 'High' or None
        """
        df = self.tickers_df.copy()
        
        # 1. Filter by Sector
        if sectors:
             df = df[df['Sector'].isin(sectors)]
             
        # 2. Random sample if too large (before expensive vol check)
        # We fetch more than limit to allow for vol filtering, then cut
        candidates = df['Symbol'].tolist()
        candidates = [t.replace('.', '-') for t in candidates] # yfinance format
        
        filtered_tickers = []
        
        print(f"🔎 Filtering universe (Initial: {len(candidates)})...")
        
        # If no deep filtering needed, just return head
        if not volatility_level:
            return candidates[:limit]
            
        # 3. Filter by Volatility (Requires fetching data!)
        # This is expensive, so we only check enough to fill the limit
        count = 0
        for t in candidates:
            if count >= limit: break
            
            # Quick fetch for volatility check (3mo is enough)
            vol = self.get_volatility(t)
            if vol is None: continue
            
            is_match = False
            if volatility_level == 'Low' and vol < 0.20: is_match = True
            elif volatility_level == 'Medium' and 0.20 <= vol <= 0.40: is_match = True
            elif volatility_level == 'High' and vol > 0.40: is_match = True
            
            if is_match:
                filtered_tickers.append(t)
                count += 1
                
        return filtered_tickers

    def get_volatility(self, ticker):
        """Calculates annualized volatility (std dev of daily returns)"""
        try:
            hist = yf.Ticker(ticker).history(period="6mo")
            if len(hist) < 20: return None
            daily_ret = hist['Close'].pct_change().dropna()
            vol = daily_ret.std() * np.sqrt(252) # Annualized
            return vol
        except:
            return None

    def scan_market(self, sectors=None, volatility=None, limit=50, progress_callback=None):
        """
        Runs Deep Grind on the filtered universe.
        """
        # Get Filtered List
        run_list = self.get_universe(sectors, volatility, limit)
        results = []
        
        print(f"🌍 Starting Market Scan on {len(run_list)} assets...")
        
        for i, ticker in enumerate(run_list):
            print(f"   ► Processing {ticker}...")
            
            if progress_callback:
                progress_callback((i / len(self.tickers)))
            
            df = self.fetch_data(ticker)
            if df is not None:
                # Initialize Engine
                try:
                    engine = PolicyBacktester(ticker, df)
                    # Run Optimization (Fast mode inside engine handles grid)
                    # Note: We run WITHOUT audit_mode for speed in batch, 
                    # but we need the 'best_params'
                    opt_res = engine.run_exhaustive_optimization(audit_mode=False)
                    
                    if opt_res:
                        # Flatten the complex array params for CSV storage
                        best_params = opt_res.get('best_params', {})
                        
                        # Helper to stringify arrays
                        def arr_to_str(arr):
                            if isinstance(arr, (list, np.ndarray)):
                                return ",".join([f"{x:.2f}" for x in arr])
                            return str(arr)

                        row = {
                            "Ticker": ticker,
                            "Sector": self.get_sector(ticker),
                            "Return": opt_res.get('best_return', 0),
                            "Buy_Hold": (df['Close'].iloc[-1]/df['Close'].iloc[0]) - 1,
                            
                            # Strategy DNA
                            "Sell_Triggers": arr_to_str(best_params.get('scale_out_triggers', [])),
                            "Sell_Amts": arr_to_str(best_params.get('scale_out_amts', [])),
                            "Buy_Triggers": arr_to_str(best_params.get('scale_in_triggers', [])),
                            "Buy_Amts": arr_to_str(best_params.get('scale_in_amts', [])),
                        }
                        results.append(row)
                        
                except Exception as e:
                    print(f"   ❌ Error optimizing {ticker}: {e}")
            
            # Rate limit protection
            time.sleep(0.5)

        return pd.DataFrame(results)

    def get_sector_guess(self, ticker):
        # Deprecated
        return self.get_sector(ticker)

    def analyze_clusters(self, results_df):
        """
        Aggregates results to find 'Meta Strategies' per sector.
        Calculates the "Centroid" (Average Parameters) for the cluster.
        """
        if results_df.empty:
            return {}
            
        summary = {}
        sectors = results_df['Sector'].unique()
        
        for sector in sectors:
            sector_df = results_df[results_df['Sector'] == sector]
            
            avg_return = sector_df['Return'].mean() * 100
            avg_bh = sector_df['Buy_Hold'].mean() * 100
            
            # --- CALCULATE STRATEGY CENTROID ---
            # We extract the first tier of every strategy to find the "Base Aggressiveness"
            sell_trigs = []
            buy_trigs = []
            
            for _, row in sector_df.iterrows():
                # Parse the strings "0.10,0.20" back to list
                try:
                    s_t = float(str(row['Sell_Triggers']).split(',')[0])
                    b_t = float(str(row['Buy_Triggers']).split(',')[0])
                    sell_trigs.append(s_t)
                    buy_trigs.append(b_t)
                except:
                    pass
            
            avg_sell_trigger = np.mean(sell_trigs) if sell_trigs else 0
            avg_buy_trigger = np.mean(buy_trigs) if buy_trigs else 0
            
            # Interpretation
            aggressiveness = "Inv"
            if avg_sell_trigger < 0.10: aggressiveness = "High (Quick Scalp)"
            elif avg_sell_trigger < 0.20: aggressiveness = "Medium (Swing)"
            else: aggressiveness = "Low (Long Term)"
            
            summary[sector] = {
                "Count": len(sector_df),
                "Avg_Allocated_Return": f"{avg_return:.2f}%",
                "Avg_BuyHold_Return": f"{avg_bh:.2f}%",
                "Alpha": f"{(avg_return - avg_bh):.2f}%",
                "Top_Performer": sector_df.loc[sector_df['Return'].idxmax()]['Ticker'],
                "DNA_Centroid": {
                    "Avg_Sell_Trigger": f"{avg_sell_trigger*100:.1f}%",
                    "Avg_Buy_Trigger": f"{avg_buy_trigger*100:.1f}%",
                    "Style": aggressiveness
                }
            }
            
        return summary

if __name__ == "__main__":
    scanner = MarketScanner()
    df = scanner.scan_market()
    print("\n🏆 SCANNED RESULTS:")
    print(df[['Ticker', 'Sector', 'Return', 'Buy_Hold']])
    
    print("\n📊 SECTOR INTELLIGENCE:")
    clusters = scanner.analyze_clusters(df)
    import json
    print(json.dumps(clusters, indent=2))
