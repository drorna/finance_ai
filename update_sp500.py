import pandas as pd
import requests

def update_sp500():
    print("Fetching S&P 500 list from Wikipedia...")
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        df = tables[0]
        
        # Select relevant columns
        df = df[['Symbol', 'Security', 'GICS Sector']]
        df.columns = ['Symbol', 'Name', 'Sector']
        
        # Clean Symbol (Replace . with -)
        df['Symbol'] = df['Symbol'].str.replace('.', '-')
        
        # Save
        df.to_csv('sp500.csv', index=False)
        print(f"✅ Success! Saved {len(df)} tickers to sp500.csv")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_sp500()
