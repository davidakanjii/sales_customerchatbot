import streamlit as st
import pandas as pd
import time
import io
import gspread
from google.oauth2.service_account import Credentials

# -------------------------------------------------
# PAGE CONFIG — MUST BE FIRST STREAMLIT COMMAND
# -------------------------------------------------
st.set_page_config(
    page_title="Order Status Assistant",
    layout="wide",
    page_icon="🤖"
)

# -------------------------------------------------
# LOAD DATA FROM GOOGLE SHEET (OR FALLBACK)
# -------------------------------------------------
@st.cache_data
def load_data():
    try:
        # Load credentials from Streamlit secrets
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        gc = gspread.authorize(creds)

        # Open sheet
        SHEET_NAME = "salesline_chatbot"
        sheet = gc.open(SHEET_NAME).sheet1

        # Read all rows
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        st.success("Data successfully loaded from Google Sheet!")

    except Exception as e:
        st.warning("Using embedded fallback data — Google Sheet not connected yet.")

        DATA_CSV_STRING = """
recid,Sales order,Inventory Unit,Order Status,Delivery Date,Invoice account,Delivery address Name,Mode of delivery,Delivery terms,Item number,Net amount,Product name,Quantity Order,Requested receipt date,Requested ship date,Unit price,Quantity,Unit,Shipping Date,modifieddatetime,modifiedby,createddatetime,createdby
5637945894,SAP0014689,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:39,Iekwuazi,11/4/25 17:33,Iekwuazi
5637945893,SAP0014688,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:37,Iekwuazi,11/4/25 17:31,Iekwuazi
5637945892,SAP0014687,fzap,Open Order,11/4/25 0:00,C28402-B0,HONEYWELL FLOUR MILLS PLC,Self -30 T,Ex works,P008966,24407627.3,WHEAT; TYPE CANADIAN RED WINTER; RAW-MATERIAL.,35000,11/4/25 0:00,11/4/25 0:00,697360.78,35,T,11/4/25 0:00,11/4/25 17:36,Iekwuazi,11/4/25 17:29,Iekwuazi
"""
        df = pd.read_csv(io.StringIO(DATA_CSV_STRING))

    # Cleanup
    df = df.fillna("N/A")

    if "Sales order" in df.columns:
        df["Sales order"] = df["Sales order"].astype(str).str.strip().str.upper()

    return df

# -------------------------------------------------
# ORDER LOOKUP LOGIC
# -------------------------------------------------
def find_order_details(order_id, df):
    order_clean = order_id.strip().upper()
    row = df[df["Sales order"] == order_clean]

    if row.empty:
        return None
    return row.iloc[0].to_dict()


def narrate_order_details(data, customer_name):
    st.subheader(f"Order Summary for **{customer_name}**")
    st.success(f"Sales Order **{data['Sales order']}** found!")

    col1, col2, col3 = st.columns(3)

    # Status & Product
    with col1:
        st.write("### Status & Product")
        st.info(f"**Order Status:** {data['Order Status']}")
        st.write(f"**Product:** {data['Product name']}")
        st.write(f"**Item Number:** {data['Item number']}")

    # Financials
    with col2:
        st.write("### Financials")
        st.metric("Net Amount", f"${float(data['Net amount']):,.2f}")
        st.write(f"**Unit Price:** ${float(data['Unit price']):,.2f}")
        st.write(f"**Invoice Account:** {data['Invoice account']}")

    # Delivery & Quantity
    with col3:
        st.write("### Delivery")
        st.warning(f"**Delivery Date:** {data['Delivery Date']}")
        st.write(f"**Ship Date:** {data['Shipping Date']}")
        st.write(f"**Quantity:** {data['Quantity Order']} {data['Unit']}")
        st.write(f"**Delivery Address:** {data['Delivery address Name']}")
        st.write(f"**Shipping Method:** {data['Mode of delivery']} ({data['Delivery terms']})")

# -------------------------------------------------
# MAIN APP (2-STAGE ASSISTANT UI)
# -------------------------------------------------
def main():
    st.title("🤖 Order Status Assistant")
    st.write("A simple lookup tool for sales orders.")

    df = load_data()

    if df.empty:
        st.error("Could not load data.")
        return

    # Initialize session state
    if "stage" not in st.session_state:
        st.session_state.stage = "name"
        st.session_state.customer_name = ""

    # Stage 1: Ask for name
    if st.session_state.stage == "name":
        st.subheader("Welcome!")
        name = st.text_input("What is your name?")

        if st.button("Start Lookup"):
            if name.strip() == "":
                st.error("Please enter a valid name.")
                return

            st.session_state.customer_name = name.strip()
            st.session_state.stage = "order"
            st.rerun()

    # Stage 2: Ask for Order ID
    elif st.session_state.stage == "order":
        st.subheader(f"Hello, {st.session_state.customer_name}! 👋")
        order_id = st.text_input("Enter your Sales Order ID:")

        colA, colB = st.columns(2)

        with colA:
            lookup = st.button("Check Status")
        with colB:
            restart = st.button("Restart")

        if restart:
            st.session_state.stage = "name"
            st.rerun()

        if lookup:
            if order_id.strip() == "":
                st.error("Please enter an order ID.")
                return

            with st.spinner("Searching database..."):
                time.sleep(1)
                result = find_order_details(order_id, df)

            if result:
                narrate_order_details(result, st.session_state.customer_name)
            else:
                st.error(f"No order found for ID **{order_id}**.")

# -------------------------------------------------
if __name__ == "__main__":
    main()
