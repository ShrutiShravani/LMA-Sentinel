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
        # 1. Create the Seal Hash first (so we can print it on the page)
        seal_content = f"{doc_id}|{status}|{new_margin}|{datetime.now().isoformat()}"
        final_digital_seal = hashlib.sha256(seal_content.encode()).hexdigest()

        pdf = FPDF()
        pdf.add_page()
        
        # --- HEADER ---
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(0, 51, 102) 
        # Total width = 190 (80+110). Fits A4 perfectly.
        pdf.cell(80, 11, "Metric", border=1, align='C')
        pdf.cell(110, 11, "Value", border=1, ln=True, align='C')

        pdf.set_font("Arial", '', 11)
        pdf.set_text_color(0)
        data = [
            ("Loan Reference", doc_id),
            ("Contractual Target", str(target)),
            ("Satellite Reality (NDVI)", str(actual)),
            ("Physical Breach Area", f"{round(breach_ratio * 100, 2)}%"),
            ("Compliance Status", status),
            ("Verdict Reason", reason),
            ("Margin Adjustment", impact),
            ("New Effective Margin", f"{new_margin} bps")
        ]

        for label, val in data:
            # Metric column (80mm)
            pdf.cell(80, 12, label, border=1, align='L')
            
            # Value column (110mm) - uses multi_cell to handle long text/errors
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.multi_cell(110, 12, str(val), border=1, align='C')
            # Reset position for next row
            pdf.set_xy(x + 110, y + 12)

        # --- DIGITAL SEAL (BOTTOM LEFT) ---
        pdf.ln(20)
        pdf.set_font("Courier", 'B', 12)
        pdf.set_text_color(0)
        pdf.cell(0, 10, "DIGITAL SEAL:", ln=True, align='L') # Bold Label
        
        pdf.set_font("Courier", '', 11)
        pdf.set_text_color(0)
        # Printing the hashed value string
        pdf.multi_cell(0, 5, f"{final_digital_seal}", align='L')

     
        # --- AUDIT INTEGRITY BOX ---
        pdf.set_y(-85)  # Position from bottom
        current_y = pdf.get_y()
        
        # Draw the background box
        pdf.set_draw_color(0, 51, 102) 
        pdf.set_fill_color(240, 242, 246) 
        pdf.rect(10, current_y, 190, 35, 'DF') 

        # Add Title inside box
        pdf.set_y(current_y + 2)
        pdf.set_x(15) # MOVE CURSOR TO THE LEFT
        pdf.set_font("Courier", 'B', 11)
        pdf.set_text_color(0)
        pdf.cell(0, 8, "AUDIT INTEGRITY ADVISORY:", ln=True)

        # Add Security Points
        pdf.set_font("Arial", '', 9)
        security_points = [
            "- Document is cryptographically sealed with a SHA-256 hash.",
            "- Modifications to NDVI values voids the Digital Seal.",
            "- Report serves as an immutable record for LMA compliance."
        ]

        for point in security_points:
            pdf.set_x(15) # FORCE CURSOR TO LEFT FOR EVERY LINE
            pdf.multi_cell(180, 5, point) # Use 180 instead of 0 for safety

        
        # --- FINAL STEP: SAVE ---
        # We output the file ONLY after all text and seals are added
        report_name = f"audit_report_{doc_id}.pdf"
        path = os.path.join(self.reports_dir, report_name)
        pdf.output(path)

        return path, final_digital_seal
