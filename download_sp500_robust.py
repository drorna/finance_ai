import pandas as pd
import requests
import io

def download_sp500():
    print("Downloading reliable S&P 500 list from GitHub (datasets/s-and-p-500-companies)...")
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse
        df = pd.read_csv(io.StringIO(response.text))
        
        # Normalize columns
        # Expected: Symbol, Name, Sector
        # GitHub might have: Symbol, Security, GICS Sector
        df = df.rename(columns={'Security': 'Name', 'GICS Sector': 'Sector'})
        
        # Fix Symbols (BRK.B -> BRK-B)
        df['Symbol'] = df['Symbol'].str.replace('.', '-', regex=False)
        
        # Save
        df.to_csv('sp500.csv', index=False)
        print(f"✅ Success! Saved {len(df)} tickers to sp500.csv")
        
    except Exception as e:
        print(f"❌ Error downloading: {e}")

if __name__ == "__main__":
    download_sp500()
