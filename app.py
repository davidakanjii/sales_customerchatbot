import streamlit as st
import pandas as pd
import time
import io
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="FMN Order Status Assistant AI",
    layout="wide",
    page_icon="🤖"
)

# FMN Brand Colors
FMN_COLORS = {
    "primary_green": "#076401",
    "primary_orange": "#FD7601",
    "primary_red": "#D22622",
    "accent_green": "#92BC0C",
    "accent_blue": "#599BD4",
    "accent_yellow": "#F9EF10",
    "secondary_orange": "#FFC102",
    "navy_blue": "#19365E",
    "background": "#FFFFFF"
}

# Custom CSS for FMN branding
st.markdown(f"""
    <style>
    /* Main title styling */
    h1 {{
        color: {FMN_COLORS['navy_blue']} !important;
    }}
    
    /* Subheaders */
    h2, h3 {{
        color: {FMN_COLORS['navy_blue']} !important;
    }}
    
    /* Primary buttons */
    .stButton > button[kind="primary"] {{
        background-color: {FMN_COLORS['primary_orange']} !important;
        color: white !important;
        border: none !important;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background-color: {FMN_COLORS['secondary_orange']} !important;
    }}
    
    /* Regular buttons */
    .stButton > button {{
        color: {FMN_COLORS['navy_blue']} !important;
        border: 2px solid {FMN_COLORS['primary_green']} !important;
    }}
    
    .stButton > button:hover {{
        background-color: {FMN_COLORS['accent_green']} !important;
        color: white !important;
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background-color: #f8f9fa;
    }}
    
    /* Success messages */
    .stSuccess {{
        background-color: {FMN_COLORS['primary_green']}20 !important;
        border-left: 4px solid {FMN_COLORS['primary_green']} !important;
    }}
    
    /* Warning messages */
    .stWarning {{
        background-color: {FMN_COLORS['primary_orange']}20 !important;
        border-left: 4px solid {FMN_COLORS['primary_orange']} !important;
    }}
    
    /* Error messages */
    .stError {{
        background-color: {FMN_COLORS['primary_red']}20 !important;
        border-left: 4px solid {FMN_COLORS['primary_red']} !important;
    }}
    
    /* Info boxes */
    .stInfo {{
        background-color: {FMN_COLORS['accent_blue']}20 !important;
        border-left: 4px solid {FMN_COLORS['accent_blue']} !important;
    }}
    
    /* Text input focus */
    .stTextInput > div > div > input:focus {{
        border-color: {FMN_COLORS['primary_green']} !important;
        box-shadow: 0 0 0 0.2rem {FMN_COLORS['primary_green']}40 !important;
    }}
    
    /* Expander header */
    .streamlit-expanderHeader {{
        background-color: {FMN_COLORS['navy_blue']}10 !important;
        color: {FMN_COLORS['navy_blue']} !important;
    }}
    
    /* Metrics */
    [data-testid="stMetricValue"] {{
        color: {FMN_COLORS['primary_green']} !important;
    }}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# CONFIGURATION & SESSION INIT
# -------------------------------------------------
MAX_ATTEMPTS = 3
SESSION_TIMEOUT = 15  # minutes

def init_session():
    """Initialize session state variables"""
    if "stage" not in st.session_state:
        st.session_state.stage = "name"
        st.session_state.customer_name = ""
        st.session_state.order_id = ""
        st.session_state.attempts = 0
        st.session_state.blocked_until = None
        st.session_state.last_activity = datetime.now()

def check_timeout():
    """Check if session has timed out"""
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=SESSION_TIMEOUT):
        st.session_state.stage = "name"
        st.session_state.customer_name = ""
        st.session_state.order_id = ""
        st.warning(f"⏰ Session timed out after {SESSION_TIMEOUT} minutes of inactivity.")
        return True
    st.session_state.last_activity = datetime.now()
    return False

# -------------------------------------------------
# LOAD DATA FROM GOOGLE SHEET (OR FALLBACK)
# -------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        gc = gspread.authorize(creds)

        SHEET_NAME = "salesline_chatbot"
        sheet = gc.open(SHEET_NAME).sheet1

        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        print("Google Sheets loaded successfully.")

    except Exception as e:
        st.error(f"Google Sheets connection failed: {e}")
        st.warning("Using embedded fallback data — Google Sheet not connected yet.")

        DATA_CSV_STRING = """recid,Sales order,Inventory Unit,Order Status,Delivery Date,Invoice account,Delivery address Name,Mode of delivery,Delivery terms,Item number,Net amount,Product name,Quantity Order,Requested receipt date,Requested ship date,Unit price,Quantity,Unit,Shipping Date,modifieddatetime,modifiedby,createddatetime,createdby
5637945894,SAP0014689,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:39,Iekwuazi,11/4/25 17:33,Iekwuazi
5637945893,SAP0014688,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:37,Iekwuazi,11/4/25 17:31,Iekwuazi
5637945892,SAP0014687,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:36,Iekwuazi,11/4/25 17:29,Iekwuazi"""
        
        df = pd.read_csv(io.StringIO(DATA_CSV_STRING))

    df = df.fillna("N/A")

    if "Sales order" in df.columns:
        df["Sales order"] = df["Sales order"].astype(str).str.strip().str.upper()
    
    if "Invoice account" in df.columns:
        df["Invoice account"] = df["Invoice account"].astype(str).str.strip().str.upper()

    return df


# -------------------------------------------------
# ORDER LOOKUP LOGIC WITH INVOICE VALIDATION
# -------------------------------------------------
def find_order_details(order_id, invoice_account, df):
    """
    Find order details with two-factor verification:
    1. Sales Order ID must match
    2. Invoice Account ID must match
    """
    order_clean = order_id.strip().upper()
    invoice_clean = invoice_account.strip().upper()
    
    # Filter by both Sales Order and Invoice Account
    rows = df[(df["Sales order"] == order_clean) & (df["Invoice account"] == invoice_clean)]

    if rows.empty:
        # Check if order exists but invoice account doesn't match
        order_exists = df[df["Sales order"] == order_clean]
        if not order_exists.empty:
            return "invalid_invoice"  # Order exists but wrong invoice account
        return None  # Order doesn't exist at all
    
    return rows


def narrate_order_details(order_df, customer_name):
    """
    Display order details for orders with multiple line items
    """
    # Get common order information from the first row
    first_row = order_df.iloc[0]
    order_id = first_row['Sales order']
    
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, {FMN_COLORS['primary_green']}15, {FMN_COLORS['accent_green']}15); 
                    padding: 20px; border-radius: 10px; border-left: 5px solid {FMN_COLORS['primary_green']};'>
            <h3 style='color: {FMN_COLORS['primary_green']}; margin: 0;'>🎉 Great news, {customer_name}!</h3>
            <p style='color: {FMN_COLORS['navy_blue']}; margin: 10px 0 0 0;'>
                I found <strong>{len(order_df)} item(s)</strong> for <strong>Sales Order {order_id}</strong>. 
                Here's everything you need to know:
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.write("")  # spacing

    # Display common order information
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"<h3 style='color: {FMN_COLORS['navy_blue']}'>📋 Order Information</h3>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style='background-color: {FMN_COLORS['accent_blue']}20; padding: 15px; border-radius: 8px; border-left: 4px solid {FMN_COLORS['accent_blue']};'>
                <p style='margin: 5px 0; color: {FMN_COLORS['navy_blue']};'><strong>Order Status:</strong> {first_row['Order Status']}</p>
                <p style='margin: 5px 0; color: {FMN_COLORS['navy_blue']};'><strong>Invoice Account:</strong> {first_row['Invoice account']}</p>
                <p style='margin: 5px 0; color: {FMN_COLORS['navy_blue']};'><strong>Total Items:</strong> {len(order_df)}</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"<h3 style='color: {FMN_COLORS['navy_blue']}'>🚚 Delivery Details</h3>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style='background-color: {FMN_COLORS['primary_orange']}20; padding: 15px; border-radius: 8px; border-left: 4px solid {FMN_COLORS['primary_orange']};'>
                <p style='margin: 5px 0; color: {FMN_COLORS['navy_blue']};'><strong>Delivery Date:</strong> {first_row['Delivery Date']}</p>
                <p style='margin: 5px 0; color: {FMN_COLORS['navy_blue']};'><strong>Ship Date:</strong> {first_row['Shipping Date']}</p>
                <p style='margin: 5px 0; color: {FMN_COLORS['navy_blue']};'><strong>Address:</strong> {first_row['Delivery address Name']}</p>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"<h3 style='color: {FMN_COLORS['navy_blue']}'>📦 Shipping Info</h3>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style='background-color: {FMN_COLORS['primary_green']}20; padding: 15px; border-radius: 8px; border-left: 4px solid {FMN_COLORS['primary_green']};'>
                <p style='margin: 5px 0; color: {FMN_COLORS['navy_blue']};'><strong>Mode:</strong> {first_row['Mode of delivery']}</p>
                <p style='margin: 5px 0; color: {FMN_COLORS['navy_blue']};'><strong>Terms:</strong> {first_row['Delivery terms']}</p>
            </div>
        """, unsafe_allow_html=True)
        # Calculate total net amount across all items
        total_amount = order_df['Net amount'].astype(float).sum()
        st.metric("Total Net Amount", f"₦{total_amount:,.2f}")

    st.markdown("---")
    
    # Display each line item
    st.markdown(f"<h3 style='color: {FMN_COLORS['navy_blue']}'>📦 Order Line Items</h3>", unsafe_allow_html=True)
    
    for idx, (_, item) in enumerate(order_df.iterrows(), 1):
        with st.expander(f"**Item {idx}: {item['Product name']}**", expanded=True):
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.write("**Product Details**")
                st.write(f"• Product: {item['Product name']}")
                st.write(f"• Item Number: {item['Item number']}")
                st.write(f"• Quantity: {item['Quantity Order']} {item['Unit']}")
            
            with col_b:
                st.write("**Pricing**")
                st.write(f"• Unit Price: ₦{float(item['Unit price']):,.2f}")
                st.write(f"• Net Amount: ₦{float(item['Net amount']):,.2f}")
            
            with col_c:
                st.write("**Dates**")
                st.write(f"• Requested Receipt: {item['Requested receipt date']}")
                st.write(f"• Requested Ship: {item['Requested ship date']}")


# -------------------------------------------------
# MAIN APP (3-STAGE ASSISTANT WITH SECURITY)
# -------------------------------------------------
def main():
    st.title("🤖 FMN Order Status Assistant AI")
    st.write("Your virtual FMN support agent for instant order verification and delivery insights — powered by a smart order-intelligence engine designed to simplify customer experience.")

    # Initialize session
    init_session()
    
    # Check for timeout
    if check_timeout():
        return

    df = load_data()

    if df.empty:
        st.error("Could not load any data.")
        return

    # Sidebar with refresh and session info
    with st.sidebar:
        st.header("Settings")
        if st.button("🔄 Refresh Data"):
            load_data.clear()
            st.rerun()
        
        if st.session_state.customer_name:
            st.info(f"👤 Logged in as: **{st.session_state.customer_name}**")
        
        st.caption(f"Session timeout: {SESSION_TIMEOUT} minutes")

    # Stage 1 — Ask for name
    if st.session_state.stage == "name":
        st.header("Welcome! I'm your Order Status Assistant.")
        name = st.text_input("Please tell me your name so I can address you properly:", max_chars=100)

        if st.button("Confirm"):
            if name.strip() == "":
                st.error("Please enter a valid name.")
                return

            st.session_state.customer_name = name.strip()
            st.session_state.stage = "order"
            st.rerun()

    # Stage 2 — Ask for order ID
    elif st.session_state.stage == "order":
        st.subheader(f"Hello, {st.session_state.customer_name}! Ready to check your order status?")
        order_id = st.text_input("Enter your Sales Order ID:", max_chars=50)

        colA, colB = st.columns(2)

        with colA:
            proceed = st.button("Next")
        with colB:
            restart = st.button("Restart")

        if restart:
            st.session_state.stage = "name"
            st.session_state.order_id = ""
            st.session_state.customer_name = ""
            st.rerun()

        if proceed:
            if order_id.strip() == "":
                st.error("Please enter an order ID.")
                return

            st.session_state.order_id = order_id.strip()
            st.session_state.stage = "validate"
            st.rerun()

    # Stage 3 — Validate with Invoice Account
    elif st.session_state.stage == "validate":
        # Check if user is blocked
        if st.session_state.blocked_until:
            if datetime.now() < st.session_state.blocked_until:
                remaining = int((st.session_state.blocked_until - datetime.now()).total_seconds())
                st.error(f"🚫 Too many failed attempts. Please wait {remaining} seconds before trying again.")
                return
            else:
                # Unblock user
                st.session_state.blocked_until = None
                st.session_state.attempts = 0

        st.subheader(f"🔒 Security Validation Required")
        st.info(f"For Sales Order: **{st.session_state.order_id}**")
        st.write("Please confirm your Invoice Account ID to view your order details.")
        
        if st.session_state.attempts > 0:
            st.warning(f"⚠️ Failed attempts: {st.session_state.attempts}/{MAX_ATTEMPTS}")
        
        invoice_account = st.text_input("Enter your Invoice Account ID:", max_chars=50)

        colA, colB = st.columns(2)

        with colA:
            verify = st.button("Verify & View Order")
        with colB:
            back = st.button("Back")

        if back:
            st.session_state.stage = "order"
            st.session_state.attempts = 0
            st.rerun()

        if verify:
            if invoice_account.strip() == "":
                st.error("Please enter your Invoice Account ID.")
                return

            # Clean the invoice account input: uppercase and trim spaces
            invoice_clean = invoice_account.strip().upper()

            with st.spinner("Verifying credentials and searching FMN order records..."):
                time.sleep(1.5)
                result = find_order_details(st.session_state.order_id, invoice_clean, df)

            if isinstance(result, pd.DataFrame):
                # Successfully found and validated order
                st.session_state.attempts = 0  # Reset attempts on success
                narrate_order_details(result, st.session_state.customer_name)
                
                # Option to check another order
                st.markdown("---")
                if st.button("Check Another Order"):
                    st.session_state.stage = "order"
                    st.session_state.order_id = ""
                    st.rerun()
                    
            elif result == "invalid_invoice":
                st.session_state.attempts += 1
                
                # Block user if max attempts reached
                if st.session_state.attempts >= MAX_ATTEMPTS:
                    st.session_state.blocked_until = datetime.now() + timedelta(minutes=5)
                    st.error(f"🚫 Maximum verification attempts ({MAX_ATTEMPTS}) exceeded. Account locked for 5 minutes for security.")
                else:
                    st.error(f"❌ **Invoice Account Mismatch!** The Invoice Account ID you entered doesn't match our records for Sales Order **{st.session_state.order_id}**. Please double-check and try again.")
                    st.warning("💡 **Tip:** Make sure you're entering the correct Invoice Account ID associated with this order.")
            else:
                st.session_state.attempts += 1
                
                if st.session_state.attempts >= MAX_ATTEMPTS:
                    st.session_state.blocked_until = datetime.now() + timedelta(minutes=5)
                    st.error(f"🚫 Maximum verification attempts ({MAX_ATTEMPTS}) exceeded. Account locked for 5 minutes for security.")
                else:
                    st.error(f"❌ No order found for ID **{st.session_state.order_id}**. Please check the order number and try again.")


if __name__ == "__main__":
    main()
