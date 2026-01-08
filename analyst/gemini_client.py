import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from google.api_core import exceptions

# ... imports ...

def configure_gemini(api_key=None):
    key = api_key or GEMINI_API_KEY
    if key:
        genai.configure(api_key=key)
        return True
    return False

@retry(
    retry=retry_if_exception_type(exceptions.ResourceExhausted),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3) # Reduce to 3 to not hang too long if quota is 0
)
def generate_content_with_retry(model, prompt):
    return model.generate_content(prompt)

def generate_daily_report(user_portfolio, signals, market_regime, api_key=None, portfolio_data=None, news_context=None):
    """
    Generates a Hebrew report using Gemini, incorporating risk metrics and news.
    """
    # Ensure configuration is set with the best available key
    if not configure_gemini(api_key):
         return "שגיאה: מפתח Gemini לא נמצא (API Key Missing)."
        
    try:
        # Switching to gemini-flash-latest as it is confirmed working for this key
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Construct the prompt with RISK Data
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        portfolio_summary = ""
        for p in user_portfolio:
            data = portfolio_data.get(p.symbol, {}) if portfolio_data else {}
            atr = data.get('atr', 0)
            is_volatile = data.get('is_high_volatility', False)
            vol_msg = "[⚠️ HIGH VOLATILITY]" if is_volatile else ""
            
            portfolio_summary += f"- {p.symbol}: {p.quantity} shares @ ${p.avg_price}. Risk: ATR={atr:.2f} {vol_msg}\n"

        signals_summary = "\n".join([f"- {s.symbol}: {s.signal_type} ({s.reason})" for s in signals])
        
        msg_news = "אין חדשות מיוחדות כרגע."
        news_summary = ""
        if news_context:
            msg_news = "להלן כותרות החדשות שאספתי עבורך:"
            for n in news_context[:5]:
                news_summary += f"- {n.get('title')} ({n.get('source')})\n"
        
        prompt = f"""
        אתה אנליסט מומחה לניהול סיכונים (Risk Management) ב-FinanceAI.
        תאריך ושעה נוכחיים: {current_date}.
        מצב השוק הנוכחי: {market_regime} (BULL/BEAR).
        
        חדשות חמות (Context):
        {news_summary}
        
        תיק השקעות:
        {portfolio_summary}
        
        בצע ניתוח ב-2 חלקים נפרדים וברורים (השתמש בכותרות בולטות):

        ## 📰 סיכום חדשות יומי
        {msg_news}
        (סכם בקצרה (עד 3 משפטים) את ההשפעה של החדשות הנ"ל על השוק או המניות בתיק).

        ## 🛡️ ניתוח סיכונים ותיק השקעות
        (כאן תנתח את המניות, התנודתיות, וההמלצות שלך. התייחס למניות HIGH VOLATILITY).
        (סכם בשפה מקצועית ועשירה).
        """
        
        # Use the retry-wrapped function
        response = generate_content_with_retry(model, prompt)
        return response.text
    except RetryError:
         return "⚠️ שגיאת גישה ל-AI: המכסה היומית/דקתית הסתיימה או שהמודל חסום. אנא נסה שוב מאוחר יותר."
    except exceptions.ResourceExhausted:
         return "השרת עמוס כרגע (Rate Limit). אנא נסה שוב בעוד מספר שניות."
    except Exception as e:
        return f"שגיאה ביצירת דוח: {str(e)}"


            
def generate_news_summary(news_context, api_key=None, time_filter="Last 24 Hours"):
    """
    Generates a concise news summary using Gemini.
    """
    if not configure_gemini(api_key):
        return "Missing API Key"
        
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        
        from datetime import datetime
        current_date_obj = datetime.now()
        current_date = current_date_obj.strftime("%Y-%m-%d")
        
        news_list = ""
        for n in news_context:
            date_str = n.get('date', 'Unknown Date')
            news_list += f"- [Date: {date_str}] {n.get('title')} ({n.get('source')})\n"
            
        prompt = f"""
        התאריך היום: {current_date}
        טווח הזמן שנבחר: {time_filter}
        
        להלן רשימת חדשות (שים לב לתאריכים בסוגריים!):
        {news_list}
        
        עליך לכתוב סיכום **כרונולוגי ומדויק**:
        1. **אסור** לכתוב "היום" או "כרגע" על אירוע שקרה לפני שבוע.
        2. עבור כל אירוע שאתה מזכיר, ציין מתי הוא קרה (למשל: "בתחילת החודש...", "לפני שבועיים...", "אתמול...").
        3. אם טווח הזמן הוא חודשי/שבועי, תאר את *המגמה* שנוצרה לאורך התקופה, ולא רק אוסף כותרות.
        4. היה קריטי: אם יש חדשות סותרות (עליות ואז ירידות), הסבר את סדר האירועים.
        """
        
        response = generate_content_with_retry(model, prompt)
        return response.text
    except Exception as e:
        return f"News Summary Error: {e}"
