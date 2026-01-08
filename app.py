import streamlit as st
from core.database import get_db
from core.models import User
from core.auth import verify_password
import time
from datetime import datetime, timedelta

# Page config must be first
st.set_page_config(
    page_title="FinanceAI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
# --- LOAD CSS ---
def load_css(file_name):
    import time
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("ui/style.css")

def login():
    # Centered Layout Strategy using columns
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-top: 50px; margin-bottom: 30px;" class="slide-up">
            <div style="font-size: 4rem; margin-bottom: 10px;">🧬</div>
            <h1 style="font-size: 3rem; margin-bottom: 0;">FinanceAI</h1>
            <p style="color: #666; font-size: 1.1rem; letter-spacing: 1px;">INSTITUTIONAL GRADE INTELLIGENCE</p>
        </div>
        """, unsafe_allow_html=True)
    
        # Clean Tabs
        tab1, tab2 = st.tabs(["כניסה", "הרשמה"])
        
        with tab1:
            st.markdown("<div class='titan-card slide-up delay-1'>", unsafe_allow_html=True)
            email = st.text_input("דואר אלקטרוני", key="login_email")
            password = st.text_input("סיסמה", type="password", key="login_pass")
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            
            if st.button("התחבר למערכת", use_container_width=True):
                db = next(get_db())
                user = db.query(User).filter(User.email == email).first()
                if user and verify_password(password, user.password_hash):
                    st.session_state['user_id'] = user.id
                    st.session_state['user_email'] = user.email
                    # Set Cookie for 30 days
                    cookie_manager.set("user_id", str(user.id), expires_at=datetime.now() + timedelta(days=30))
                    st.toast("התחברת בהצלחה", icon="🔓")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("פרטי הזדהות שגויים")
            st.markdown("</div>", unsafe_allow_html=True)
                
        with tab2:
            st.markdown("<div class='titan-card slide-up delay-1'>", unsafe_allow_html=True)
            new_email = st.text_input("דואר אלקטרוני", key="signup_email")
            new_password = st.text_input("סיסמה", type="password", key="signup_pass")
            confirm_password = st.text_input("אימות סיסמה", type="password", key="signup_confirm")
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            
            if st.button("יצירת חשבון חדש", use_container_width=True):
                if new_password != confirm_password:
                    st.error("הסיסמאות אינן תואמות")
                    return
                
                db = next(get_db())
                if db.query(User).filter(User.email == new_email).first():
                    st.error("האימייל כבר קיים במערכת")
                    return
                
                from core.auth import get_password_hash
                hashed_pw = get_password_hash(new_password)
                new_user = User(email=new_email, password_hash=hashed_pw)
                db.add(new_user)
                db.commit()
                st.success("החשבון נוצר בהצלחה. כעת ניתן להתחבר.")
            st.markdown("</div>", unsafe_allow_html=True)

import extra_streamlit_components as stx

# Initialize Cookie Manager
# @st.cache_resource (Removed to avoid CachedWidgetWarning)
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

def main():
    # Check for existing session or cookie
    if 'user_id' not in st.session_state:
        # Try to read cookie
        user_id_cookie = cookie_manager.get(cookie="user_id")
        if user_id_cookie:
             # Validate cookie against DB
             db = next(get_db())
             user = db.query(User).filter(User.id == user_id_cookie).first()
             if user:
                 st.session_state['user_id'] = user.id
                 st.session_state['user_email'] = user.email
                 st.rerun()
        
        # Show Login if no valid cookie
        login()
    else:
        # Sidebar Profile
        with st.sidebar:
            st.markdown("""
            <div style="text-align: center; padding: 20px 0;">
                <div style="font-size: 3rem;">👤</div>
                <h3 style="margin-top:10px;">פרופיל אישי</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.info(f"מחובר כ:\n{st.session_state.get('user_email')}")
            
            st.markdown("---")
            if st.button("🚪 התנתק מהמערכת", use_container_width=True):
                cookie_manager.delete("user_id")
                del st.session_state['user_id']
                st.rerun()
            
            st.markdown("<div style='margin-top: 50px; text-align: center; color: #444; font-size: 0.8em;'>FinanceAI v2.5</div>", unsafe_allow_html=True)

        # Main App Logic
        try:
             # Lazy import
            from ui.pages import dashboard
            dashboard.show(st.session_state['user_id'])
        except Exception as e:
            st.error(f"Dashboard module error: {e}")
            import traceback
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
