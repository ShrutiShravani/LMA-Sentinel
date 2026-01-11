import streamlit as st
import requests
import os
import pandas as pd

st.set_page_config(layout="wide", page_title="LMA-Sentinel")
col_left, col_right = st.columns([0.4, 0.6])

# Initialize Session State
if 'step' not in st.session_state: st.session_state['step'] = 0
if 'doc_id' not in st.session_state: st.session_state['doc_id'] = None

with col_left:
    st.title("ESG Audit Engine")
    uploaded_file = st.file_uploader("Upload LMA Contract", type="pdf")
    
    # --- PHASE 1 BUTTON ---
    if st.button("PHASE 1: PRIVACY SHIELD", use_container_width=True):
        if uploaded_file:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            with st.spinner("🛰️ Masking sensitive client data..."):
                res = requests.post("http://localhost:8000/masking", files=files).json()
                st.session_state['doc_id'] = res['doc_id']
                st.session_state['mask_data'] = res
                st.session_state['step'] = 1
        else: st.warning("Upload PDF first")

    # --- PHASE 2 BUTTON (Enabled only after Step 1) ---
    if st.session_state['step'] >= 1:
        if st.button("PHASE 2: LEGAL EXTRACTION", use_container_width=True):
            with st.spinner("🛰️ Extracting coordinates,ndvi and bps..."):
                res = requests.post(f"http://localhost:8000/extraction/{st.session_state['doc_id']}").json()
                st.session_state['ext_data'] = res
                st.session_state['step'] = 2

    # --- PHASE 3 BUTTON (Enabled only after Step 2) ---
    if st.session_state['step'] >= 2:
        if st.button("PHASE 3: SATELLITE VERIFIER", use_container_width=True):
            with st.spinner("🛰️ Querying Sentinel-2 Stacks..."):
                # 1. Get the response
                resp = requests.post(f"http://localhost:8000/verification/{st.session_state['doc_id']}")
                
                # 2. IMMEDIATELY save it to session_state
                st.session_state['sat_data'] = resp.json()
                
                # 3. Update the step
                st.session_state['step'] = 3
                
                # 4. Force a rerun to show the table
                st.rerun()
    
    if st.session_state['step'] >= 3:
        if st.button("PHASE 4: TRUST LEDGER", use_container_width=True):
            with st.spinner("⚖️ Recalculating Margin & Sealing Audit..."):
                ext = st.session_state['ext_data']['data']
                sat = st.session_state['sat_data']
                if "sat_res" in sat: sat = sat["sat_res"]

                payload = {
                    "doc_id": st.session_state['doc_id'],
                    "target": float(ext['ndvi']['value']), 
                    "actual": float(sat.get('actual_ndvi', 0)),
                    "breach_ratio": float(str(sat.get('breach_area_percentage', "0")).replace('%','')) / 100,
                    "ratchet_bps": float(ext['margin']['value'])
                }
                
                res = requests.post("http://localhost:8000/audit", json=payload).json()
                st.session_state['ledger_data'] = res
                st.session_state['step'] = 4
                st.rerun()

# --- RIGHT COLUMN: DYNAMIC EVIDENCE DISPLAY ---
with col_right:
    st.subheader("Real-Time Evidence Vault")
    step = st.session_state['step']
    
    if step == 0:
        st.info("Awaiting contract ingestion...")
        
    elif step == 1:
        st.markdown("### 🔒 Anonymized PII Preview")
        st.code(st.session_state['mask_data']['preview'], language="text")
        
    elif step == 2:
        res = st.session_state['ext_data']
        st.image(res["evidence_url"], caption="Extracted Legal Anchor")
        # Show Data Bar
        st.json(res["data"]) # Or use your HTML data bar here
        
    elif step == 3:
        # 1. Pull the dictionary
        raw_data = st.session_state.get('sat_data', {})

        # --- DEBUG TOOL (Comment this out after it works) ---
        # st.write("API Data Check:", sat.keys()) \
        if "sat_res" in raw_data:
            sat = raw_data["sat_res"]
        else:
            sat = raw_data

        if sat.get("status") == "SUCCESS":
            st.markdown("### 📊 Final Audit Executive Summary")
            
            # 2. EVIDENCE IMAGES
            col_img1, col_img2 = st.columns(2)
            with col_img1:
                st.image(sat.get("map_thumb_url"), caption="NDVI Heatmap", use_column_width=True)
            with col_img2:
                st.image(sat.get("mask_thumb_url"), caption="Breach Mask", use_column_width=True)

            # 3. CONVERT DICT TO LISTS FOR TABLE
            # We explicitly define the rows to ensure no KeyErrors
            metrics = [
                "Audit Verdict", 
                "Confidence (Satellite Stacks)", 
                "Actual NDVI", 
                "Contract Target NDVI", 
                "Breach Area %", 
                "Compliance Verdict"
            ]
            
            values = [
                sat.get('verdict'),
                f"{sat.get('image_count')} Images (90-day Median)",
                f"{sat.get('actual_ndvi')}",
                f"{sat.get('target_ndvi')}",
                sat.get('breach_area_percentage'),
                "❌ NON-COMPLIANT" if sat.get('is_breach') else "✅ COMPLIANT"
            ]

            # 4. RENDER THE TABLE
            st.table({"Metric": metrics, "Value": values})
            
            # 5. ANALYSIS BLOCK
            st.info(f"**Planetary Analysis:** {sat.get('analysis')}")
            
            # 6. ACTION COLOR CARD
            color = "#ef4444" if sat.get("is_breach") else "#22c55e"
            st.markdown(f"""
                <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center;">
                    <h2 style="color: white; margin: 0;">ACTION: {sat.get('verdict')}</h2>
                </div>
            """, unsafe_allow_html=True)

        elif sat.get("status") == "ERROR":
            st.error(f"Audit Failed: {sat.get('reason')}")
    
    elif step == 4:
        ledger = st.session_state['ledger_data']
        
        # --- HEADER WITH DOWNLOAD ON RIGHT CORNER ---
        head_col, dl_col = st.columns([0.7, 0.3])
        with head_col:
            st.markdown("### 🏦 Final Financial Settlement")
        with dl_col:
            # os.path.basename now works because 'os' is imported at top
            report_filename = os.path.basename(ledger['report_path'])
            # Fetch the PDF from FastAPI
            pdf_response = requests.get(f"http://localhost:8000/download/{report_filename}")
            st.download_button(
                label="📥 DOWNLOAD PDF",
                data=pdf_response.content,
                file_name=report_filename,
                mime="application/pdf",
                use_container_width=True
            )

        # --- KPI TILES ---
        kpi1, kpi2, kpi3 = st.columns(3)
        status_symbol = "✅" if ledger['status'] == "COMPLIANT" else "🚨"
        kpi1.metric("Compliance", f"{status_symbol} {ledger['status']}")
        kpi2.metric("Adjustment", ledger['margin_adjustment'], delta=ledger['margin_adjustment'], delta_color="inverse")
        kpi3.metric("Final Margin", ledger['final_margin'])
      

        # --- FINANCIAL CHART ---
        st.markdown("#### 📉 Margin Ratchet Visualization")
        base_val = 150.0 
        final_val = float(ledger['final_margin'].split()[0])
        chart_df = pd.DataFrame({"Stage": ["Base", "Audit"], "bps": [base_val, final_val]}).set_index("Stage")
        st.bar_chart(chart_df, color="#003366")

        # --- BEAUTIFUL TABLE WITH ICONS ---
        st.markdown("#### 🔍 Audit Traceability Ledger")
        audit_table = pd.DataFrame([
            {"Metric": "🆔 Loan Reference", "Value": ledger['loan_ref'], "Status": "Verified"},
            {"Metric": "🌿 Actual NDVI", "Value": ledger['actual_ndvi'], "Status": "Analyzed"},
            {"Metric": "📉 Breach Area", "Value": ledger['breach_ratio'], "Status": "Calculated"},
            {"Metric": "💸 Impact", "Value": ledger['revenue_impact'], "Status": "Projected"},
            {"Metric": "🔒 Digital Seal", "Value": f"{ledger['Digital_seal'][:20]}...", "Status": "SHA-256"}
        ])
        st.dataframe(audit_table, use_container_width=True, hide_index=True)

        # --- SEAL BOX ---
        st.markdown(f"""
            <div style="background-color: #f0f2f6; border-left: 5px solid #003366; padding: 10px; border-radius: 5px;">
                <p style="margin: 0; font-family: monospace; font-size: 10px;">HASH: {ledger['Digital_seal']}</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("New Audit", type="primary"):
            st.session_state.clear()
            st.rerun()