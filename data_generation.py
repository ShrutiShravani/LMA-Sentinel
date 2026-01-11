from fpdf import FPDF

from faker import Faker

import os

import random



fake = Faker()



regions = {

    "Success": {"lat_range": (61.0, 62.0), "lon_range": (24.0, 25.0), "target": "0.75 (Seventy-five per centum)","margin_bps": "5.0","desc": "Boreal Forest Asset"},

    "Breach": {"lat_range": (-10.5, -9.5), "lon_range": (-55.5, -54.5), "target": "0.82 (Eighty-two per centum)", "margin_bps": "7.5","desc": "Amazon Preservation Zone"},

    "Failure": {"lat": "NOT_PROVIDED", "lon": "NOT_PROVIDED", "target": "0.70","margin_bps":"2.5", "desc": "Incomplete Reporting"}

}



def generate_lma_150(category, doc_id):

    pdf = FPDF()

    pdf.set_auto_page_break(auto=True, margin=15)

    

    # --- PAGE 1: COVER PAGE (SENSITIVE) ---

    pdf.add_page()

    pdf.set_font("Times", 'B', 14)

    borrower = fake.company().upper()

    lender = f"{fake.last_name()} BANK PLC"

    

    pdf.multi_cell(0, 10, f"DATED {fake.date().upper()}\n\n(1) {borrower} (as Borrower)\n\n(2) {lender} (as Original Lender)\n\n(3) {fake.name().upper()} (as Agent)", align='L')

    pdf.ln(20)

    pdf.set_font("Times", 'B', 22)

    pdf.cell(0, 20, "EUR 750,000,000 REVOLVING CREDIT FACILITY", ln=True, align='C')



    # --- PAGES 2-148: MASSIVE BOILERPLATE ---

    # We increase this to 148 to make the total doc ~150 pages

    for i in range(2, 149):

        pdf.add_page()

        pdf.set_font("Times", 'B', 10)

        pdf.cell(0, 10, f"CLAUSE {i}. OPERATIONAL COVENANTS AND REPRESENTATIONS", ln=True)

        pdf.set_font("Times", '', 9)

        

        if i == 18:

            pdf.multi_cell(0, 5, "18.3 Sustainability Margin Adjustment: As specified in Schedule 4, "

                                 "the Margin shall be adjusted based on Satellite NDVI Verification.")

        else:

            # Add dense legal text

            pdf.multi_cell(0, 5, fake.text(max_nb_chars=3000))



    # --- PAGE 149: THE ESG DATA (THE NEEDLE) ---

    pdf.add_page()

    pdf.set_font("Times", 'B', 12)

    pdf.cell(0, 10, "SCHEDULE 4: SUSTAINABILITY PERFORMANCE TARGETS (SPTs)", ln=True, align='C')

    

    reg = regions[category]

    lat_str = str(round(random.uniform(reg["lat_range"][0], reg["lat_range"][1]), 5)) if "lat_range" in reg else reg["lat"]

    lon_str = str(round(random.uniform(reg["lon_range"][0], reg["lon_range"][1]), 5)) if "lon_range" in reg else reg["lon"]



    prose = (

        f"The Project Site is defined as the area centered at Latitude {lat_str} and Longitude {lon_str}. "

        f"The Borrower shall ensure the Mean NDVI exceeds the threshold of {reg['target']}. "
        f"In the event the Sustainability Performance Target is met, the Sustainability Margin Adjustment "
        f"shall result in a reduction of the Margin by {reg['margin_bps']} bps. "

        f"Verification will be performed by the Agent using Sentinel-2 Spectral Imagery."

    )

    pdf.set_font("Times", '', 11)

    pdf.multi_cell(0, 7, prose)



    # --- PAGE 150: THE SIGNATORIES & CONTACTS (FOR MASKING TEST) ---

    pdf.add_page()

    pdf.set_font("Times", 'B', 12)

    pdf.cell(0, 10, "SCHEDULE 5: ADDRESSES FOR NOTICES", ln=True, align='C')

    pdf.ln(5)

    pdf.set_font("Times", '', 10)

    

    # This data is purely for your PII Masking engine to "catch"

    pdf.multi_cell(0, 7, f"THE BORROWER: {borrower}\nAddress: {fake.address()}\n"

                         f"Attention: {fake.name()}\nEmail: {fake.email()}\n"

                         f"Account No: {fake.bban()}\nSWIFT: {fake.swift()}\n\n"

                         f"THE LENDER: {lender}\nIBAN: {fake.iban()}\n"

                         f"Contact: {fake.name()} (Director)")



    folder = "data/lma_150_dataset"

    os.makedirs(folder, exist_ok=True)

    pdf.output(f"{folder}/LMA_{category}_{doc_id}.pdf")



# Run generation

for cat in ["Success", "Breach", "Failure"]:

    for i in range(1, 6):

        generate_lma_150(cat, i)