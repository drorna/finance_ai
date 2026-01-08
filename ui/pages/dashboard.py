import streamlit as st
import pandas as pd
import yfinance as yf
from core.database import get_db
from core.models import Portfolio, Signal, User, Transaction
from quant.strategy import analyze_market_regime, generate_signals, backtest_strategy
from quant.optimizer import optimize_asset
from quant.analysis import analyze_portfolio
from quant.policy_engine import PolicyBacktester
from analyst.gemini_client import generate_daily_report, generate_news_summary
from analyst.news import get_portfolio_news
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def show(user_id):
    # Retrieve DB session
    db = next(get_db())
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.timestamp.desc()).limit(10).all()
    
    # Analyze Data (Quant Engine)
    # market_regime = get_market_regime() # Old mocked function
    
    # Real Strategy Engine
    regime_data = analyze_market_regime()
    market_regime = regime_data.get("regime", "NEUTRAL")
    
    # Run Backtest (Quick check on SPY)
    backtest_res = backtest_strategy(ticker="SPY", period="5y")
    
    # Optimizer Engine (Lazy load for MVP - currently runs on load, ideally should be cached or button triggered)
    # We will trigger it in the UI to save performance.
    
    # Generate Signals
    strategy_signals = generate_signals(portfolio, regime_data)
    
    portfolio_data = analyze_portfolio(portfolio) if portfolio else {}

    # --- HELPER: RENDER DEEP GRIND VIEW ---
    def render_detailed_strategy_view(ticker, df_history, engine_result, unique_key):
        """
        Reusable component to show Strategy DNA, Audit Log, and Simulator.
        """
        best_ret = engine_result.get('best_return', 0) * 100
        best_params = engine_result.get('best_params', {})
        audit_df = engine_result.get('audit_df')
        
        # Compare to Buy & Hold (approx)
        bh_ret = (df_history['Close'].iloc[-1] / df_history['Close'].iloc[0] - 1) * 100
        
        st.markdown(f"### 🏆 אסטרטגיה מנצחת לחברת {ticker} (תשואה: {best_ret:.2f}%)")
        st.caption(f"לעומת החזקה פסיבית (Buy & Hold): {bh_ret:.2f}%")
        
        # Adapt to Multi-Tier Arrays
        s_out_trigs = best_params.get('scale_out_triggers', [])
        s_out_amts = best_params.get('scale_out_amts', [])
        s_in_trigs = best_params.get('scale_in_triggers', [])
        s_in_amts = best_params.get('scale_in_amts', [])
        
        # Helper to display formatted tiers
        def format_tiers(trigs, amts, is_buy=False):
            lines = []
            if len(trigs) == 0: return "ללא פעולות"
            
            for i in range(len(trigs)):
                # Handle array indexing safely
                t = trigs[i] if i < len(trigs) else 0
                a = amts[i] if i < len(amts) else 0
                
                pct_trig = t * 100
                pct_amt = a * 100
                if is_buy:
                        lines.append(f"• ירידה של **{abs(pct_trig):.0f}%** ⬅️ קנה ב-**{pct_amt:.0f}%** מהפוזיציה")
                else:
                        # Check for Stop Loss (Negative Trigger)
                        if t < 0:
                            lines.append(f"• 🛑 ירידה של **{abs(pct_trig):.0f}%** (Stop Loss) ⬅️ מכור **{pct_amt:.0f}%**")
                        else:
                            lines.append(f"• עלייה של **{pct_trig:.0f}%** ⬅️ מכור **{pct_amt:.0f}%** מהכמות")
            return "<br>".join(lines)

        c1, c2 = st.columns(2)
        with c1:
            st.success(f"**💰 לקיחת רווחים (Scale Out):**")
            st.markdown(format_tiers(s_out_trigs, s_out_amts, False), unsafe_allow_html=True)
        with c2:
            st.error(f"**📉 בניה בירידות (Scale In):**")
            st.markdown(format_tiers(s_in_trigs, s_in_amts, True), unsafe_allow_html=True)
        
        st.divider()
        
        # Audit Log (Expandable)
        with st.expander("📊 הצג את כל האסטרטגיות שנבדקו (Audit Log)"):
            st.dataframe(audit_df, use_container_width=True)
        
        # --- WINNING STRATEGY TIMELINE ---
        # We run a quick debug sim using the best parameters to get the specific trade logs
        try:
            debug_eng = PolicyBacktester(ticker, df_history)
            val, best_logs = debug_eng.simulate_policy_debug(
                debug_eng.closes, debug_eng.dates, 10000.0,
                s_out_trigs, s_out_amts, # Use Best Params
                s_in_trigs, s_in_amts,
                0.40
            )
            
            with st.expander("📜 ציר זמן עסקאות (Timeline) - אסטרטגיה מנצחת", expanded=False):
                if best_logs:
                    logs_df = pd.DataFrame(best_logs)
                    st.dataframe(
                        logs_df.style.apply(lambda x: ['background-color: #d4edda' if 'TAKE' in str(r) else 'background-color: #f8d7da' if 'BUY' in str(r) else '' for r in x['Action']], axis=1),
                        use_container_width=True
                    )
                else:
                    st.info("האסטרטגיה המנצחת לא ביצעה פעולות בתקופה זו (Buy & Hold?).")
        except Exception as e:
            st.error(f"Error generating timeline: {e}")

        st.divider()
        
        # --- CUSTOM SIMULATOR (MULTI-TIER) ---
        st.markdown("#### 🧪 סימולטור טקטי (מדרגות)")
        with st.form(f"sim_form_{unique_key}"):
            c_s1, c_s2 = st.columns(2)
            # Input as comma separated strings
            def_s_trigs = ",".join([str(int(x*100)) for x in s_out_trigs])
            def_s_amts = ",".join([str(int(x*100)) for x in s_out_amts])
            def_b_trigs = ",".join([str(int(x*100)) for x in s_in_trigs])
            def_b_amts = ",".join([str(int(x*100)) for x in s_in_amts])
            
            with c_s1:
                st.markdown("**מכירה (Sell)**")
                st.caption("טריגרים חיוביים לרווח, שליליים ל-Stop Loss")
                user_s_trigs_str = st.text_input("Triggers % (e.g. 10,20,-5)", value=def_s_trigs)
                user_s_amts_str = st.text_input("Amounts % (e.g. 50,50,100)", value=def_s_amts)
            with c_s2:
                st.markdown("**קניה (Buy)**")
                st.caption("טריגרים שליליים לקנייה בירידות")
                user_b_trigs_str = st.text_input("Dip Triggers % (e.g. -5,-10)", value=def_b_trigs)
                user_b_amts_str = st.text_input("Buy Amounts % (Position)", value=def_b_amts)
            
            run_sim = st.form_submit_button("הרץ סימולציה אישית")
            
            if run_sim:
                try:
                    # Parse Inputs
                    u_s_t = [float(x.strip())/100 for x in user_s_trigs_str.split(',') if x.strip()]
                    u_s_a = [float(x.strip())/100 for x in user_s_amts_str.split(',') if x.strip()]
                    u_b_t = [float(x.strip())/100 for x in user_b_trigs_str.split(',') if x.strip()]
                    u_b_a = [float(x.strip())/100 for x in user_b_amts_str.split(',') if x.strip()]
                    
                    # Re-init engine just for simulation logic access (static methods mostly)
                    # We need closures/dates from the passed df_history
                    # engine_instance = PolicyBacktester(ticker, df_history) # Already available? No passed in.
                    # We can just use the static method directly but we need data.
                    # We will re-instantiate lightly.
                    temp_engine = PolicyBacktester(ticker, df_history)
                    
                    val, logs = temp_engine.simulate_policy_debug(
                        temp_engine.closes, temp_engine.dates, 10000.0,
                        u_s_t, u_s_a,
                        u_b_t, u_b_a,
                        0.40
                    )
                    sim_ret = (val / 10000.0 - 1) * 100
                    
                    st.markdown(f"**תוצאת הסימולציה:** תשואה של **{sim_ret:.2f}%** (שווי סופי: ${val:.2f})")
                    
                    if logs:
                        logs_df = pd.DataFrame(logs)
                        st.markdown("##### 📜 יומן פעולות (Timeline)")
                        st.dataframe(
                            logs_df.style.apply(lambda x: ['background-color: #d4edda' if 'TAKE' in str(r) else 'background-color: #f8d7da' if 'BUY' in str(r) else '' for r in x['Action']], axis=1),
                            use_container_width=True
                        )
                    else:
                        st.info("לא בוצעו פעולות.")
                except Exception as e:
                    st.error(f"שגיאה בנתונים: {e}")

    
    # Fetch User for Cash Balance
    user_obj = db.query(User).filter(User.id == user_id).first()
    cash_balance = user_obj.cash_balance if user_obj else 0.0

    # Calculate Global Metrics
    total_value = 0
    total_cost = 0
    total_day_change = 0
    
    for asset in portfolio:
        data = portfolio_data.get(asset.symbol, {})
        price = data.get('price', asset.avg_price)
        change = data.get('change', 0)
        
        market_val = price * asset.quantity
        cost_basis = asset.avg_price * asset.quantity
        
        total_value += market_val
        total_cost += cost_basis
        total_day_change += (change * asset.quantity)
        
    total_return = total_value - total_cost
    total_return_pct = (total_return / total_cost * 100) if total_cost > 0 else 0
    total_day_change_pct = (total_day_change / (total_value - total_day_change) * 100) if (total_value - total_day_change) > 0 else 0

    # --- Header ---
    ticker = "SPY"
    regime_color = '#27ae60' if market_regime == 'BULL' else '#c0392b'
    
    st.markdown(f"""
    <div class="slide-up" style="display: flex; justify-content: space-between; align-items: flex-end;">
        <div>
            <h1 style='font-size: 2.5rem; margin-bottom: 0;'>Dashboard</h1>
            <p style='color: #888; font-size: 1rem;'>STRATEGY ENGINE: <span style='color: {regime_color}; font-weight: bold;'>{market_regime} MARKET</span> (Based on {ticker} 200 SMA)</p>
        </div>
        <div style="text-align: right; background: rgba(255,255,255,0.05); padding: 10px 20px; border-radius: 10px; border: 1px solid #333; display: flex; gap: 20px;">
             <div>
                 <div style="font-size: 0.8rem; color: #aaa;">VOLATILITY (VIX)</div>
                 <div style="font-size: 1.2rem; font-weight: bold;">{regime_data.get('volatility', 0):.1f}%</div>
             </div>
             <div style="border-left: 1px solid #444; padding-left: 20px;">
                 <div style="font-size: 0.8rem; color: #aaa;">STRATEGY (5Y)</div>
                 <div style="font-size: 1.2rem; font-weight: bold; color: #D4AF37;">{backtest_res['strategy_return'] if backtest_res else 0:.1f}%</div>
             </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # --- Metrics Row ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class='titan-card'><div style='color:#888; font-size:0.8rem;'>PORTFOLIO VALUE</div><div style='font-size:1.8rem; font-weight:bold;'>${total_value:,.2f}</div></div>""", unsafe_allow_html=True)
    with m2:
        color = "#27ae60" if total_day_change >= 0 else "#c0392b"
        st.markdown(f"""<div class='titan-card'><div style='color:#888; font-size:0.8rem;'>DAILY CHANGE</div><div style='font-size:1.8rem; font-weight:bold; color:{color};'>${total_day_change:,.2f}</div><div style='font-size:0.9rem; color:{color};'>{total_day_change_pct:+.2f}%</div></div>""", unsafe_allow_html=True)
    with m3:
        color_ret = "#27ae60" if total_return >= 0 else "#c0392b"
        st.markdown(f"""<div class='titan-card'><div style='color:#888; font-size:0.8rem;'>TOTAL RETURN</div><div style='font-size:1.8rem; font-weight:bold; color:{color_ret};'>${total_return:,.2f}</div><div style='font-size:0.9rem; color:{color_ret};'>{total_return_pct:+.2f}%</div></div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""<div class='titan-card'><div style='color:#888; font-size:0.8rem;'>CASH BALANCE</div><div style='font-size:1.8rem; font-weight:bold;'>${cash_balance:,.2f}</div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
    
    # --- TABS LAYOUT ---
    tab_overview, tab_journal, tab_intel, tab_opt = st.tabs(["Overview", "Journal & Actions", "Intelligence", "Strategy Lab"])
    
    # --- TAB 1: OVERVIEW ---
    with tab_overview:
        st.markdown("<div class='titan-card slide-up delay-1'>", unsafe_allow_html=True)
        st.markdown("### Portfolio Holdings")
        
        # Table Header
        h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([1.5, 0.8, 1, 1, 1, 1, 1, 1.5])
        h1.markdown("**Symbol**")
        h2.markdown("**Qty**")
        h3.markdown("**Avg Price**")
        h4.markdown("**Live Price**")
        h5.markdown("**Total Val**")
        h6.markdown("**Today**")
        h7.markdown("**Return**")
        h8.markdown("**AI Action**")
        st.markdown("<div style='border-bottom: 1px solid #333; margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        if not portfolio:
            st.info("Your portfolio is empty. Add assets in the 'Journal' tab.")
        else:
            for asset in portfolio:
                rt = portfolio_data.get(asset.symbol, {"price": asset.avg_price, "change": 0, "change_pct": 0, "is_high_volatility": False})
                sig = strategy_signals.get(asset.symbol, {"action": "WAIT", "reason": "No Data"})
                
                live_price = rt['price']
                change_today = rt['change']
                pct_today = rt['change_pct']
                is_volatile = rt.get('is_high_volatility', False)
                
                market_val = live_price * asset.quantity
                total_ret = (live_price - asset.avg_price) * asset.quantity
                total_ret_pct = ((live_price - asset.avg_price) / asset.avg_price * 100) if asset.avg_price else 0
                
                c_today = "#27ae60" if change_today >= 0 else "#c0392b"
                c_total = "#27ae60" if total_ret >= 0 else "#c0392b"
                warning_icon = "⚠️" if is_volatile else ""
                
                # Signal Color
                sig_color = "#f1c40f" # Default Hold
                if "BUY" in sig['action']: sig_color = "#27ae60"
                if "SELL" in sig['action']: sig_color = "#e74c3c"

                r1, r2, r3, r4, r5, r6, r7, r8 = st.columns([1.5, 0.8, 1, 1, 1, 1, 1, 1.5])
                r1.markdown(f"**{asset.symbol}** {warning_icon}")
                r2.write(f"{asset.quantity}")
                r3.write(f"${asset.avg_price:.2f}")
                r4.write(f"${live_price:.2f}")
                r5.markdown(f"**${market_val:,.2f}**")
                r6.markdown(f"<span style='color:{c_today}'>{pct_today:+.2f}%</span>", unsafe_allow_html=True)
                r7.markdown(f"<span style='color:{c_total}'>{total_ret_pct:+.2f}%</span>", unsafe_allow_html=True)
                r8.markdown(f"<span style='color:{sig_color}; font-weight:bold; border:1px solid {sig_color}; padding:2px 8px; border-radius:4px; font-size:0.8rem;' title='{sig['reason']}'>{sig['action']}</span>", unsafe_allow_html=True)
                st.markdown("<div style='border-bottom: 1px solid #1a1a1a; margin: 5px 0;'></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    # --- TAB 2: JOURNAL & ACTIONS ---
    with tab_journal:
        c_actions, c_history = st.columns([1, 1.5])
        
        with c_actions:
            st.markdown("### Action Center")
            
            action_type = st.selectbox("Action Type", ["Buy Asset", "Sell Asset", "Deposit Cash", "Withdraw Cash"])
            
            if action_type == "Deposit Cash":
                 with st.form("deposit_form"):
                     amount = st.number_input("Amount to Deposit", min_value=1.0)
                     submit_dep = st.form_submit_button("Deposit")
                     if submit_dep:
                         user_obj.cash_balance += amount
                         txn = Transaction(user_id=user_id, symbol="CASH", transaction_type="DEPOSIT", quantity=1, price=amount, timestamp=datetime.now())
                         db.add(txn)
                         db.commit()
                         st.success(f"Deposited ${amount:,.2f}")
                         st.rerun()

            elif action_type == "Withdraw Cash":
                 with st.form("withdraw_form"):
                     amount = st.number_input("Amount to Withdraw", min_value=1.0)
                     submit_with = st.form_submit_button("Withdraw")
                     if submit_with:
                         if user_obj.cash_balance >= amount:
                             user_obj.cash_balance -= amount
                             txn = Transaction(user_id=user_id, symbol="CASH", transaction_type="WITHDRAWAL", quantity=1, price=amount, timestamp=datetime.now())
                             db.add(txn)
                             db.commit()
                             st.success(f"Withdrew ${amount:,.2f}")
                             st.rerun()
                         else:
                             st.error(f"Insufficient Funds. Available: ${user_obj.cash_balance:,.2f}")

            elif action_type == "Buy Asset":
                with st.form("buy_form"):
                    symbol = st.text_input("Symbol (e.g. AAPL)").upper()
                    qty = st.number_input("Quantity", min_value=0.01, step=1.0)
                    price = st.number_input("Purchase Price", min_value=0.01, step=0.01)
                    date = st.date_input("Date")
                    submit = st.form_submit_button("Execute Buy")
                    
                    if submit and symbol and qty > 0:
                        total_cost = qty * price
                        if user_obj.cash_balance >= total_cost:
                            # Update Cash
                            user_obj.cash_balance -= total_cost
                            
                            # Update Portfolio
                            existing = db.query(Portfolio).filter(Portfolio.user_id==user_id, Portfolio.symbol==symbol).first()
                            if existing:
                                old_cost = existing.quantity * existing.avg_price
                                new_cost = old_cost + total_cost
                                new_qty = existing.quantity + qty
                                existing.avg_price = new_cost / new_qty
                                existing.quantity = new_qty
                            else:
                                new_asset = Portfolio(user_id=user_id, symbol=symbol, quantity=qty, avg_price=price, purchase_date=date)
                                db.add(new_asset)
                            
                            # Add Transaction
                            txn = Transaction(user_id=user_id, symbol=symbol, transaction_type="BUY", quantity=qty, price=price, timestamp=datetime.now())
                            db.add(txn)
                            db.commit()
                            st.success(f"Bought {qty} {symbol}")
                            st.rerun()
                        else:
                            st.error(f"Insufficient Cash. Balance: ${user_obj.cash_balance:,.2f}")

            elif action_type == "Sell Asset":
                if not portfolio:
                    st.warning("Portfolio is empty.")
                else:
                    my_stocks = [p.symbol for p in portfolio]
                    symbol_to_sell = st.selectbox("Select Asset", my_stocks)
                    
                    asset = db.query(Portfolio).filter(Portfolio.user_id==user_id, Portfolio.symbol==symbol_to_sell).first()
                    current_qty = asset.quantity if asset else 0
                    
                    with st.form("sell_form"):
                        st.info(f"Holding: {current_qty} shares")
                        qty_sell = st.number_input("Quantity to Sell", min_value=0.01, max_value=float(current_qty), step=1.0)
                        price_sell = st.number_input("Sell Price", min_value=0.01, step=0.01)
                        submit_sell = st.form_submit_button("Execute Sell")
                        
                        if submit_sell:
                            sale_value = qty_sell * price_sell
                            
                            # Update Cash
                            user_obj.cash_balance += sale_value
                            
                            if qty_sell == current_qty:
                                db.delete(asset) # Full close
                            else:
                                asset.quantity -= qty_sell
                            
                            # Add Transaction
                            txn = Transaction(user_id=user_id, symbol=symbol_to_sell, transaction_type="SELL", quantity=qty_sell, price=price_sell, timestamp=datetime.now())
                            db.add(txn)
                            db.commit()
                            st.success(f"Sold {qty_sell} {symbol_to_sell}")
                            st.rerun()
            
        with c_history:
             st.markdown("### Transaction Journal")
             if not transactions:
                 st.write("No recent transactions.")
             else:
                 for t in transactions:
                     color = "#27ae60" if t.transaction_type in ["BUY", "DEPOSIT"] else "#c0392b"
                     icon = "📥" if t.transaction_type in ["BUY", "DEPOSIT"] else "📤"
                     
                     c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 0.5])
                     with c1:
                         st.markdown(f"<div><span style='color:{color}; font-weight:bold;'>{icon} {t.transaction_type}</span> <br><b>{t.symbol}</b></div>", unsafe_allow_html=True)
                     with c2:
                         st.write(f"{t.quantity} @ ${t.price}")
                     with c3:
                         st.markdown(f"<div style='color:#666; font-size:0.8rem;'>{t.timestamp.strftime('%d/%m %H:%M')}</div>", unsafe_allow_html=True)
                     with c4:
                         if st.button("🗑️", key=f"del_{t.id}", help="Delete from history"):
                             db.delete(t)
                             db.commit()
                             st.rerun()
                     
                     st.markdown("<div style='border-bottom:1px solid #222; margin-bottom:10px;'></div>", unsafe_allow_html=True)

    # --- TAB 3: INTELLIGENCE ---
    with tab_intel:
        c_news, c_ai = st.columns([1, 1])
        
        with c_news:
            st.markdown("<div class='titan-card slide-up delay-3'>", unsafe_allow_html=True)
            st.markdown("### 📰 Breaking Stock News")
            
            # News Filter
            news_filter = st.selectbox("Time Filter", ["Last 24 Hours", "Last Week", "Last Month"])
            
            # Helper to visualize what we are sending (Debug)
            # st.caption(f"Debug: Active Filter '{news_filter}'") 
            
            symbols = [p.symbol for p in portfolio] if portfolio else []
            news_items = []
            
            # --- News State Management ---
            # Create a unique key for the cache based on filter and symbols
            symbols_hash = "_".join(sorted(symbols)) if symbols else "empty"
            cache_key = f"news_{news_filter}_{symbols_hash}"
            
            if 'news_cache' not in st.session_state:
                st.session_state['news_cache'] = {}
                
            # If we don't have news for this specific filter/symbol combo, fetch it
            if cache_key not in st.session_state['news_cache']:
                 if symbols:
                    with st.spinner("Scanning Web..."):
                        try:
                            full_news = get_portfolio_news(symbols, time_filter=news_filter)
                            st.session_state['news_cache'][cache_key] = full_news[:15] # Store top 15
                        except Exception as e:
                             st.error(f"News error: {e}")
                             st.session_state['news_cache'][cache_key] = []
                 else:
                     st.session_state['news_cache'][cache_key] = []

            # Retrieve from cache
            news_items = st.session_state['news_cache'].get(cache_key, [])
            
            # Force Refresh Button
            if st.button("🔄 Refresh News", key="refresh_news"):
                if symbols:
                     with st.spinner("Refreshing..."):
                        full_news = get_portfolio_news(symbols, time_filter=news_filter)
                        st.session_state['news_cache'][cache_key] = full_news[:15]
                        st.rerun()

            if news_items:
                # Scrollable container
                st.markdown("<div style='max-height: 500px; overflow-y: auto; padding-right: 5px;'>", unsafe_allow_html=True)
                for news in news_items:
                        title = news.get('title', 'No Title')
                        source = news.get('source', 'Unknown')
                        url = news.get('url', '#')
                        date = news.get('date', '')
                        
                        st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                        <a href="{url}" target="_blank" style="text-decoration: none; color: #fff; font-weight: bold; font-size: 0.95rem; display:block; margin-bottom:5px;">{title}</a>
                        <div style="font-size: 0.75rem; color: #888;">{source} • <span style="color: #D4AF37;">{date}</span> (Filter: {news_filter})</div>
                        </div>
                        """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                 if symbols:
                     st.warning("No news found or connection error.")
                 else:
                     st.info("Add assets to see personalized news.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c_ai:
            st.markdown("<div class='titan-card slide-up delay-4'>", unsafe_allow_html=True)
            st.markdown("### 🤖 Chief Investment Officer (AI)")
            
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                 user = db.query(User).filter(User.id == user_id).first()
                 if user and user.gemini_api_key:
                     api_key = user.gemini_api_key
            if not portfolio:
                st.info("Connect assets to activate the AI Analyst.")
            else:
                st.write("Generating insights based on your portfolio and market regime...")
                
                btn_news_sum = st.button("📰 NEWS SUMMARY", use_container_width=True)
                if btn_news_sum:
                    if not api_key:
                        st.error("Missing Gemini API Key.")
                    else:
                        if not news_items:
                            st.info("No gathered news to summarize. Try adding assets or refreshing.")
                        else:
                            with st.spinner("Summarizing headlines..."):
                                summary = generate_news_summary(news_items, api_key=api_key, time_filter=news_filter)
                                st.markdown(f"""
                                <div style="background: rgba(52, 152, 219, 0.1); border: 1px solid rgba(52, 152, 219, 0.3); padding: 15px; border-radius: 10px; margin-top: 15px; color: #e1e1e1; font-size: 0.95rem; line-height: 1.6;">
                                    <h4>📰 Daily Briefing</h4>
                                    {summary}
                                </div>
                                """, unsafe_allow_html=True)
                
                if st.button("🧠 GENERATE STRATEGY REPORT", use_container_width=True):
                    with st.spinner("Analyzing Market Context..."):
                        signals = db.query(Signal).filter(Signal.user_id == user_id).all()
                        try:
                            # Use the persistent news_items variable which now comes from Session State
                            report = generate_daily_report(portfolio, signals, market_regime, api_key=api_key, portfolio_data=portfolio_data, news_context=news_items)
                            st.markdown(f"""
                            <div style="background: rgba(46, 204, 113, 0.1); border: 1px solid rgba(46, 204, 113, 0.3); padding: 15px; border-radius: 10px; margin-top: 15px; color: #e1e1e1; font-size: 0.95rem; line-height: 1.6;">
                                {report}
                            </div>
                            """, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"AI Error: {e}")
                
            st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 4: OPTIMIZATION LAB ---
    with tab_opt:
        st.markdown("### 🧬 Strategy Optimization Lab")
        st.markdown("The system analyzes your assets to find the **mathematically optimal strategy** for each ONE.")
        
        if not portfolio:
            st.info("Add assets to the portfolio to unlock optimization.")
        else:
            # We want to run this only on demand or cached, as it's heavy
            # Optimization Mode Selection
            mode = st.radio("Simulation Mode", ["Standard (Trend/Mean Rev)", "Deep Grind (Policy & Risk Management)"], horizontal=True)
            
            if st.button("🚀 Run Analysis", use_container_width=True):
                progress_bar = st.progress(0)
                
                for i, asset in enumerate(portfolio):
                    with st.spinner(f"Optimizing {asset.symbol}..."):
                        
                        # --- STANDARD MODE ---
                        if "Standard" in mode:
                            result = optimize_asset(asset.symbol)
                            fundamentals = result.get('fundamentals', {})
                            opt_res = result.get('optimization', {})
                            
                            with st.expander(f"🧬 {asset.symbol} Analysis", expanded=True):
                                c1, c2 = st.columns([1, 2])
                                with c1:
                                    st.markdown("#### 🆔 Profile")
                                    st.markdown(f"**Sector:** {fundamentals.get('sector')}")
                                    st.markdown(f"**Size:** {fundamentals.get('size')}")
                                    st.markdown(f"**Health:** {fundamentals.get('health')}")
                                    st.markdown(f"**Volatility:** {fundamentals.get('volatility')} (Beta: {fundamentals.get('beta'):.2f})")
                                with c2:
                                    st.markdown("#### 🏆 Optimal Strategy")
                                    if opt_res:
                                        strat_name = opt_res.get('strategy_name')
                                        strat_ret = opt_res.get('return', 0) * 100
                                        bh_ret = opt_res.get('buy_hold_return', 0) * 100
                                        params = opt_res.get('params', {})
                                        color = "#27ae60" if strat_ret > bh_ret else "#f39c12"
                                        st.markdown(f"<div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; border-left: 4px solid {color};'>"
                                                    f"<h3 style='margin:0; color:{color};'>{strat_name}</h3>"
                                                    f"<p style='margin:5px 0 0 0;'>Calculated Return: <b>{strat_ret:.2f}%</b> (vs Buy & Hold: {bh_ret:.2f}%)</p>"
                                                    f"</div>", unsafe_allow_html=True)
                                        st.markdown("**Winning Parameters:**")
                                        st.json(params)
                                    else:
                                        st.warning("Not enough data.")

                        # --- DEEP GRIND MODE ---
                        else:
                            # Fetch Data manually for the Engine
                            stock = yf.Ticker(asset.symbol)
                            df = stock.history(period="2y") # 2 Years for deep grind
                            
                            if len(df) > 100:
                                engine = PolicyBacktester(asset.symbol, df)
                                result = engine.run_exhaustive_optimization(audit_mode=True)
                                
                                best_ret = result.get('best_return', 0) * 100
                                best_params = result.get('best_params', {})
                                audit_df = result.get('audit_df')
                                
                                # Compare to Buy & Hold (approx)
                                bh_ret = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
                                

                            if len(df) > 100:
                                engine = PolicyBacktester(asset.symbol, df)
                                result = engine.run_exhaustive_optimization(audit_mode=True)
                                
                                with st.expander(f"🧬 {asset.symbol} Deep Grind Results", expanded=True):
                                     render_detailed_strategy_view(asset.symbol, df, result, f"port_{asset.symbol}")

                            else:
                                st.error(f"Insufficient data for {asset.symbol}")
                    
                    progress_bar.progress((i + 1) / len(portfolio))
                
                st.success("Analysis Complete!")

        st.divider()
        
        # --- MARKET SCANNER SECTION ---
        st.markdown("### 🌍 Global Market Scanner (Cross-Sectional Analysis)")
        st.info("This module scans a universe of stocks to find 'Meta-Strategies' for each sector.")
        
        # User control for scan size
        col_scan1, col_scan2, col_scan3 = st.columns(3)
        with col_scan1:
             # Load available sectors using absolute path or robust method
             try:
                 # Check current dir
                 if os.path.exists("sp500.csv"):
                     sp500 = pd.read_csv("sp500.csv")
                 else:
                     # Fallback to project root
                     project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                     sp500 = pd.read_csv(os.path.join(project_root, "sp500.csv"))
                     
                 all_sectors = sorted([str(s) for s in sp500['Sector'].unique().tolist() if str(s) != 'nan'])
             except Exception as e:
                 st.error(f"Error loading sectors: {e}")
                 all_sectors = []
             
             sel_sectors = st.multiselect("סינון לפי סקטורים:", all_sectors, default=None, placeholder="כל השוק")
        
        with col_scan2:
             sel_vol = st.selectbox("רמת תנודתיות:", ["Any", "Low (Stable)", "Medium", "High (Volatile)"])
             vol_param = sel_vol.split(' ')[0] if sel_vol != "Any" else None
             
        with col_scan3:
            st.write("") # Spacer
            # User accepted full scan logic. We set safety limit to 500 (Full S&P)
            scan_limit = 500 
            btn_scan = st.button("🔭 הרץ סריקה חכמה", use_container_width=True)
        
        if btn_scan:
             from quant.market_scanner import MarketScanner
             scanner = MarketScanner()

             prog_bar = st.progress(0)
             status_text = st.empty()

             def update_progress(p):
                 prog_bar.progress(p)
                 status_text.text(f"Scanning Market... {int(p*100)}%")

             # Run Scan
             results_df = scanner.scan_market(sectors=sel_sectors, volatility=vol_param, limit=scan_limit, progress_callback=update_progress)

             if results_df.empty:
                 st.warning("לא נמצאו מניות העונות לקריטריונים.")
                 st.session_state.scanner_results = None
                 st.session_state.scanner_clusters = None
             else:
                 clusters = scanner.analyze_clusters(results_df)

                 # שמירת התוצאות ב-session_state
                 st.session_state.scanner_results = results_df
                 st.session_state.scanner_clusters = clusters

                 st.success(f"Scan Complete! Processed {len(results_df)} stocks.")
                 status_text.empty()

        # --- DISPLAY RESULTS FROM SESSION STATE ---
        # תצוגת התוצאות - עובד גם אחרי rerun!
        if 'scanner_results' in st.session_state and st.session_state.scanner_results is not None:
            results_df = st.session_state.scanner_results
            clusters = st.session_state.scanner_clusters

            # Import scanner for drill-down feature
            from quant.market_scanner import MarketScanner
            scanner = MarketScanner()

            # --- DISPLAY CLUSTERS (HEBREW UX) ---
            st.markdown("#### 🧠 תובנות סקטוריאליות (Sector Intelligence)")

            for sector, data in clusters.items():
                dna = data.get('DNA_Centroid', {})
                alpha = data.get('Alpha')

                # Translate Sector Names (Basic Mapping)
                sector_he = sector
                sector_map = {
                    'Information Technology': 'טכנולוגיה', 'Health Care': 'בריאות',
                    'Financials': 'פיננסים', 'Consumer Discretionary': 'צריכה מחזורית',
                    'Communication Services': 'תקשורת', 'Industrials': 'תעשייה',
                    'Consumer Staples': 'צריכה בסיסית', 'Energy': 'אנרגיה',
                    'Utilities': 'תשתיות', 'Real Estate': 'נדל"ן', 'Materials': 'חומרי גלם'
                }
                if sector in sector_map: sector_he = sector_map[sector]

                with st.expander(f"📂 {sector_he} (תוספת תשואה: {alpha})", expanded=False):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("ממוצע טריגר מכירה", dna.get('Avg_Sell_Trigger'))
                    c2.metric("ממוצע קנייה בירידה", dna.get('Avg_Buy_Trigger'))
                    c3.metric("סגנון מסחר", dna.get('Style'))

            st.divider()
            # --- FULL RESULTS TABLE ---
            st.markdown("#### 📜 תוצאות הסריקה המלאות")
            st.info("💡 לחץ על שורה בטבלה כדי לראות ניתוח עומק וציר זמן")

            # Helper to describe strategy in Hebrew
            def describe_strat(row):
                try:
                    # Sell Parsing
                    s_triggers = [float(x) for x in str(row['Sell_Triggers']).split(',') if x]
                    if not s_triggers: return "ללא מכירה"
                    first_sell = s_triggers[0]
                    
                    if len(s_triggers) > 2:
                        desc = "סולם מימושים (Ladder)"
                    elif len(s_triggers) == 1 and first_sell > 0.25:
                        desc = "Moonbag (יעד רחוק)"
                    elif first_sell < 0.08:
                        desc = "קציר מהיר (Scalping)"
                    else:
                        desc = "מימוש סטנדרטי"
                        
                    # Buy Parsing
                    b_triggers = [float(x) for x in str(row['Buy_Triggers']).split(',') if x]
                    if b_triggers:
                         if len(b_triggers) > 2: desc += " + אגירה (Martingale)"
                         elif abs(b_triggers[0]) > 0.15: desc += " + קניית עומק"
                         else: desc += " + קנייה דינמית"
                         
                    return desc
                except:
                    return "מותאם אישית"

            # Rename for Display
            display_df = results_df.copy()
            display_df['תיאור האסטרטגיה'] = display_df.apply(describe_strat, axis=1)
            
            display_df = display_df.rename(columns={
                'Ticker': 'סימול',
                'Sector': 'סקטור',
                'Return': 'תשואת אסטרטגיה',
                'Buy_Hold': 'תשואת שוק'
            })
            # Format as %
            display_df['תשואת אסטרטגיה'] = display_df['תשואת אסטרטגיה'].apply(lambda x: f"{x*100:.2f}%")
            display_df['תשואת שוק'] = display_df['תשואת שוק'].apply(lambda x: f"{x*100:.2f}%")
            
            # INTERACTIVE TABLE
            event = st.dataframe(
                display_df[['סימול', 'סקטור', 'תיאור האסטרטגיה', 'תשואת אסטרטגיה', 'תשואת שוק']],
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            selected_rows = event.selection.rows
            selected_ticker = None
            if selected_rows:
                idx = selected_rows[0]
                selected_ticker = display_df.iloc[idx]['סימול']

            # --- DRILL DOWN FEATURE ---
            st.divider()
            st.subheader("🔍 מעבדה: ניתוח עומק למניה")
            
            # Logic for auto-analysis if row clicked
            if selected_ticker:
                st.markdown(f"**נבחרה מניה:** `{selected_ticker}`")
                if st.button(f"הצג דוח מלא עבור {selected_ticker}", type="primary"):
                    with st.spinner(f"מבצע Deep Grind על {selected_ticker}..."):
                         stock_data = scanner.fetch_data(selected_ticker)
                         if stock_data is not None:
                              engine = PolicyBacktester(selected_ticker, stock_data)
                              result = engine.run_exhaustive_optimization(audit_mode=True)
                              
                              render_detailed_strategy_view(selected_ticker, stock_data, result, f"scan_{selected_ticker}")
                              st.success("הניתוח הושלם. גלול למעלה לציר הזמן.")
                         else:
                              st.error("לא ניתן למשוך נתונים.")
            else:
                st.info("בחר מניה מהטבלה למעלה כדי להתחיל.")
