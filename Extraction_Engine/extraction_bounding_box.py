import os
import json
import fitz
from google import genai
from google.genai import types
import streamlit as st

MODEL_NAME = "gemini-2.5-flash"

client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)

response = client.models.list()
for m in response:
    print(m.name, m.description)
class LegalBrain:
    def __init__(self):
        self.model = MODEL_NAME

    def extract_text_blocks(self, pdf_path):
        doc = fitz.open(pdf_path)
        blocks = []
        # We need to search the WHOLE doc because your data is on pages 18 and 149
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text").lower()
            # Only send pages that actually have our data to save tokens/improve accuracy
            if any(kw in text for kw in ["project site", "ndvi", "bps", "latitude"]):
                for block in page.get_text("blocks"):
                    x0, y0, x1, y1, text, *_ = block
                    if text.strip():
                        blocks.append({
                            "p": page_idx + 1,
                            "t": text.strip(),
                            "b": [y0, x0, y1, x1] # Raw coordinates
                        })
        return blocks

    def extract_fields_with_gemini(self, blocks):
        # We pass the blocks as a JSON string within the contents
        prompt = """
        ACT AS: Data Extraction Robot. 
        INPUT: A list of text blocks from a legal PDF.
        
        TASK: Extract the EXACT values for these three fields.
        1. GPS: Find 'Latitude' and 'Longitude' in the text. Copy the numbers exactly.
        2. NDVI: Find 'Mean NDVI' or 'Threshold'. Extract the decimal (e.g., 0.75).
        3. MARGIN BPS: Find the 'bps' value. If it says '-5.0 bps', return '5.0'. 
           The '-' means 'reduction', it is NOT a negative number.

        JSON STRUCTURE:
        {
          "gps": {"value": "...", "raw_text_found": "..."},
          "ndvi": {"value": "...", "raw_text_found": "..."},
          "margin": {"value": "...", "raw_text_found": "..."}
        }
        
        STRICT: Do not invent data. Use ONLY the provided text blocks.
        """

        response = client.models.generate_content(
            model=self.model,
            contents=[prompt, f"DOC_BLOCKS: {json.dumps(blocks)}"],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0
            )
        )
        return json.loads(response.text)

    def run(self, pdf_path):
        blocks = self.extract_text_blocks(pdf_path)
        return self.extract_fields_with_gemini(blocks)

if __name__ == "__main__":
    brain = LegalBrain()
    # Ensure this file exists and was created by your generator
    PDF_FILE = "data/lma_150_dataset/LMA_Success_1.pdf" 
    result = brain.run(PDF_FILE)
    print(json.dumps(result, indent=2))