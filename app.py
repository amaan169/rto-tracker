import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import text

# Ensure a mobile-friendly layout
st.set_page_config(page_title="RTO Tracker", layout="centered", initial_sidebar_state="expanded")

# Initialize connection to Neon Postgres using Streamlit's built-in SQL connection feature
conn = st.connection("postgresql", type="sql")

def init_db():
    """Initialize the Postgres database with the required schema."""
    with conn.session as s:
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                date TEXT,
                vehicle_number TEXT,
                service_type TEXT,
                agent_name TEXT,
                amount REAL,
                payment_status TEXT,
                file_status TEXT DEFAULT 'Pending'
            )
        '''))
        s.commit()

def load_data():
    """Load all transaction data from the database, ordered descending by date."""
    try:
        # Use ttl=0 so we don't cache stale data on the dashboard
        df = conn.query("SELECT * FROM transactions ORDER BY date DESC", ttl=0)
        return df
    except Exception:
        # Failsafe in case table is empty or missing
        return pd.DataFrame()

def add_transaction(txn_date, vehicle_no, service_type, agent_name, amount, payment_status, file_status):
    """Insert a new transaction into the database."""
    with conn.session as s:
        s.execute(
            text('''
                INSERT INTO transactions (date, vehicle_number, service_type, agent_name, amount, payment_status, file_status)
                VALUES (:date, :vehicle, :service, :agent, :amount, :payment, :file_status)
            '''),
            {
                "date": str(txn_date),
                "vehicle": vehicle_no.upper(),
                "service": service_type,
                "agent": agent_name,
                "amount": amount,
                "payment": payment_status,
                "file_status": file_status
            }
        )
        s.commit()

def update_status(txn_id, payment_status, file_status):
    """Update the status of an existing transaction."""
    with conn.session as s:
        s.execute(
            text('''
                UPDATE transactions 
                SET payment_status = :payment, file_status = :file_status 
                WHERE id = :id
            '''),
            {
                "payment": payment_status,
                "file_status": file_status,
                "id": int(txn_id)
            }
        )
        s.commit()

def main():
    init_db()
    
    st.title("📄 RTO Tracker Dashboard")
    st.markdown("Manage your freelance transactions easily from any device.")
    
    # ==========================
    # SIDEBAR: DATA ENTRY FORM
    # ==========================
    with st.sidebar:
        st.header("➕ Add Transaction")
        
        with st.form("add_txn_form", clear_on_submit=True):
            txn_date = st.date_input("Date", date.today())
            vehicle_no = st.text_input("Vehicle Number").strip()
            
            service_type = st.selectbox(
                "Service Type", 
                ["Transfer of Ownership", "Vehicle Renewal", "Finance Cancel", "Driving License", "Other"]
            )
            
            agent_name = st.text_input("Agent Name").strip()
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
            
            payment_status = st.selectbox("Payment Status", ["Not Paid", "Paid"])
            file_status = st.selectbox("File Status", ["Pending", "In Progress", "Completed"])
            
            submit_btn = st.form_submit_button("Save Transaction", use_container_width=True)
            
            if submit_btn:
                if vehicle_no:
                    add_transaction(txn_date, vehicle_no, service_type, agent_name, amount, payment_status, file_status)
                    st.success("✅ Transaction Saved!")
                else:
                    st.error("⚠️ Vehicle Number is required.")
                    
    # ==========================
    # MAIN PAGE: EDIT FEATURE
    # ==========================
    st.header("✏️ Edit Status")
    st.markdown("Quickly update the payment or file status of an existing record.")
    
    df = load_data()
    
    with st.form("edit_status_form"):
        all_ids = df['id'].tolist() if not df.empty else []
        
        edit_id = st.number_input("Record ID", min_value=1, step=1)
        
        col_a, col_b = st.columns(2)
        with col_a:
            new_payment = st.selectbox("Update Payment Status", ["Paid", "Not Paid"])
        with col_b:
            new_file_status = st.selectbox("Update File Status", ["Pending", "In Progress", "Completed"])
            
        update_btn = st.form_submit_button("Update Status")
        
        if update_btn:
            if edit_id in all_ids:
                update_status(edit_id, new_payment, new_file_status)
                st.success(f"✅ Record #{edit_id} updated successfully!")
                st.rerun()
            else:
                st.error(f"⚠️ Record ID {edit_id} not found.")

    st.divider()

    # ==========================
    # MAIN PAGE: DAY-WISE VIEW
    # ==========================
    st.header("📅 Recent Transactions")
    
    if df.empty:
        st.info("No transactions found. Add one from the sidebar!")
    else:
        grouped = df.groupby('date', sort=False)
        
        for txn_date, group in grouped:
            st.markdown(f"### 📌 {txn_date}")
            
            display_df = group.copy().drop(columns=['date'])
            
            st.dataframe(
                display_df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", format="%d"),
                    "vehicle_number": "Vehicle No",
                    "service_type": "Service",
                    "agent_name": "Agent",
                    "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
                    "payment_status": "Payment",
                    "file_status": "File Status"
                }
            )

if __name__ == "__main__":
    main()
