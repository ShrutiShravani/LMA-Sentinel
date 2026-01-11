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
        # Create Seal
        seal_content = f"{doc_id}|{status}|{new_margin}|{datetime.now().isoformat()}"
        final_digital_seal = hashlib.sha256(seal_content.encode()).hexdigest()

        # Force A4 Portrait with standard margins
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # --- TITLE ---
        pdf.set_font("Helvetica", 'B', 16) # Helvetica is safer on Linux/Streamlit than Arial
        pdf.set_text_color(0, 51, 102) 
        pdf.cell(0, 15, "LMA-SENTINEL: COMPLIANCE AUDIT", ln=True, align='C')
        pdf.ln(5)

        # --- THE TABLE (STRICT ALIGNMENT) ---
        pdf.set_font("Helvetica", 'B', 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(0)
        
        # Header
        pdf.cell(80, 10, "Compliance Metric", border=1, align='C', fill=True)
        pdf.cell(110, 10, "Verified Value", border=1, ln=True, align='C', fill=True)

        # Data Rows
        pdf.set_font("Helvetica", '', 10)
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
            # We use a fixed height and cell() instead of multi_cell 
            # for the label to keep the table structure rigid.
            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(80, 10, label, border=1)
            
            pdf.set_font("Helvetica", '', 10)
            # We use cell() for value too. If 'reason' is very long, 
            # we truncate it slightly so it doesn't break the table layout.
            display_val = str(val)[:55] + "..." if len(str(val)) > 58 else str(val)
            pdf.cell(110, 10, display_val, border=1, ln=True, align='C')

        # --- TIGHTENED FOOTER ---
        pdf.ln(6)
        pdf.set_font("Courier", 'B', 10)
        pdf.cell(0, 8, "VALIDATION DIGITAL SEAL:", ln=True)
        pdf.set_font("Courier", '', 7)
        pdf.set_text_color(120)
        pdf.multi_cell(0, 4, final_digital_seal)

        # Audit Advisory Box
        pdf.ln(4)
        curr_y = pdf.get_y()
        pdf.set_draw_color(0, 51, 102)
        pdf.set_fill_color(248, 249, 251)
        pdf.rect(10, curr_y, 190, 28, 'DF')
        
        pdf.set_xy(15, curr_y + 3)
        pdf.set_font("Helvetica", 'B', 9)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 5, "AUDIT INTEGRITY ADVISORY", ln=True)
        
        pdf.set_font("Helvetica", '', 8)
        pdf.set_text_color(0)
        pdf.set_x(15)
        pdf.multi_cell(180, 4, "- Cryptographically sealed record (SHA-256).\n- Modification to data voids this certificate.\n- Immutable LMA compliance record.")

        # --- SAVE & RETURN ---
        report_name = f"audit_report_{doc_id}.pdf"
        # Ensure we use a safe path for Streamlit Cloud
        save_path = os.path.join(self.reports_dir, report_name)
        pdf.output(save_path)

        return save_path, final_digital_seal