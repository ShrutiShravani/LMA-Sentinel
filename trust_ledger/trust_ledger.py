import hashlib
from fpdf import FPDF
from datetime import datetime
import os


class TrustLedger:
    def __init__(self, base_margin_bps=150):
        self.base_margin = base_margin_bps 
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)

    def calculate_final_verdict(self, doc_id, target, actual, breach_ratio, ratchet_bps):
        # 1. THE GOVERNANCE KILL-SWITCH
        if actual is None:
            status = "DECLASSIFIED"
            adjustment = ratchet_bps 
            reason = "Data Stream Failure / Missing Coordinates"
            display_actual = "UNVERIFIED"

         # 2. THE CRITICAL ESCALATION (Double Penalty)
        elif breach_ratio > 0.10: 
            status = "Double BREACH"
            adjustment = ratchet_bps * 2
            reason = f"CRITICAL: {round(breach_ratio*100, 1)}% Physical Degradation Detected"
            display_actual = str(actual)

        # 3. STANDARD RATCHET
        elif actual < target:
            status = "BREACH"
            adjustment = ratchet_bps
            reason = "KPI Target Not Met (Average NDVI below target)"
            display_actual = str(actual)

        # 4. COMPLIANT
        else:
            status = "COMPLIANT"
            adjustment = -ratchet_bps 
            reason = "KPI Target Satisfied"
            display_actual = str(actual)

        new_margin = self.base_margin + adjustment
        impact_str = f"+{adjustment} bps" if adjustment > 0 else f"{adjustment} bps"



        # 4. ROI METRICS 
        portfolio_val = 100_000_000
        annual_revenue_change = (portfolio_val * (abs(adjustment) / 10000))
        
        # Generate the PDF
        report_path,final_digital_Seal = self.generate_pdf_report(
            doc_id, target, display_actual, status, impact_str, new_margin,reason, breach_ratio
        )

        # RETURN AS DICTIONARY (For FastAPI/Streamlit)
        return {
            "loan_ref": doc_id,
            "status": status,
            "actual_ndvi": display_actual,
            "breach_ratio": f"{round(breach_ratio * 100, 2)}%",
            "margin_adjustment": impact_str,
            "final_margin": f"{new_margin} bps",
            "revenue_impact": f"${annual_revenue_change:,.2f}",
            "report_path": report_path,
            "Digital_seal":final_digital_Seal
        }

    def generate_pdf_report(self, doc_id, target, actual, status, impact, new_margin, reason, breach_ratio):
        # 1. Create the Seal Hash
        seal_content = f"{doc_id}|{status}|{new_margin}|{datetime.now().isoformat()}"
        final_digital_seal = hashlib.sha256(seal_content.encode()).hexdigest()

        pdf = FPDF()
        pdf.add_page()
        
        # --- TITLE & BRANDING ---
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(0, 51, 102) 
        pdf.cell(0, 15, "LMA-SENTINEL: AUTOMATED COMPLIANCE AUDIT", ln=True, align='C')
        
        pdf.set_font("Arial", 'I', 9)
        pdf.set_text_color(100)
        pdf.cell(0, 5, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
        pdf.ln(10)

        # --- TABLE HEADER ---
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(230, 230, 230) # Light grey fill for header
        pdf.set_text_color(0)
        pdf.cell(80, 12, "Compliance Metric", border=1, align='C', fill=True)
        pdf.cell(110, 12, "Verified Value", border=1, ln=True, align='C', fill=True)

        # --- TABLE DATA ---
        pdf.set_font("Arial", '', 11)
        data = [
            ("Loan Reference", str(doc_id)),
            ("Contractual Target", f"{target} NDVI"),
            ("Satellite Reality", f"{actual} NDVI"),
            ("Physical Breach Area", f"{round(float(breach_ratio) * 100, 2)}%"),
            ("Compliance Status", str(status)),
            ("Verdict Reason", str(reason)),
            ("Margin Adjustment", f"{impact}"),
            ("New Effective Margin", f"{new_margin} bps")
        ]

        for label, val in data:
            # We calculate height based on the right-hand column content
            # This prevents the "overlap" bug
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(80, 12, label, border=1)
            
            pdf.set_font("Arial", '', 11)
            # multi_cell moves the cursor to the next line automatically
            pdf.multi_cell(110, 12, str(val), border=1, align='C')

        # --- DIGITAL SEAL SECTION ---
        pdf.ln(15)
        pdf.set_font("Courier", 'B', 11)
        pdf.cell(0, 10, "VALIDATION DIGITAL SEAL:", ln=True)
        
        pdf.set_font("Courier", '', 9)
        pdf.set_text_color(100)
        # We use a smaller font for the hash so it doesn't wrap weirdly
        pdf.multi_cell(0, 5, final_digital_seal)

        # --- SECURITY FOOTER BOX ---
        pdf.set_y(-110)  # Position 60mm from bottom
        curr_y = pdf.get_y()
        pdf.set_draw_color(0, 51, 102)
        pdf.set_fill_color(245, 247, 249)
        pdf.rect(10, curr_y, 190, 35, 'DF') 
        
        pdf.set_xy(15, curr_y + 5)
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 5,"AUDIT INTEGRITY ADVISORY", ln=True)
        
        pdf.set_font("Arial", '', 9)
        pdf.set_text_color(0)
        pdf.ln(2)
        
        security_text = (
            "- This document is cryptographically sealed with a SHA-256 hash.\n"
            "- Any modification to financial margins or NDVI values voids this record.\n"
            "- This report serves as an immutable record for LMA compliance audits."
        )
        pdf.multi_cell(180, 5, security_text)

        # --- SAVE ---
        report_name = f"audit_report_{doc_id}.pdf"
        path = os.path.join(self.reports_dir, report_name)
        pdf.output(path)

        return path, final_digital_seal
