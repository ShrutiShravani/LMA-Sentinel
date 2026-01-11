import fitz  # PyMuPDF
import re
import os
from fpdf import FPDF

class SecureShield:
    def __init__(self):
        # Enhanced regex to ensure no "leakage" of sensitive LMA data
        self.patterns = {
            # Entities - Catches the uppercase names on Page 1
            "BORROWER": r'(?i)\(1\)\s*([\s\S]+?)\s*\(as Borrower\)',
            "LENDER": r'(?i)\(2\)\s*([A-Z\s,]+)\s*\(as Original Lender\)',
            
            # Financials - Catches the sensitive data on Page 150
            "IBAN": r'[A-Z]{2}\d{2}[a-zA-Z0-9]{11,30}',
            "SWIFT": r'\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b',
            
            # Personal Data
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # Contact & Agent Info (Page 1 & 150)
            "NOTICES": r'(?i)(?:Attention:|Contact:|Director:|\(3\))\s*([A-Za-z\s\.\-]+)',
        }

    def mask_text(self, text):
        masked_text = text
        for label, pattern in self.patterns.items():
            masked_text = re.sub(pattern, f"[{label}_REDACTED]", masked_text)
        return masked_text

    def process_pdf_bytes(self, pdf_stream, filename):
        """Processes PDF from FastAPI stream (no need to save to disk first)."""
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        full_raw_text = ""
        
        # Memory-efficient extraction
        for page in doc:
            full_raw_text += page.get_text("text")

        safe_text = self.mask_text(full_raw_text)
        doc.close()
        
        return {
            "doc_name": filename,
            "safe_content": safe_text,
            "status": "Ready for Extraction"
        }
    def save_masked_pdf(self, safe_text, output_filename):
        
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            
            # Write the masked text into the PDF
            # We encode/decode to handle potential special characters
            clean_text = safe_text.encode('latin-1', 'ignore').decode('latin-1')
            pdf.multi_cell(0, 10, clean_text)
            
            pdf.output(output_filename)
            print(f"Redacted PDF saved: {output_filename}")

