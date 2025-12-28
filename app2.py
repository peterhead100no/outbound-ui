import streamlit as st
import pandas as pd
import requests
import time
import json
from datetime import datetime
from pathlib import Path
from database import get_exotel_data
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET

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
if 'last_status_check' not in st.session_state:
    st.session_state.last_status_check = {}

# API Configuration
API_ENDPOINT = "http://subepiglottic-nonviscously-maureen.ngrok-free.dev/start"
HEADERS = {"Content-Type": "application/json"}

# Exotel API Configuration (from environment variables)
import os
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY", "your_api_key")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN", "your_api_token")
EXOTEL_SUBDOMAIN = os.getenv("EXOTEL_SUBDOMAIN", "api.exotel.in")
EXOTEL_SID = os.getenv("EXOTEL_SID", "Exotel")
EXOTEL_PHONE_NUMBER = os.getenv("EXOTEL_PHONE_NUMBER", "default_phone")

def dial_number(phone_number):
    """Make API call to dial a phone number and return call_sid"""
    try:
        payload = {
            "dialout_settings": {
                "phone_number": phone_number
            }
        }
        print(f"\n{'='*80}")
        print(f"[DIAL REQUEST] Phone Number: {phone_number}")
        print(f"[DIAL REQUEST] Payload: {payload}")
        print(f"[DIAL REQUEST] Endpoint: {API_ENDPOINT}")
        print(f"{'='*80}")
        
        response = requests.post(API_ENDPOINT, json=payload, headers=HEADERS, timeout=5)
        
        print(f"[DIAL RESPONSE] Status Code: {response.status_code}")
        print(f"[DIAL RESPONSE] Content-Type: {response.headers.get('content-type')}")
        print(f"[DIAL RESPONSE] Response Length: {len(response.text)} characters")
        print(f"[DIAL RESPONSE] Full Response:\n{response.text}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"\n[JSON PARSED] Successfully parsed JSON response")
                print(f"[JSON DATA] {response_data}")
                
                # Extract call_sid from response - it's at the top level, not nested
                call_sid = response_data.get("call_sid")
                print(f"\n[EXTRACTED] call_sid: {call_sid}")
                print(f"{'='*80}\n")
                
                if call_sid:
                    return True, "Call initiated successfully", call_sid
                else:
                    print(f"[ERROR] No call_sid in response!")
                    print(f"[ERROR] Response keys: {list(response_data.keys())}")
                    return False, "No call_sid in response", None
            except Exception as parse_error:
                print(f"[ERROR] JSON Parse Error: {str(parse_error)}")
                print(f"[ERROR] Response text: {response.text[:300]}")
                print(f"{'='*80}\n")
                return False, "Invalid response format", None
        else:
            print(f"[ERROR] HTTP Error {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            print(f"{'='*80}\n")
            return False, f"Error: {response.status_code} - {response.text}", None
    except requests.exceptions.Timeout:
        print(f"\n[ERROR] Request Timeout")
        print(f"{'='*80}\n")
        return False, "Request timeout - API not responding", None
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Connection Error")
        print(f"{'='*80}\n")
        return False, "Connection error - Cannot reach API", None
    except Exception as e:
        print(f"\n[ERROR] Exception: {str(e)}")
        print(f"[ERROR] Type: {type(e)}")
        print(f"{'='*80}\n")
        return False, f"Error: {str(e)}", None

def get_call_status(call_sid):
    """Fetch call status from Exotel API using call_sid"""
    try:
        # Correct URL format with @ symbol and ?details=true parameter
        url = f"https://{EXOTEL_API_KEY}:{EXOTEL_API_TOKEN}@{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/{call_sid}?details=true"
        
        print(f"\n{'='*80}")
        print(f"[API REQUEST] Getting call status for call_sid: {call_sid}")
        print(f"[API REQUEST] URL: https://***:***@{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/{call_sid}?details=true")
        print(f"{'='*80}")
        
        response = requests.get(url, timeout=10, verify=True)
        
        print(f"[API RESPONSE] Status Code: {response.status_code}")
        print(f"[API RESPONSE] Content-Type: {response.headers.get('content-type')}")
        print(f"[API RESPONSE] Response Length: {len(response.text)} characters")
        print(f"[API RESPONSE] Full Response:\n{response.text[:1000]}")
        
        if response.status_code == 200:
            try:
                # Check if response is XML or JSON
                content_type = response.headers.get('content-type', '').lower()
                
                if 'xml' in content_type or response.text.strip().startswith('<?xml'):
                    print(f"\n[PARSING] Detected XML response, parsing XML...")
                    
                    # Parse XML response
                    root = ET.fromstring(response.text)
                    
                    # Extract status from XML
                    # Namespace might be present, so we search without it
                    call_elem = root.find('.//Call') or root.find('Call')
                    
                    if call_elem is None:
                        print(f"[ERROR] Could not find 'Call' element in XML")
                        return False, "Invalid XML structure", None
                    
                    status = call_elem.findtext('Status', 'unknown')
                    duration = call_elem.findtext('Duration')
                    answered_by = call_elem.findtext('AnsweredBy')
                    end_time = call_elem.findtext('EndTime')
                    
                    print(f"\n[EXTRACTED DATA FROM XML]")
                    print(f"  - Status: {status}")
                    print(f"  - Duration: {duration}")
                    print(f"  - AnsweredBy: {answered_by}")
                    print(f"  - EndTime: {end_time}")
                    print(f"{'='*80}\n")
                    
                    return True, status, {
                        'status': status,
                        'duration': duration,
                        'answered_by': answered_by,
                        'end_time': end_time
                    }
                    
                else:
                    print(f"\n[PARSING] Detected JSON response, parsing JSON...")
                    response_data = response.json()
                    print(f"[JSON DATA] {response_data}")
                    
                    call_data = response_data.get("Call", {})
                    status = call_data.get("Status", "unknown")
                    duration = call_data.get("Duration")
                    answered_by = call_data.get("AnsweredBy")
                    end_time = call_data.get("EndTime")
                    
                    print(f"\n[EXTRACTED DATA FROM JSON]")
                    print(f"  - Status: {status}")
                    print(f"  - Duration: {duration}")
                    print(f"  - AnsweredBy: {answered_by}")
                    print(f"  - EndTime: {end_time}")
                    print(f"{'='*80}\n")
                    
                    return True, status, {
                        'status': status,
                        'duration': duration,
                        'answered_by': answered_by,
                        'end_time': end_time
                    }
                    
            except ET.ParseError as xml_error:
                print(f"\n[ERROR] XML Parse Error: {str(xml_error)}")
                print(f"[ERROR] Response text: {response.text[:300]}")
                print(f"{'='*80}\n")
                return False, f"Invalid XML format: {str(xml_error)}", None
            except json.JSONDecodeError as json_error:
                print(f"\n[ERROR] JSON Parse Error: {str(json_error)}")
                print(f"[ERROR] Response text: {response.text[:300]}")
                print(f"{'='*80}\n")
                return False, f"Invalid JSON format: {str(json_error)}", None
            except Exception as parse_error:
                print(f"\n[ERROR] Parse Error: {str(parse_error)}")
                print(f"[ERROR] Response text: {response.text[:300]}")
                print(f"{'='*80}\n")
                return False, f"Invalid response format: {str(parse_error)}", None
        else:
            print(f"\n[ERROR] HTTP Error {response.status_code}")
            print(f"[ERROR] Response: {response.text[:500]}")
            print(f"{'='*80}\n")
            return False, f"Error: {response.status_code} - {response.text}", None
    except requests.exceptions.Timeout:
        print(f"\n[ERROR] Request Timeout (10 seconds)")
        print(f"{'='*80}\n")
        return False, "Request timeout", None
    except requests.exceptions.ConnectionError as ce:
        print(f"\n[ERROR] Connection Error: {str(ce)}")
        print(f"{'='*80}\n")
        return False, "Connection error", None
    except Exception as e:
        print(f"\n[ERROR] General Error: {str(e)}")
        print(f"[ERROR] Error Type: {type(e)}")
        print(f"{'='*80}\n")
        return False, f"Error: {str(e)}", None

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
                    'error': None,
                    'call_sid': None,
                    'duration': None,
                    'answered_by': None,
                    'end_time': None
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
        
        # Polling section
        if st.session_state.call_status:
            if st.button("🔄 Refresh Status", key="refresh_status_manual"):
                refresh_count = 0
                error_count = 0
                for idx, status_info in st.session_state.call_status.items():
                    if status_info.get('call_sid') and status_info.get('status') in ['Dialed', 'in-progress']:
                        success, call_status, details = get_call_status(status_info['call_sid'])
                        if success:
                            st.session_state.call_status[idx].update({
                                'status': call_status,
                                'duration': details.get('duration'),
                                'answered_by': details.get('answered_by'),
                                'end_time': details.get('end_time')
                            })
                            refresh_count += 1
                        else:
                            error_count += 1
                
                if refresh_count > 0:
                    st.success(f"✅ Refreshed {refresh_count} call status(es)")
                if error_count > 0:
                    st.warning(f"⚠️ Failed to refresh {error_count} call(s)")
                st.rerun()
        
        # Create a data table with dial buttons
        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 1.5, 1.5, 1])
            
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
                duration = status_info.get('duration')
                if duration:
                    st.caption(f"⏱️ {duration}s")
                if status_info.get('end_time'):
                    st.caption(f"Ended: {status_info['end_time']}")
            
            with col6:
                if status == "Not Dialed":
                    if st.button("📞 Dial", key=f"dial_manual_{idx}"):
                        success, message, call_sid = dial_number(str(row['phone no']))
                        if success:
                            st.session_state.call_status[idx] = {
                                'status': 'Dialed',
                                'timestamp': datetime.now().strftime("%H:%M:%S"),
                                'error': None,
                                'call_sid': call_sid,
                                'duration': None,
                                'answered_by': None,
                                'end_time': None
                            }
                            st.success(message)
                            st.rerun()
                        else:
                            st.session_state.call_status[idx] = {
                                'status': 'Failed',
                                'timestamp': datetime.now().strftime("%H:%M:%S"),
                                'error': message,
                                'call_sid': None,
                                'duration': None,
                                'answered_by': None,
                                'end_time': None
                            }
                            st.error(message)
                            st.rerun()
                elif status in ['in-progress', 'Dialed']:
                    if st.button("🔍 Check Status", key=f"check_status_{idx}"):
                        call_sid = status_info.get('call_sid')
                        if call_sid:
                            success, call_status, details = get_call_status(call_sid)
                            if success:
                                st.session_state.call_status[idx].update({
                                    'status': call_status,
                                    'duration': details.get('duration'),
                                    'answered_by': details.get('answered_by'),
                                    'end_time': details.get('end_time')
                                })
                                st.success(f"✅ Status updated: {call_status}")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to get status: {call_status}")
                                st.info(f"call_sid: {call_sid}")
                        else:
                            st.error("❌ No call_sid found for this call")
                else:
                    st.write(f"⏸️ {status}")
    
    # Automatic Mode
    else:
        st.subheader("🤖 Automatic Dialing")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("▶️ Start Automatic Dialing", key="start_auto"):
                st.session_state.is_automatic_running = True
        
        with col2:
            if st.button("⏹️ Stop Automatic Dialing", key="stop_auto"):
                st.session_state.is_automatic_running = False
        
        with col3:
            auto_refresh = st.checkbox("🔄 Auto-refresh every 10s", value=False, key="auto_refresh")
        
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
                                success, message, call_sid = future.result()
                                
                                if success:
                                    st.session_state.call_status[idx] = {
                                        'status': 'Dialed',
                                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                                        'error': None,
                                        'call_sid': call_sid,
                                        'duration': None,
                                        'answered_by': None,
                                        'end_time': None
                                    }
                                    status_container.success(f"✅ Call initiated: {row['name']}")
                                else:
                                    st.session_state.call_status[idx] = {
                                        'status': 'Failed',
                                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                                        'error': message,
                                        'call_sid': None,
                                        'duration': None,
                                        'answered_by': None,
                                        'end_time': None
                                    }
                                    status_container.error(f"❌ Failed: {row['name']} - {message}")
                            except Exception as e:
                                st.session_state.call_status[idx] = {
                                    'status': 'Failed',
                                    'timestamp': datetime.now().strftime("%H:%M:%S"),
                                    'error': str(e),
                                    'call_sid': None,
                                    'duration': None,
                                    'answered_by': None,
                                    'end_time': None
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
        
        # Auto-refresh status every 10 seconds
        if auto_refresh:
            st.info("🔄 Auto-refreshing call status every 10 seconds...")
            
            # Create columns for status display
            cols = st.columns(3)
            with cols[0]:
                st.metric("Refreshing every", "10 seconds")
            
            # Refresh loop
            placeholder = st.empty()
            
            while auto_refresh:
                # Update status for all calls with call_sid
                for idx, status_info in st.session_state.call_status.items():
                    if status_info.get('call_sid') and status_info.get('status') in ['Dialed', 'in-progress']:
                        success, call_status, details = get_call_status(status_info['call_sid'])
                        if success:
                            st.session_state.call_status[idx].update({
                                'status': call_status,
                                'duration': details.get('duration'),
                                'answered_by': details.get('answered_by'),
                                'end_time': details.get('end_time')
                            })
                
                # Display updated status table
                with placeholder.container():
                    status_data = []
                    for idx, row in df.iterrows():
                        status_info = st.session_state.call_status.get(idx, {})
                        status_data.append({
                            'Name': row['name'],
                            'Phone No': row['phone no'],
                            'Status': status_info.get('status', 'Not Dialed'),
                            'call_sid': status_info.get('call_sid', '-')[:8] + '...' if status_info.get('call_sid') else '-',
                            'Duration': status_info.get('duration', '-'),
                            'Time': status_info.get('timestamp', '-')
                        })
                    
                    status_df = pd.DataFrame(status_data)
                    st.dataframe(status_df, use_container_width=True, hide_index=True)
                
                # Wait 10 seconds before next refresh
                time.sleep(10)
        
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
                'call_sid': status_info.get('call_sid', '-')[:12] + '...' if status_info.get('call_sid') else '-',
                'Duration (s)': status_info.get('duration', '-'),
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
