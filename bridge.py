import os
import hashlib
import fitz  # PyMuPDF
from datetime import datetime
from pydantic import BaseModel

# Import your custom modules
from Secure_shield.pii_masking import SecureShield
from Extraction_Engine.extraction_bounding_box import LegalBrain
from Planetary_verifier.verifier import PlanetaryVerifier
from trust_ledger.trust_ledger import TrustLedger

# Initialize Directories
os.makedirs("static", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# Initialize Classes
shield = SecureShield()
brain = LegalBrain()
verifier = PlanetaryVerifier()
ledger = TrustLedger(base_margin_bps=150)

# This serves as our in-memory database
audit_vault = {}

def local_masking(file_bytes, filename):
    """Replaces @app.post('/masking')"""
    doc_id = hashlib.md5(file_bytes).hexdigest()
    
    # Process PII
    result = shield.process_pdf_bytes(file_bytes, filename)
    safe_text = result["safe_content"]
    
    # Save Masked PDF
    masked_pdf_path = f"static/masked_{doc_id}.pdf"
    shield.save_masked_pdf(safe_text, masked_pdf_path)
    
    audit_vault[doc_id] = {
        "safe_text": safe_text,
        "path": masked_pdf_path
    }
    
    return {
        "doc_id": doc_id,
        "preview": safe_text[:1200],
        "status": "🔒 PII Secured"
    }

def local_extraction(doc_id: str):
    """Replaces @app.post('/extraction/{doc_id}')"""
    record = audit_vault.get(doc_id)
    if not record:
        return {"status": "ERROR", "reason": "Doc ID not found"}
        
    pdf_path = record["path"]
    extracted_data = brain.run(pdf_path)
    audit_vault[doc_id]["extracted_data"] = extracted_data
    
    doc = fitz.open(pdf_path)
    found_pages = []

    # Highlight Logic
    targets = [
        str(extracted_data['ndvi']['value']),
        str(extracted_data['margin']['value']),
    ]
    gps_value = str(extracted_data['gps']['value'])
    gps_parts = [p.strip() for p in gps_value.replace(',', ' ').split() if len(p) > 2]
    targets.extend(gps_parts)

    for target in targets:
        if not target or target == "None": continue
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text_instances = page.search_for(target)
            if text_instances:
                found_pages.append(page_idx)
                for inst in text_instances:
                    shape = page.new_shape()
                    shape.draw_rect(inst)
                    shape.finish(color=(1, 0, 0), width=2)
                    shape.commit(overlay=True)

    valid_pages = [p for p in found_pages if p < len(doc)]
    display_page_idx = valid_pages[0] if valid_pages else 0
    
    timestamp = int(datetime.now().timestamp())
    img_filename = f"evidence_{doc_id}_{timestamp}.png"
    img_path = f"static/{img_filename}"
    
    pix = doc[display_page_idx].get_pixmap(dpi=150)
    pix.save(img_path)
    
    return {
        "data": extracted_data,
        "evidence_url": img_path, # Local path for Streamlit
        "page_num": display_page_idx + 1
    }

def local_verification(doc_id: str):
    """Replaces @app.post('/verification/{doc_id}')"""
    try:
        record = audit_vault.get(doc_id)
        data = record.get("extracted_data")
        
        gps_raw = data['gps']['value']
        if ',' in gps_raw:
            lat, lon = gps_raw.split(',')[0].strip(), gps_raw.split(',')[1].strip()
        else:
            parts = gps_raw.split()
            lat, lon = parts[0], parts[1]

        target_ndvi = float(data['ndvi']['value'])
        result = verifier.verify_zonal_truth(lat, lon, target_ndvi)
        
        audit_vault[doc_id]["sat_res"] = result
        return result
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}

def local_audit(doc_id, target, actual, breach_ratio, ratchet_bps):
    """Replaces @app.post('/audit')"""
    # result contains 'report_path' and 'Digital_seal'
    return ledger.calculate_final_verdict(
        doc_id, target, actual, breach_ratio, ratchet_bps
    )