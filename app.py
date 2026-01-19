import streamlit as st
import pandas as pd
import time
import io
import gspread
from google.oauth2.service_account import Credentials

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="FMN Order Status Assistant AI",
    layout="wide",
    page_icon="🤖",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# CUSTOM CSS FOR FMN BRANDING & MOBILE RESPONSIVE
# -------------------------------------------------
st.markdown("""
<style>
    /* FMN Brand Colors */
    :root {
        --fmn-red: #E31837;
        --fmn-dark: #1a1a2e;
        --fmn-gold: #FFD700;
        --fmn-light: #f8f9fa;
        --fmn-gray: #6c757d;
    }
    
    /* Main container styling */
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem;
    }
    
    /* Header styling */
    .stApp header {
        background: transparent;
    }
    
    /* Custom card styling */
    .custom-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid rgba(227, 24, 55, 0.3);
        box-shadow: 0 8px 32px 0 rgba(227, 24, 55, 0.2);
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .custom-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(227, 24, 55, 0.3);
    }
    
    /* Title styling */
    .fmn-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #E31837 0%, #FFD700 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        animation: fadeInDown 0.8s ease;
    }
    
    .fmn-subtitle {
        color: rgba(255, 255, 255, 0.8);
        text-align: center;
        font-size: 1rem;
        margin-bottom: 2rem;
        animation: fadeInUp 0.8s ease;
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.1);
        border: 2px solid rgba(227, 24, 55, 0.3);
        border-radius: 12px;
        color: white;
        font-size: 1.1rem;
        padding: 0.8rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #E31837;
        box-shadow: 0 0 20px rgba(227, 24, 55, 0.4);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #E31837 0%, #c41230 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(227, 24, 55, 0.4);
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(227, 24, 55, 0.6);
        background: linear-gradient(135deg, #c41230 0%, #E31837 100%);
    }
    
    /* Info boxes */
    .stInfo, .stWarning, .stSuccess, .stError {
        border-radius: 12px;
        border-left: 4px solid #E31837;
        animation: slideInLeft 0.5s ease;
    }
    
    /* Order summary cards */
    .order-card {
        background: linear-gradient(135deg, rgba(227, 24, 55, 0.1) 0%, rgba(255, 215, 0, 0.1) 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(227, 24, 55, 0.2);
        transition: all 0.3s ease;
    }
    
    .order-card:hover {
        transform: scale(1.02);
        box-shadow: 0 8px 25px rgba(227, 24, 55, 0.3);
    }
    
    /* Metrics */
    .stMetric {
        background: rgba(227, 24, 55, 0.1);
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid rgba(227, 24, 55, 0.3);
    }
    
    .stMetric label {
        color: rgba(255, 255, 255, 0.8);
        font-weight: 600;
    }
    
    .stMetric .metric-value {
        color: #FFD700;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(227, 24, 55, 0.2);
        border-radius: 12px;
        border: 1px solid rgba(227, 24, 55, 0.3);
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .streamlit-expanderContent {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 0 0 12px 12px;
        border: 1px solid rgba(227, 24, 55, 0.2);
    }
    
    /* Animations */
    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Mobile Responsive */
    @media (max-width: 768px) {
        .fmn-title {
            font-size: 1.8rem;
        }
        
        .fmn-subtitle {
            font-size: 0.9rem;
        }
        
        .custom-card {
            padding: 1.2rem;
        }
        
        .stButton > button {
            padding: 0.7rem 1.5rem;
            font-size: 1rem;
        }
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Section headers */
    h3 {
        color: #FFD700;
        font-weight: 700;
        border-bottom: 2px solid rgba(227, 24, 55, 0.5);
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# LOAD DATA FROM GOOGLE SHEET (OR FALLBACK)
# -------------------------------------------------
@st.cache_data(show_spinner=False)
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

        DATA_CSV_STRING = """
recid,Sales order,Inventory Unit,Order Status,Delivery Date,Invoice account,Delivery address Name,Mode of delivery,Delivery terms,Item number,Net amount,Product name,Quantity Order,Requested receipt date,Requested ship date,Unit price,Quantity,Unit,Shipping Date,modifieddatetime,modifiedby,createddatetime,createdby
5637945894,SAP0014689,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:39,Iekwuazi,11/4/25 17:33,Iekwuazi
5637945893,SAP0014688,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:37,Iekwuazi,11/4/25 17:31,Iekwuazi
5637945892,SAP0014687,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:36,Iekwuazi,11/4/25 17:29,Iekwuazi
"""
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
    order_clean = order_id.strip().upper()
    invoice_clean = invoice_account.strip().upper()
    
    rows = df[(df["Sales order"] == order_clean) & (df["Invoice account"] == invoice_clean)]

    if rows.empty:
        order_exists = df[df["Sales order"] == order_clean]
        if not order_exists.empty:
            return "invalid_invoice"
        return None
    
    return rows


def narrate_order_details(order_df, customer_name):
    first_row = order_df.iloc[0]
    order_id = first_row['Sales order']
    
    # Header with animation
    st.markdown(f"""
    <div style='text-align: center; animation: fadeInDown 0.8s ease;'>
        <h1 style='color: #FFD700; font-size: 2.5rem; margin-bottom: 0.5rem;'>🎉 Great News, {customer_name}!</h1>
        <p style='color: rgba(255,255,255,0.8); font-size: 1.2rem;'>Found <span style='color: #E31837; font-weight: bold;'>{len(order_df)} item(s)</span> for Order <span style='color: #FFD700; font-weight: bold;'>{order_id}</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Summary cards in columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class='order-card'>
            <h3>📋 Order Information</h3>
        </div>
        """, unsafe_allow_html=True)
        st.info(f"**Status:** {first_row['Order Status']}")
        st.write(f"**📄 Invoice Account:** {first_row['Invoice account']}")
        st.write(f"**📦 Total Items:** {len(order_df)}")

    with col2:
        st.markdown("""
        <div class='order-card'>
            <h3>🚚 Delivery Details</h3>
        </div>
        """, unsafe_allow_html=True)
        st.warning(f"**📅 Delivery Date:** {first_row['Delivery Date']}")
        st.write(f"**🚢 Ship Date:** {first_row['Shipping Date']}")
        st.write(f"**📍 Address:** {first_row['Delivery address Name']}")

    with col3:
        st.markdown("""
        <div class='order-card'>
            <h3>💰 Financial Summary</h3>
        </div>
        """, unsafe_allow_html=True)
        total_amount = order_df['Net amount'].astype(float).sum()
        st.metric("Total Amount", f"₦{total_amount:,.2f}")
        st.write(f"**🚛 Delivery Mode:** {first_row['Mode of delivery']}")
        st.write(f"**📋 Terms:** {first_row['Delivery terms']}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Line items
    st.markdown("""
    <div style='text-align: center; margin: 2rem 0;'>
        <h2 style='color: #FFD700; font-size: 2rem;'>📦 Order Line Items</h2>
    </div>
    """, unsafe_allow_html=True)
    
    for idx, (_, item) in enumerate(order_df.iterrows(), 1):
        with st.expander(f"**Item {idx}: {item['Product name']}**", expanded=(idx == 1)):
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.markdown("### 🏷️ Product Details")
                st.write(f"**Product:** {item['Product name']}")
                st.write(f"**Item #:** {item['Item number']}")
                st.write(f"**Quantity:** {item['Quantity Order']} {item['Unit']}")
            
            with col_b:
                st.markdown("### 💵 Pricing")
                st.write(f"**Unit Price:** ₦{float(item['Unit price']):,.2f}")
                st.write(f"**Net Amount:** ₦{float(item['Net amount']):,.2f}")
            
            with col_c:
                st.markdown("### 📅 Dates")
                st.write(f"**Receipt Date:** {item['Requested receipt date']}")
                st.write(f"**Ship Date:** {item['Requested ship date']}")


# -------------------------------------------------
# MAIN APP
# -------------------------------------------------
def main():
    # Custom header
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1 class='fmn-title'>🤖 FMN Order Status Assistant</h1>
        <p class='fmn-subtitle'>Your intelligent partner for instant order verification and delivery insights</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_data()

    if df.empty:
        st.error("Could not load any data.")
        return

    # Initialize session state
    if "stage" not in st.session_state:
        st.session_state.stage = "name"
        st.session_state.customer_name = ""
        st.session_state.order_id = ""

    # Stage 1 — Ask for name
    if st.session_state.stage == "name":
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("### 👋 Welcome! Let's Get Started")
        st.write("Please enter your name so I can personalize your experience:")
        
        name = st.text_input("Your Name", placeholder="e.g., David Akanji", label_visibility="collapsed")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Continue ➡️"):
                if name.strip() == "":
                    st.error("⚠️ Please enter your name to continue")
                    return

                st.session_state.customer_name = name.strip()
                st.session_state.stage = "order"
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

    # Stage 2 — Ask for order ID
    elif st.session_state.stage == "order":
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown(f"### 👋 Hello, {st.session_state.customer_name}!")
        st.write("Let's find your order. Please enter your Sales Order ID below:")
        
        order_id = st.text_input("Sales Order ID", placeholder="e.g., SPF00013310", label_visibility="collapsed")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔍 Find My Order"):
                if order_id.strip() == "":
                    st.error("⚠️ Please enter your order ID")
                    return

                st.session_state.order_id = order_id.strip()
                st.session_state.stage = "validate"
                st.rerun()
        
        with col2:
            if st.button("🔄 Start Over"):
                st.session_state.stage = "name"
                st.session_state.order_id = ""
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

    # Stage 3 — Validate with Invoice Account
    elif st.session_state.stage == "validate":
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("### 🔒 Verification Required")
        st.info(f"**Sales Order:** {st.session_state.order_id}")
        st.write("Please confirm your Invoice Account ID to view your order details.")
        
        invoice_account = st.text_input("Invoice Account ID", placeholder="e.g., C33371-C0", label_visibility="collapsed")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Verify & View"):
                if invoice_account.strip() == "":
                    st.error("⚠️ Please enter your Invoice Account ID")
                    return

                invoice_clean = invoice_account.strip().upper()

                with st.spinner("🔄 Verifying your credentials..."):
                    time.sleep(1.5)
                    result = find_order_details(st.session_state.order_id, invoice_clean, df)

                if isinstance(result, pd.DataFrame):
                    st.markdown("</div>", unsafe_allow_html=True)
                    narrate_order_details(result, st.session_state.customer_name)
                    
                    st.markdown("---")
                    col_a, col_b, col_c = st.columns([1, 2, 1])
                    with col_b:
                        if st.button("🔍 Check Another Order"):
                            st.session_state.stage = "order"
                            st.session_state.order_id = ""
                            st.rerun()
                    return
                        
                elif result == "invalid_invoice":
                    st.error(f"❌ **Invoice Account Mismatch!** The Invoice Account ID you entered doesn't match our records for Sales Order **{st.session_state.order_id}**. Please double-check and try again.")
                    st.warning("💡 **Tip:** Make sure you're entering the correct Invoice Account ID associated with this order.")
                else:
                    st.error(f"❌ No order found for ID **{st.session_state.order_id}**. Please check the order number and try again.")

        with col2:
            if st.button("⬅️ Back"):
                st.session_state.stage = "order"
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
