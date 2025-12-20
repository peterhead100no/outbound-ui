import streamlit as st
import pandas as pd
import requests
import time

API_URL = "http://54.169.210.53:7862/start"

st.set_page_config(page_title="Bulk Call Trigger", layout="wide")

st.title("Outbound Calling Dashboard")

st.markdown("""
Upload an Excel file with **Phone, State, Reason**  
Click **Start Calling** to trigger calls sequentially.
""")

# File uploader
uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx", "xls"]
)

delay_seconds = st.number_input(
    "Gap between calls (seconds)",
    min_value=5,
    max_value=300,
    value=20,
    step=5
)

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    required_cols = {"Phone", "State", "Reason"}
    if not required_cols.issubset(df.columns):
        st.error("Excel must contain columns: Phone, State, Reason")
        st.stop()

    df["Phone"] = df["Phone"].astype(str).str.strip()
    df["FullPhone"] = "+91" + df["Phone"]

    st.subheader("📄 Preview Uploaded Data")
    st.dataframe(df)
    if st.button("🚀 Start Calling"):
        results = []

        progress = st.progress(0)
        status_text = st.empty()

        total = len(df)

        for idx, row in df.iterrows():
            phone = row["FullPhone"]

            status_text.text(f"📞 Calling {phone} ({idx + 1}/{total})")

            payload = {
                "dialout_settings": {
                    "phone_number": phone
                }
            }

            try:
                response = requests.post(
                    API_URL,
                    json=payload,
                    timeout=10
                )

                results.append({
                    "Phone": phone,
                    "State": row["State"],
                    "Reason": row["Reason"],
                    "HTTP_Status": response.status_code,
                    "Result": "Success" if response.ok else "Failed",
                    "Response": response.text
                })

            except Exception as e:
                results.append({
                    "Phone": phone,
                    "State": row["State"],
                    "Reason": row["Reason"],
                    "HTTP_Status": None,
                    "Result": "Error",
                    "Response": str(e)
                })

            progress.progress((idx + 1) / total)

            # ⏸ GAP BETWEEN CALLS
            if idx < total - 1:
                for remaining in range(delay_seconds, 0, -1):
                    status_text.text(
                        f"⏳ Waiting {remaining}s before next call..."
                    )
                    time.sleep(1)
