import streamlit as st
import pandas as pd
import time
import io
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import hashlib

# -------------------------------------------------
# CONFIGURATION
# -------------------------------------------------
class Config:
    PAGE_TITLE = "FMN Order Status Assistant AI"
    PAGE_ICON = "🤖"
    SHEET_NAME = "salesline_chatbot"
    MAX_LOGIN_ATTEMPTS = 3
    SESSION_TIMEOUT_MINUTES = 15
    CACHE_TTL_SECONDS = 300  # 5 minutes

# -------------------------------------------------
# SESSION MANAGEMENT
# -------------------------------------------------
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "stage": "name",
        "customer_name": "",
        "order_id": "",
        "login_attempts": 0,
        "last_activity": datetime.now(),
        "order_history": [],
        "blocked_until": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def check_session_timeout():
    """Check if session has timed out"""
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=Config.SESSION_TIMEOUT_MINUTES):
        reset_session()
        st.warning(f"⏰ Session timed out after {Config.SESSION_TIMEOUT_MINUTES} minutes of inactivity. Please start again.")
        return True
    st.session_state.last_activity = datetime.now()
    return False

def reset_session():
    """Reset session to initial state"""
    st.session_state.stage = "name"
    st.session_state.customer_name = ""
    st.session_state.order_id = ""
    st.session_state.login_attempts = 0
    st.session_state.order_history = []

def check_rate_limit():
    """Check if user is temporarily blocked due to failed attempts"""
    if st.session_state.blocked_until:
        if datetime.now() < st.session_state.blocked_until:
            remaining = (st.session_state.blocked_until - datetime.now()).seconds
            return True, remaining
        else:
            st.session_state.blocked_until = None
            st.session_state.login_attempts = 0
    return False, 0

# -------------------------------------------------
# DATA LOADING
# -------------------------------------------------
@st.cache_data(ttl=Config.CACHE_TTL_SECONDS, show_spinner=False)
def load_data():
    """Load data from Google Sheets with fallback to embedded CSV"""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        gc = gspread.authorize(creds)
        sheet = gc.open(Config.SHEET_NAME).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        st.success("✅ Connected to live Google Sheets data", icon="🔄")

    except Exception as e:
        st.warning("⚠️ Using cached data - Google Sheets unavailable")
        
        DATA_CSV_STRING = """recid,Sales order,Inventory Unit,Order Status,Delivery Date,Invoice account,Delivery address Name,Mode of delivery,Delivery terms,Item number,Net amount,Product name,Quantity Order,Requested receipt date,Requested ship date,Unit price,Quantity,Unit,Shipping Date,modifieddatetime,modifiedby,createddatetime,createdby
5637945894,SAP0014689,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:39,Iekwuazi,11/4/25 17:33,Iekwuazi
5637945893,SAP0014688,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:37,Iekwuazi,11/4/25 17:31,Iekwuazi
5637945892,SAP0014687,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:36,Iekwuazi,11/4/25 17:29,Iekwuazi"""
        
        df = pd.read_csv(io.StringIO(DATA_CSV_STRING))

    # Data cleaning
    df = df.fillna("N/A")
    
    if "Sales order" in df.columns:
        df["Sales order"] = df["Sales order"].astype(str).str.strip().str.upper()
    
    if "Invoice account" in df.columns:
        df["Invoice account"] = df["Invoice account"].astype(str).str.strip().str.upper()

    return df

def refresh_data():
    """Force refresh cached data"""
    load_data.clear()
    st.rerun()

# -------------------------------------------------
# INPUT SANITIZATION
# -------------------------------------------------
def sanitize_input(text):
    """Sanitize user input to prevent injection attacks"""
    if not text:
        return ""
    # Remove any potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", ';', '&', '|']
    sanitized = text.strip()
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    return sanitized

# -------------------------------------------------
# ORDER LOOKUP LOGIC
# -------------------------------------------------
class OrderManager:
    @staticmethod
    def find_order_details(order_id, invoice_account, df):
        """Find order with two-factor verification"""
        order_clean = sanitize_input(order_id).upper()
        invoice_clean = sanitize_input(invoice_account).upper()
        
        if not order_clean or not invoice_clean:
            return "invalid_input"
        
        # Filter by both Sales Order and Invoice Account
        rows = df[(df["Sales order"] == order_clean) & (df["Invoice account"] == invoice_clean)]

        if rows.empty:
            # Check if order exists but invoice doesn't match
            order_exists = df[df["Sales order"] == order_clean]
            if not order_exists.empty:
                return "invalid_invoice"
            return None
        
        return rows

    @staticmethod
    def get_order_summary(order_df):
        """Generate order summary statistics"""
        return {
            "total_items": len(order_df),
            "total_amount": order_df['Net amount'].astype(float).sum(),
            "total_quantity": order_df['Quantity Order'].astype(float).sum(),
            "order_status": order_df.iloc[0]['Order Status'],
            "delivery_date": order_df.iloc[0]['Delivery Date']
        }

# -------------------------------------------------
# UI COMPONENTS
# -------------------------------------------------
def render_progress_indicator(current_stage):
    """Display progress through the verification stages"""
    stages = {
        "name": 1,
        "order": 2,
        "validate": 3
    }
    
    current = stages.get(current_stage, 1)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if current >= 1:
            st.success("✅ Step 1: Identity")
        else:
            st.info("1️⃣ Step 1: Identity")
    
    with col2:
        if current >= 2:
            st.success("✅ Step 2: Order ID")
        else:
            st.info("2️⃣ Step 2: Order ID")
    
    with col3:
        if current >= 3:
            st.success("✅ Step 3: Verification")
        else:
            st.info("3️⃣ Step 3: Verification")
    
    st.markdown("---")

def display_order_details(order_df, customer_name):
    """Enhanced order details display"""
    first_row = order_df.iloc[0]
    order_id = first_row['Sales order']
    summary = OrderManager.get_order_summary(order_df)
    
    st.success(f"### 🎉 Order Found for {customer_name}!")
    st.write(f"**Sales Order:** {order_id} | **Status:** {summary['order_status']}")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Items", summary['total_items'])
    with col2:
        st.metric("Total Amount", f"₦{summary['total_amount']:,.2f}")
    with col3:
        st.metric("Total Quantity", f"{summary['total_quantity']:,.0f}")
    with col4:
        st.metric("Delivery Date", summary['delivery_date'])
    
    st.markdown("---")
    
    # Order Information
    with st.expander("📋 Order Information", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**Invoice Account:** {first_row['Invoice account']}")
            st.write(f"**Delivery Address:** {first_row['Delivery address Name']}")
            st.write(f"**Mode of Delivery:** {first_row['Mode of delivery']}")
        with col_b:
            st.write(f"**Delivery Terms:** {first_row['Delivery terms']}")
            st.write(f"**Shipping Date:** {first_row['Shipping Date']}")
            st.write(f"**Inventory Unit:** {first_row['Inventory Unit']}")
    
    # Line Items
    st.markdown("### 📦 Order Line Items")
    
    for idx, (_, item) in enumerate(order_df.iterrows(), 1):
        with st.expander(f"Item {idx}: {item['Product name']}", expanded=idx == 1):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**Product Details**")
                st.write(f"Item Number: `{item['Item number']}`")
                st.write(f"Product: {item['Product name']}")
            
            with col2:
                st.write("**Quantity & Pricing**")
                st.write(f"Quantity: **{item['Quantity Order']} {item['Unit']}**")
                st.write(f"Unit Price: ₦{float(item['Unit price']):,.2f}")
                st.write(f"Net Amount: **₦{float(item['Net amount']):,.2f}**")
            
            with col3:
                st.write("**Important Dates**")
                st.write(f"Receipt Date: {item['Requested receipt date']}")
                st.write(f"Ship Date: {item['Requested ship date']}")
    
    # Add to order history
    if order_id not in [o['order_id'] for o in st.session_state.order_history]:
        st.session_state.order_history.append({
            'order_id': order_id,
            'timestamp': datetime.now(),
            'items': summary['total_items'],
            'amount': summary['total_amount']
        })

def display_order_history():
    """Display previously checked orders in this session"""
    if st.session_state.order_history:
        with st.sidebar.expander("📜 Session History", expanded=False):
            for order in st.session_state.order_history:
                st.write(f"**{order['order_id']}**")
                st.caption(f"{order['items']} items | ₦{order['amount']:,.2f}")
                st.caption(f"Checked: {order['timestamp'].strftime('%H:%M:%S')}")
                st.markdown("---")

# -------------------------------------------------
# MAIN APPLICATION
# -------------------------------------------------
def main():
    st.set_page_config(
        page_title=Config.PAGE_TITLE,
        layout="wide",
        page_icon=Config.PAGE_ICON
    )
    
    # Initialize session
    init_session_state()
    
    # Check for session timeout
    if check_session_timeout():
        return
    
    # Header
    st.title(f"{Config.PAGE_ICON} FMN Order Status Assistant AI")
    st.caption("Secure order verification system with real-time delivery insights")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ System Info")
        if st.button("🔄 Refresh Data"):
            refresh_data()
        
        st.info(f"Session timeout: {Config.SESSION_TIMEOUT_MINUTES} min")
        
        if st.session_state.customer_name:
            st.success(f"👤 {st.session_state.customer_name}")
        
        display_order_history()
        
        if st.button("🔴 End Session"):
            reset_session()
            st.rerun()
    
    # Load data
    df = load_data()
    
    if df.empty:
        st.error("❌ Unable to load order data. Please contact support.")
        return
    
    # Progress indicator
    render_progress_indicator(st.session_state.stage)
    
    # Check rate limiting
    is_blocked, remaining_time = check_rate_limit()
    if is_blocked:
        st.error(f"🚫 Too many failed attempts. Please wait {remaining_time} seconds before trying again.")
        return
    
    # Stage 1: Name Input
    if st.session_state.stage == "name":
        st.header("👋 Welcome! Let's Get Started")
        st.write("To ensure secure access to your order information, please identify yourself.")
        
        name = st.text_input("Enter your full name:", max_chars=100, placeholder="e.g., John Doe")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Continue ➡️", type="primary"):
                name_clean = sanitize_input(name)
                if len(name_clean) < 2:
                    st.error("Please enter a valid name (at least 2 characters).")
                else:
                    st.session_state.customer_name = name_clean
                    st.session_state.stage = "order"
                    st.rerun()
    
    # Stage 2: Order ID Input
    elif st.session_state.stage == "order":
        st.header(f"👋 Hello, {st.session_state.customer_name}!")
        st.write("Please provide your Sales Order ID to proceed.")
        
        order_id = st.text_input("Sales Order ID:", max_chars=50, placeholder="e.g., SAP0014689")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Continue ➡️", type="primary"):
                order_clean = sanitize_input(order_id)
                if len(order_clean) < 3:
                    st.error("Please enter a valid order ID (at least 3 characters).")
                else:
                    st.session_state.order_id = order_clean
                    st.session_state.stage = "validate"
                    st.rerun()
        
        with col2:
            if st.button("⬅️ Back"):
                st.session_state.stage = "name"
                st.rerun()
    
    # Stage 3: Invoice Verification
    elif st.session_state.stage == "validate":
        st.header("🔒 Security Verification Required")
        st.info(f"**Order ID:** {st.session_state.order_id}")
        st.write("For security purposes, please confirm your Invoice Account ID.")
        
        if st.session_state.login_attempts > 0:
            st.warning(f"⚠️ Failed attempts: {st.session_state.login_attempts}/{Config.MAX_LOGIN_ATTEMPTS}")
        
        invoice_account = st.text_input("Invoice Account ID:", max_chars=50, placeholder="e.g., C28402-B0")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🔍 Verify & View", type="primary"):
                invoice_clean = sanitize_input(invoice_account)
                
                if len(invoice_clean) < 2:
                    st.error("Please enter a valid Invoice Account ID.")
                else:
                    with st.spinner("🔄 Verifying credentials..."):
                        time.sleep(1)
                        result = OrderManager.find_order_details(
                            st.session_state.order_id,
                            invoice_clean,
                            df
                        )
                    
                    if isinstance(result, pd.DataFrame):
                        # Success
                        st.session_state.login_attempts = 0
                        display_order_details(result, st.session_state.customer_name)
                        
                        st.markdown("---")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("🔍 Check Another Order"):
                                st.session_state.stage = "order"
                                st.session_state.order_id = ""
                                st.rerun()
                        with col_b:
                            if st.button("🏠 Start Over"):
                                reset_session()
                                st.rerun()
                    
                    elif result == "invalid_invoice":
                        st.session_state.login_attempts += 1
                        
                        if st.session_state.login_attempts >= Config.MAX_LOGIN_ATTEMPTS:
                            st.session_state.blocked_until = datetime.now() + timedelta(minutes=5)
                            st.error("🚫 Maximum attempts exceeded. Account temporarily locked for 5 minutes.")
                        else:
                            st.error(f"❌ Invoice Account Mismatch! The credentials don't match our records.")
                            st.info("💡 Please verify your Invoice Account ID and try again.")
                    
                    elif result == "invalid_input":
                        st.error("❌ Invalid input detected. Please check your entries.")
                    
                    else:
                        st.session_state.login_attempts += 1
                        st.error(f"❌ Order not found: **{st.session_state.order_id}**")
                        st.info("💡 Please verify the order number and try again.")
        
        with col2:
            if st.button("⬅️ Back"):
                st.session_state.stage = "order"
                st.session_state.login_attempts = 0
                st.rerun()

if __name__ == "__main__":
    main()
