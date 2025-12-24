import streamlit as st
import pandas as pd
import requests
import time
import json
from datetime import datetime
from pathlib import Path
from database import get_exotel_data
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure page
st.set_page_config(
    page_title="Outbound Dialer",
    page_icon="☎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS for better UI
st.markdown("""
    <style>
        .status-dialed { color: green; font-weight: bold; }
        .status-not-dialed { color: red; font-weight: bold; }
        .status-pending { color: orange; font-weight: bold; }
        .dial-button { padding: 10px; margin: 5px 0; }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'call_status' not in st.session_state:
    st.session_state.call_status = {}
if 'df' not in st.session_state:
    st.session_state.df = None
if 'is_automatic_running' not in st.session_state:
    st.session_state.is_automatic_running = False
if 'last_dialed_index' not in st.session_state:
    st.session_state.last_dialed_index = -1

# API Configuration
API_ENDPOINT = "http://54.169.210.53:7862/start"
HEADERS = {"Content-Type": "application/json"}

def dial_number(phone_number):
    """Make API call to dial a phone number"""
    try:
        payload = {
            "dialout_settings": {
                "phone_number": phone_number
            }
        }
        response = requests.post(API_ENDPOINT, json=payload, headers=HEADERS, timeout=5)
        if response.status_code == 200:
            return True, "Call initiated successfully"
        else:
            return False, f"Error: {response.status_code} - {response.text}"
    except requests.exceptions.Timeout:
        return False, "Request timeout - API not responding"
    except requests.exceptions.ConnectionError:
        return False, "Connection error - Cannot reach API"
    except Exception as e:
        return False, f"Error: {str(e)}"

def load_excel_file(uploaded_file):
    """Load Excel file and validate columns"""
    try:
        df = pd.read_excel(uploaded_file)
        # Normalize column names (case-insensitive)
        df.columns = df.columns.str.lower().str.strip()
        
        # Check for required columns
        required_cols = ['name', 'phone no', 'reason of call']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"Missing required columns: {', '.join(missing_cols)}")
            st.info(f"Found columns: {', '.join(df.columns.tolist())}")
            return None
        
        # Initialize call status for each row
        for idx in df.index:
            if idx not in st.session_state.call_status:
                st.session_state.call_status[idx] = {
                    'status': 'Not Dialed',
                    'timestamp': None,
                    'error': None
                }
        
        return df
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def get_status_color(status):
    """Return color for status display"""
    if status == "Dialed":
        return "🟢"
    elif status == "Failed":
        return "🔴"
    else:
        return "🟡"

# Main title
st.title("☎️ Outbound Call Dialer")
st.markdown("---")

# Create tabs for different sections
tab1, tab2 = st.tabs(["📞 Dialer", "📊 Exotel Data"])

with tab2:
    st.subheader("📊 Exotel Call Data")
    
    if st.button("🔄 Refresh Data", key="refresh_exotel"):
        st.session_state.exotel_data = None
    
    if 'exotel_data' not in st.session_state:
        st.session_state.exotel_data = None
    
    if st.session_state.exotel_data is None:
        with st.spinner("Loading data from database..."):
            exotel_df = get_exotel_data()
            if exotel_df is not None:
                st.session_state.exotel_data = exotel_df
            else:
                st.error("❌ Failed to load data from database. Please check the database connection.")
    
    if st.session_state.exotel_data is not None:
        exotel_df = st.session_state.exotel_data
        st.success(f"✅ Loaded {len(exotel_df)} records from exotel_data table")
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(exotel_df))
        with col2:
            st.metric("Columns", len(exotel_df.columns))
        
        st.markdown("---")
        
        # Display the dataframe
        st.dataframe(exotel_df, use_container_width=True, hide_index=True)
        
        # Download option
        csv = exotel_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="exotel_data.csv",
            mime="text/csv"
        )

# Sidebar for file upload
with st.sidebar:
    st.header("📁 Upload & Configuration")
    uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx', 'xls', 'csv'])
    
    if uploaded_file:
        df = load_excel_file(uploaded_file)
        if df is not None:
            st.session_state.df = df
            st.success(f"✅ File loaded successfully! ({len(df)} records)")

# Main content area for Tab 1
with tab1:
    col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Call Mode Selection")
    mode = st.radio("Select Mode:", ["Manual", "Automatic"])

with col2:
    st.subheader("⚙️ Settings")
    if mode == "Automatic":
        interval_seconds = st.number_input(
            "Interval between calls (seconds):",
            min_value=1,
            max_value=300,
            value=5,
            step=1
        )
        batch_size = st.number_input(
            "Parallel calls (batch size):",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
            help="Number of calls to dial in parallel. Set to 3 to dial 3 calls at the same time."
        )

st.markdown("---")

# Display data and control interface
if st.session_state.df is not None:
    df = st.session_state.df
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    
    dialed_count = sum(1 for v in st.session_state.call_status.values() if v['status'] == 'Dialed')
    failed_count = sum(1 for v in st.session_state.call_status.values() if v['status'] == 'Failed')
    pending_count = len(df) - dialed_count - failed_count
    
    with col1:
        st.metric("Total Records", len(df))
    with col2:
        st.metric("Dialed", dialed_count, delta=f"{dialed_count}/{len(df)}")
    with col3:
        st.metric("Failed", failed_count, delta=f"{failed_count}/{len(df)}")
    with col4:
        st.metric("Pending", pending_count, delta=f"{pending_count}/{len(df)}")
    
    st.markdown("---")
    
    # Manual Mode
    if mode == "Manual":
        st.subheader("🎯 Manual Dialing")
        
        # Create a data table with dial buttons
        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            
            status_info = st.session_state.call_status.get(idx, {})
            status = status_info.get('status', 'Not Dialed')
            
            with col1:
                st.write(f"**{row['name']}**")
            
            with col2:
                st.write(f"{row['phone no']}")
            
            with col3:
                st.write(f"{row['reason of call']}")
            
            with col4:
                st.write(f"{get_status_color(status)} {status}")
                if status_info.get('timestamp'):
                    st.caption(f"at {status_info['timestamp']}")
            
            with col5:
                if status == "Not Dialed":
                    if st.button("📞 Dial", key=f"dial_manual_{idx}"):
                        success, message = dial_number(str(row['phone no']))
                        if success:
                            st.session_state.call_status[idx] = {
                                'status': 'Dialed',
                                'timestamp': datetime.now().strftime("%H:%M:%S"),
                                'error': None
                            }
                            st.success(message)
                            st.rerun()
                        else:
                            st.session_state.call_status[idx] = {
                                'status': 'Failed',
                                'timestamp': datetime.now().strftime("%H:%M:%S"),
                                'error': message
                            }
                            st.error(message)
                            st.rerun()
                else:
                    st.write(f"⏸️ {status}")
    
    # Automatic Mode
    else:
        st.subheader("🤖 Automatic Dialing")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ Start Automatic Dialing", key="start_auto"):
                st.session_state.is_automatic_running = True
        
        with col2:
            if st.button("⏹️ Stop Automatic Dialing", key="stop_auto"):
                st.session_state.is_automatic_running = False
        
        # Display status during automatic dialing
        if st.session_state.is_automatic_running:
            st.info(f"⏳ Automatic dialing is running (Interval: {interval_seconds}s, Batch Size: {batch_size})")
            
            # Display progress
            progress_bar = st.progress(0)
            status_container = st.container()
            
            pending_indices = [
                idx for idx, v in st.session_state.call_status.items()
                if v['status'] == 'Not Dialed'
            ]
            
            if pending_indices:
                # Process in batches with parallel execution
                for batch_start in range(0, len(pending_indices), batch_size):
                    if not st.session_state.is_automatic_running:
                        break
                    
                    batch_indices = pending_indices[batch_start:batch_start + batch_size]
                    
                    # Create a dictionary to store futures
                    futures_to_idx = {}
                    
                    # Submit all calls in the batch to the thread pool
                    with ThreadPoolExecutor(max_workers=batch_size) as executor:
                        for idx in batch_indices:
                            row = df.loc[idx]
                            future = executor.submit(dial_number, str(row['phone no']))
                            futures_to_idx[future] = idx
                        
                        # Process completed calls as they finish
                        for future in as_completed(futures_to_idx):
                            idx = futures_to_idx[future]
                            row = df.loc[idx]
                            
                            try:
                                success, message = future.result()
                                
                                if success:
                                    st.session_state.call_status[idx] = {
                                        'status': 'Dialed',
                                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                                        'error': None
                                    }
                                    status_container.success(f"✅ Call initiated: {row['name']}")
                                else:
                                    st.session_state.call_status[idx] = {
                                        'status': 'Failed',
                                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                                        'error': message
                                    }
                                    status_container.error(f"❌ Failed: {row['name']} - {message}")
                            except Exception as e:
                                st.session_state.call_status[idx] = {
                                    'status': 'Failed',
                                    'timestamp': datetime.now().strftime("%H:%M:%S"),
                                    'error': str(e)
                                }
                                status_container.error(f"❌ Error: {row['name']} - {str(e)}")
                            
                            # Update progress
                            dialed_count = sum(
                                1 for v in st.session_state.call_status.values()
                                if v['status'] in ['Dialed', 'Failed']
                            )
                            progress_bar.progress(dialed_count / len(df))
                    
                    # Wait before next batch (except for the last batch)
                    if batch_start + batch_size < len(pending_indices):
                        time.sleep(interval_seconds)
                
                st.success("✅ Automatic dialing completed!")
                st.session_state.is_automatic_running = False
                st.rerun()
            else:
                st.warning("⚠️ No pending calls to dial")
                st.session_state.is_automatic_running = False
        
        st.markdown("---")
        st.subheader("📊 Call Status")
        
        # Display detailed status table
        status_data = []
        for idx, row in df.iterrows():
            status_info = st.session_state.call_status.get(idx, {})
            status_data.append({
                'Name': row['name'],
                'Phone No': row['phone no'],
                'Reason': row['reason of call'],
                'Status': status_info.get('status', 'Not Dialed'),
                'Time': status_info.get('timestamp', '-'),
                'Error': status_info.get('error', '-')
            })
        
        status_df = pd.DataFrame(status_data)
        st.dataframe(status_df, use_container_width=True, hide_index=True)
else:
    st.info("👈 Please upload an Excel file from the sidebar to get started")
    st.markdown("""
    ### Expected Excel File Format:
    Your Excel file should have the following columns:
    - **Name**: Contact name
    - **Phone No**: Phone number (with country code, e.g., +917387243265)
    - **Reason of Call**: Purpose of the call
    """)

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: gray; font-size: 12px;'>
        Outbound Dialer v1.0 | Powered by Streamlit
    </div>
""", unsafe_allow_html=True)
