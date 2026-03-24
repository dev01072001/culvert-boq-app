import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import base64

# --- 1. A-G LOOKUP TABLE ---
lookup_data = {
    'H': [1,2,3,4,5,6,7,8,9,10],
    'H1': [1.6,1.5,1.4,1.4,1.3,1.1,0.9,0.8,0.6,0.5],
    'W': [2.1,2.7,3.2,3.7,4.35,5.1,5.9,6.6,7.4,8.1],
    'A': [0.5,0.7,0.8,0.9,1.25,1.6,2.0,2.5,2.8,3.2],
    'B': [0.4,0.5,0.5,0.6,0.7,1.0,1.1,1.2,1.4,1.4],
    'C': [1.2,1.5,1.9,2.2,2.4,2.5,2.8,2.9,3.2,3.5],
    'D': [0.3]*10,
    'E': [0.4,0.5,0.6,0.6,0.75,0.9,1.1,1.25,1.4,1.5],
    'F': [0.3,0.3,0.35,0.35,0.35,0.4,0.5,0.5,0.5,0.5],
    'G': [0.3,0.3,0.35,0.35,0.35,0.4,0.5,0.5,0.5,0.5]
}
df_lookup = pd.DataFrame(lookup_data)

# --- 2. ENGINE ---
def calculate_master_boq(row):
    n = row["NO_OF_CULVERTS"]
    VC, TS, BS, SW = row["VC"], row["TS"], row["BS"], row["SW"]
    L, ROAD_W, MW = row["L"], row["ROAD_W"], row["MW"]
    sel = row["PROT_SEL"]

    cushion = row["FRL"] - (row["INVERT"] + VC + TS)
    row["CUSHION"] = cushion
    row["BL"] = ROAD_W + (row["SLOPE_COUNT"] * row["SLOPE_RATIO"] * cushion)
    row["OW"] = (row["CELLS"] * L) + (2 * SW) + ((row["CELLS"]-1) * MW)
    OW, BL = row["OW"], row["BL"]

    row["PROT_COUNT"] = 4 if row["SIDE_SEL"] == "Both Sides" else 2
    if sel == "Independent Retaining wall":
        row["PROT_HT"] = VC + TS
        row["PROT_LEN"] = (1.5 * row["PROT_HT"]) - SW
    elif sel == "Wing Wall + Return Wall":
        row["PROT_HT"] = (VC + TS + 1.0) / 2
        row["PROT_LEN"] = (2 * (VC + TS - 1.0)) / np.cos(np.radians(45))
    else:
        row["PROT_HT"] = VC + TS
        row["PROT_LEN"] = (2 * row["PROT_HT"]) - SW

    if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"]:
        h_idx = max(1, min(10, int(round(row["PROT_HT"]))))
        match = df_lookup[df_lookup['H'] == h_idx].iloc[0]
        for p in ['W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = match[p]
    else:
        row["W"] = OW
        row["T_BASE_SLAB"] = 0.30

    row["EXC"] = (((OW+1)*(BL+1)*(BS+0.15)) + ((row.get("W", 0)+1)*(row["PROT_LEN"]+1)*2.15)*row["PROT_COUNT"]) * n
    row["PCC_BOX"] = ((OW+0.3)*(BL+0.3)*0.1)*n
    row["PCC_PROT"] = ((row.get("W", 0)+0.3)*(row["PROT_LEN"]+0.3)*0.1)*row["PROT_COUNT"]*n
    
    hk = 1.2 - BS
    row["S_KEY"] = ((OW*0.25*hk) + (OW*0.5*0.45*hk)) * 2 * n if row["S_KEY_REQ"] == "Yes" else 0
    row["RCC_BOX"] = (OW*BL*(TS+BS)*n) + ((2*SW + (row["CELLS"]-1)*MW)*VC*BL*n) + (0.5*row["H_SIZE"]**2*4*row["CELLS"]*BL*n) + row["S_KEY"]
    
    if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"]:
        area_f = (row["A"]*(row["F"]+row["E"])/2) + (row["B"]*row["E"]) + (row["C"]*(row["E"]+row["G"])/2)
        area_s = ((row["B"]+row["D"])/2)*row["PROT_HT"]
        row["RCC_PROT"] = (area_f + area_s) * row["PROT_LEN"] * row["PROT_COUNT"] * n
    else:
        row["RCC_PROT"] = (row.get("W", OW)*row["PROT_LEN"]*0.3 + 2*row["PROT_HT"]*row["PROT_LEN"]*SW) * row["PROT_COUNT"] * n

    row["BACKFILL"] = ((0.5*(VC+TS+BS)**2*BL)*2*n) + ((0.5*row["PROT_HT"]**2*row["PROT_LEN"])*row["PROT_COUNT"]*n)
    row["FM"] = ((VC+TS+BS)*0.6*BL*2*n) + (row["PROT_HT"]*0.6*row["PROT_LEN"]*row["PROT_COUNT"]*n)
    row["WC"] = (row["L"]*row["CELLS"]*BL*0.15)*n
    row["STEEL"] = (row["RCC_BOX"]*row["ST_BOX"] + row["RCC_PROT"]*row["ST_PROT"])
    
    box_w = (L * row["CELLS"]) + (MW * (row["CELLS"]-1))
    l_c = box_w + (row["PROT_LEN"] * 2 * np.sin(np.radians(45)))
    apron_area = (((box_w + l_c) / 2) * row["PROT_LEN"]) * 2
    row["RIGID"] = apron_area * 0.3 * n
    row["LAUNCH"] = apron_area * 0.45 * n
    
    def wh(h, l): return (np.floor((h-0.6)/1.0)+1) * (np.floor(l/1.0)+1) if h>0.6 else 0
    row["WEEP"] = (wh(VC, BL)*2 + wh(row["PROT_HT"], row["PROT_LEN"])*row["PROT_COUNT"]) * n

    return row

# --- 3. PDF GENERATOR ---
def create_pdf(res):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "IIT GUWAHATI - CULVERT BOQ REPORT", ln=True, align='C')
    pdf.ln(10)
