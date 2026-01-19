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
    page_icon="🤖"
)

# -------------------------------------------------
# LOAD DATA FROM GOOGLE SHEET (OR FALLBACK)
# -------------------------------------------------
@st.cache_data
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
    
    st.subheader(f"Great news, {customer_name}! 🎉")
    st.write(
        f"I found **{len(order_df)} item(s)** for **Sales Order {order_id}**. "
        f"Here's everything you need to know:"
    )

    # Display common order information
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("### Order Information")
        st.info(f"**Order Status:** {first_row['Order Status']}")
        st.write(f"**Invoice Account:** {first_row['Invoice account']}")
        st.write(f"**Total Items:** {len(order_df)}")

    with col2:
        st.write("### Delivery Details")
        st.warning(f"**Delivery Date:** {first_row['Delivery Date']}")
        st.write(f"**Ship Date:** {first_row['Shipping Date']}")
        st.write(f"**Delivery Address:** {first_row['Delivery address Name']}")

    with col3:
        st.write("### Shipping Information")
        st.write(f"**Mode of Delivery:** {first_row['Mode of delivery']}")
        st.write(f"**Delivery Terms:** {first_row['Delivery terms']}")
        # Calculate total net amount across all items
        total_amount = order_df['Net amount'].astype(float).sum()
        st.metric("Total Net Amount", f"₦{total_amount:,.2f}")

    st.markdown("---")
    
    # Display each line item
    st.write("### 📦 Order Line Items")
    
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
        st.header("Welcome! I'm your Order Status Assistant.")
        name = st.text_input("Please tell me your name so I can address you properly:")

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
        order_id = st.text_input("Enter your Sales Order ID:")

        colA, colB = st.columns(2)

        with colA:
            proceed = st.button("Next")
        with colB:
            restart = st.button("Restart")

        if restart:
            st.session_state.stage = "name"
            st.session_state.order_id = ""
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
        st.subheader(f"🔒 Security Validation Required")
        st.info(f"For Sales Order: **{st.session_state.order_id}**")
        st.write("To protect your order information, please verify your identity.")
        
        invoice_account = st.text_input("Enter your Invoice Account ID:")

        colA, colB = st.columns(2)

        with colA:
            verify = st.button("Verify & View Order")
        with colB:
            back = st.button("Back")

        if back:
            st.session_state.stage = "order"
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

            if result is not None and result != "invalid_invoice":
                narrate_order_details(result, st.session_state.customer_name)
                
                # Option to check another order
                st.markdown("---")
                if st.button("Check Another Order"):
                    st.session_state.stage = "order"
                    st.session_state.order_id = ""
                    st.rerun()
                    
            elif result == "invalid_invoice":
                st.error(f"❌ **Access Denied!** The Invoice Account ID you provided does not match the Sales Order **{st.session_state.order_id}**. Please verify your credentials and try again.")
                st.warning("💡 **Tip:** Make sure you're entering the correct Invoice Account ID associated with this order.")
            else:
                st.error(f"❌ No order found for ID **{st.session_state.order_id}**. Please check the order number and try again.")


if __name__ == "__main__":
    main()
