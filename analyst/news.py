from duckduckgo_search import DDGS

def get_financial_news(query=None, symbols=None, time_filter="Last 24 Hours", max_results=5):
    """
    Searches for financial news using DuckDuckGo.
    
    Args:
        query (str, optional): A general search query. If symbols are provided, this might be ignored or combined.
        symbols (list of str, optional): A list of stock symbols to search for.
        time_filter (str): UI time filter string (e.g., "Last 24 Hours", "Last Week", "Last Month").
        max_results (int): Maximum number of news results to return.
    """
    # Map UI filter to DDGS format: 'd' (day), 'w' (week), 'm' (month)
    time_map = {
        "Last 24 Hours": "d",
        "Last Week": "w",
        "Last Month": "m"
    }
    tf_code = time_map.get(time_filter, "d")
    
    news_items = []
    
    try:
        # Construct a more specific query if symbols are provided
        if symbols:
            search_query = f"{' '.join(symbols)} stock news finance market"
        elif query:
            search_query = query
        else:
            # Fallback if neither symbols nor query is provided
            search_query = "Stock Market News Finance Economy"
            
        # Use the 'timelimit' parameter in DDGS
        # Fetch more results to allow for better filtering/diversity
        limit_request = 20 if tf_code == 'm' else 10
        print(f"DEBUG: Fetching {limit_request} items for query='{search_query}' with timelimit='{tf_code}'")
        
        results = DDGS().news(keywords=search_query, region="wt-wt", safesearch="off", timelimit=tf_code, max_results=limit_request)
        return results
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def get_market_news(time_filter="Last 24 Hours"):
    """
    General market news.
    """
    return get_financial_news("Stock Market News Finance Economy", max_results=5)

def get_portfolio_news(portfolio_symbols, time_filter="Last 24 Hours"):
    """
    News specific to the portfolio.
    """
    if not portfolio_symbols:
        return []
    
    query = " ".join(portfolio_symbols) + " stock news"
    return get_financial_news(query, symbols=portfolio_symbols, time_filter=time_filter, max_results=7)
