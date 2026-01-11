from fastapi import FastAPI, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw
import os
import hashlib
from datetime import datetime
import fitz # PyMuPDF
from PIL import Image, ImageDraw
import shutil
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException

# Import your custom modules
from Secure_shield.pii_masking import SecureShield
from Extraction_Engine.extraction_bounding_box import LegalBrain
from Planetary_verifier.verifier import PlanetaryVerifier
from trust_ledger.trust_ledger import TrustLedger

app = FastAPI(title="LMA-Sentinel Core Engine: Legal-to-Lens")

# --- MOUNT STATIC FILES ---
# This allows Streamlit to load the highlighted images via URL
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Classes
shield = SecureShield()
brain = LegalBrain()
verifier = PlanetaryVerifier()
ledger = TrustLedger(base_margin_bps=150)
audit_vault={}

class AuditRequest(BaseModel):
    doc_id: str
    target: float
    actual: float
    breach_ratio: float
    ratchet_bps: float

@app.post("/masking")
async def run_masking(file: UploadFile = File(...)):
    # 1. Read raw content for hashing
    content = await file.read()
    doc_id = hashlib.md5(content).hexdigest()
    
    # 2. Generate the MASKED text and a MASKED PDF
    result = shield.process_pdf_bytes(content, file.filename)
    safe_text = result["safe_content"]
    
    # 3. SAVE THE MASKED PDF (This is what Phase 2 will use)
    # We use your SecureShield's built-in save method
    masked_pdf_path = f"static/masked_{doc_id}.pdf"
    shield.save_masked_pdf(safe_text, masked_pdf_path)
    
    # Store the path to the MASKED PDF for the Brain
    audit_vault[doc_id] = {
        "safe_text": safe_text,
        "path": masked_pdf_path
    }
    
    return {
        "doc_id": doc_id,
        "preview": safe_text[:1200],
        "status": "🔒 PII Secured"
    }

@app.post("/extraction/{doc_id}")
async def run_extraction(doc_id: str):
    record = audit_vault.get(doc_id)
    pdf_path = record["path"] 
    
    extracted_data = brain.run(pdf_path) 
    audit_vault[doc_id]["extracted_data"] = extracted_data
    doc = fitz.open(pdf_path)
    found_pages = []

    # FIX 1: Search for the VALUE only (more robust) instead of Label + Value
    # This ensures GPS and NDVI are actually found even if the label is on a different line
    targets = [
        str(extracted_data['ndvi']['value']),
        str(extracted_data['margin']['value']),
    ]
    
    gps_value = str(extracted_data['gps']['value'])
    # Clean the string and split by spaces/commas
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
                    # FIX 2: REMOVED 'fill' to stop the red patch. Added 'color' for hollow border.
                    shape.finish(color=(1, 0, 0), width=2) 
                    shape.commit(overlay=True)

    # FIX 3: Robust page selection. 
    # If found_pages has 225 but doc is 150, we force it to a valid index.
    if found_pages:
        # 1. Remove duplicates and sort
        unique_pages = sorted(list(set(found_pages)))
        # Filter out any accidental out-of-bounds indices and pick the first valid one
        valid_pages = [p for p in found_pages if p < len(doc)]
        display_page_idx = valid_pages[0] if valid_pages else 0
    else:
        display_page_idx = 0
    
    timestamp = int(datetime.now().timestamp())
    img_filename = f"evidence_{doc_id}_{timestamp}.png"
    img_path = f"static/{img_filename}"
    
    pix = doc[display_page_idx].get_pixmap(dpi=150)
    pix.save(img_path)
    
    return {
        "data": extracted_data,
        "evidence_url": f"http://localhost:8000/static/{img_filename}",
        "page_num": display_page_idx + 1
    }

# REMOVE 'async' - this allows Earth Engine's .getInfo() to run without locking
@app.post("/verification/{doc_id}")
def run_verification(doc_id: str):
    try:
        record = audit_vault.get(doc_id)
        if not record:
            return {"status": "ERROR", "reason": "Document ID not found"}

        # FIX 1: Use the correct key 'extracted_data' saved in Phase 2
        data = record.get("extracted_data")
        if not data:
            return {"status": "ERROR", "reason": "No extraction data found in vault"}
        
        # FIX 2: Safer GPS splitting
        gps_raw = data['gps']['value']
        if ',' in gps_raw:
            lat = gps_raw.split(',')[0].strip()
            lon = gps_raw.split(',')[1].strip()
            print(lat,lon)
        else:
            # Fallback for space-separated coordinates
            parts = gps_raw.split()
            lat, lon = parts[0], parts[1]

        # 2. Call your Verifier Class
        verifier = PlanetaryVerifier()
        # Ensure target_ndvi is a float
        target_ndvi = float(data['ndvi']['value'])
        print(target_ndvi)
        
        result = verifier.verify_zonal_truth(lat, lon, target_ndvi)
        print(result)
        
        # 3. Save result back to vault
        record["sat_res"] = result
        print(f"DEBUG: Verifier Result Keys: {result.keys()}")

        return result

    except Exception as e:
        print(f"API VERIFICATION ERROR: {e}")
        return {"status": "ERROR", "reason": str(e)}

@app.post("/audit")
async def perform_audit(req: AuditRequest):
    try:
        # result contains 'report_path' and 'Digital_seal'
        result = ledger.calculate_final_verdict(
            req.doc_id, req.target, req.actual, req.breach_ratio, req.ratchet_bps
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_report(filename: str):
    # Ensure we look in the correct 'reports' directory
    file_path = os.path.join("reports", filename)
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, 
            media_type='application/pdf', 
            filename=filename,
            # 'attachment' forces the browser to download to local 'Downloads'
            content_disposition_type="attachment" 
        )
    raise HTTPException(status_code=404, detail="Audit Report PDF not found")