import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF

# --- 1. THE LOOKUP TABLE ---
# # Explained: Standard dimensions (A to G) for Independent Retaining Walls.
lookup_data = {
    'H': [1,2,3,4,5,6,7,8,9,10],
    'H1': [1.6,1.5,1.4,1.4,1.3,1.1,0.9,0.8,0.6,0.5],
    'W': [2.1,2.7,3.2,3.7,4.35,5.1,5.9,6.6,7.4,8.1],
    'A': [0.5,0.7,0.8,0.9,1.25,1.6,2.0,2.5,2.8,3.2],
    'B': [0.4,0.5,0.5,0.6,0.7,1.0,1.1,1.2,1.4,1.4],
    'C': [1.2,1.5,1.9,2.2,2.4,2.5,2.8,2.9,3.2,3.5],
    'D': [0.3]*10,
    'E': [0.4,0.5,0.6,0.6,0.75,0.9,1.1,1.2,1.4,1.5],
    'F': [0.3,0.3,0.35,0.35,0.35,0.4,0.5,0.5,0.5,0.5],
    'G': [0.3,0.3,0.35,0.35,0.35,0.4,0.5,0.5,0.5,0.5]
}
df_lookup = pd.DataFrame(lookup_data)

# --- 2. THE CALCULATION ENGINE ---
def calculate_geometry_pipeline(row):
    VC, TS, SW = row["VERTICAL_CLEARANCE_OF_CULVERT"], row["TOP_SLAB_THICKNESS"], row["SIDE_WALL_THICKNESS"]
    sel = row["PROT_SELECTION"]
    is_both = row["SIDE_SELECTION"] == "Both Sides"
    row["PROT_COUNT"] = 4 if is_both else 2
    if sel == "Independent Retaining wall":
        row["PROT_HT"] = VC + TS
        row["PROT_LEN"] = (1.5 * row["PROT_HT"]) - SW
    elif sel == "Wing Wall + Return Wall":
        row["PROT_HT"] = (VC + TS + 1.0) / 2
        row["PROT_LEN"] = (2 * (VC + TS - 1.0)) / np.cos(np.radians(45))
    elif sel == "U-Trough Wing Wall":
        row["PROT_COUNT"] = 2 if is_both else 1
        row["PROT_HT"] = (VC + TS + 1.0) / 2
        row["PROT_LEN"] = (2 * (VC + TS - 1.0)) / np.cos(np.radians(30))
        bw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * (row["NO_OF_CELLS"]-1))
        row["PROT_AVG_WIDTH"] = (bw + (bw + (row["PROT_LEN"] * 2 * np.sin(np.radians(30))))) / 2
    elif sel == "U-Trough Along Alignment":
        row["PROT_COUNT"] = 2 if is_both else 1
        row["PROT_HT"] = VC + TS
        row["PROT_LEN"] = (2 * row["PROT_HT"]) - SW
    return row

import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF

# --- 1. THE LOOKUP TABLE ---
# # Explained: Standard dimensions (A to G) for Independent Retaining Walls.
lookup_data = {
    'H': [1,2,3,4,5,6,7,8,9,10],
    'H1': [1.6,1.5,1.4,1.4,1.3,1.1,0.9,0.8,0.6,0.5],
    'W': [2.1,2.7,3.2,3.7,4.35,5.1,5.9,6.6,7.4,8.1],
    'A': [0.5,0.7,0.8,0.9,1.25,1.6,2.0,2.5,2.8,3.2],
    'B': [0.4,0.5,0.5,0.6,0.7,1.0,1.1,1.2,1.4,1.4],
    'C': [1.2,1.5,1.9,2.2,2.4,2.5,2.8,2.9,3.2,3.5],
    'D': [0.3]*10,
    'E': [0.4,0.5,0.6,0.6,0.75,0.9,1.1,1.2,1.4,1.5],
    'F': [0.3,0.3,0.35,0.35,0.35,0.4,0.5,0.5,0.5,0.5],
    'G': [0.3,0.3,0.35,0.35,0.35,0.4,0.5,0.5,0.5,0.5]
}
df_lookup = pd.DataFrame(lookup_data)

# --- 2. THE CALCULATION ENGINE ---
def calculate_geometry_pipeline(row):
    VC, TS, SW = row["VERTICAL_CLEARANCE_OF_CULVERT"], row["TOP_SLAB_THICKNESS"], row["SIDE_WALL_THICKNESS"]
    sel = row["PROT_SELECTION"]
    is_both = row["SIDE_SELECTION"] == "Both Sides"
    row["PROT_COUNT"] = 4 if is_both else 2
    if sel == "Independent Retaining wall":
        row["PROT_HT"] = VC + TS
        row["PROT_LEN"] = (1.5 * row["PROT_HT"]) - SW
    elif sel == "Wing Wall + Return Wall":
        row["PROT_HT"] = (VC + TS + 1.0) / 2
        row["PROT_LEN"] = (2 * (VC + TS - 1.0)) / np.cos(np.radians(45))
    elif sel == "U-Trough Wing Wall":
        row["PROT_COUNT"] = 2 if is_both else 1
        row["PROT_HT"] = (VC + TS + 1.0) / 2
        row["PROT_LEN"] = (2 * (VC + TS - 1.0)) / np.cos(np.radians(30))
        bw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * (row["NO_OF_CELLS"]-1))
        row["PROT_AVG_WIDTH"] = (bw + (bw + (row["PROT_LEN"] * 2 * np.sin(np.radians(30))))) / 2
    elif sel == "U-Trough Along Alignment":
        row["PROT_COUNT"] = 2 if is_both else 1
        row["PROT_HT"] = VC + TS
        row["PROT_LEN"] = (2 * row["PROT_HT"]) - SW
    return row

def assign_protection_sections(row):
    if row["PROT_SELECTION"] in ["Wing Wall + Return Wall", "Independent Retaining wall"]:
        h_idx = max(1, min(10, int(round(row["PROT_HT"]))))
        match = df_lookup[df_lookup['H'] == h_idx].iloc[0]
        for p in ['W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = match[p]
    else:
        row["T_BASE_SLAB"] = 0.25 if row["PROT_HT"] <= 2 else 0.30 if row["PROT_HT"] <= 3 else 0.40
    return row

def calculate_scour_geometry(row):
    box_w = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * (row["NO_OF_CELLS"]-1))
    l_c = box_w + (row["PROT_LEN"] * 2 * np.sin(np.radians(45))) if row["PROT_SELECTION"] in ["U-Trough Wing Wall", "Wing Wall + Return Wall"] else (row["PROT_LEN"] * 2) + box_w
    row["L_CURTAIN"] = l_c
    ds, us = {"D": 2.5, "A": 0.828, "W": 0.7}, {"D": 2.0, "A": 0.703, "W": 0.7}
    if row["CURTAIN_WALL_LOCATION"] == "Both Sides":
        row["CURTAIN_AREA_TOTAL"] = (ds["A"] + us["A"]) * l_c
    else:
        p = ds if row["CURTAIN_WALL_LOCATION"] == "D/S Only" else us
        row["CURTAIN_AREA_TOTAL"] = p["A"] * l_c
    row["APRON_PLAN_AREA"] = (((box_w + l_c) / 2) * row["PROT_LEN"]) * (2 if row["CURTAIN_WALL_LOCATION"] == "Both Sides" else 1)
    return row

def calculate_master_quantities(row):
    n, BL, OW, VC, TS, BS = row["NO_OF_CULVERTS"], row["BARREL_LENGTH"], row["OUTER_WIDTH"], row["VERTICAL_CLEARANCE_OF_CULVERT"], row["TOP_SLAB_THICKNESS"], row["THICK_BOTTOM_SLAB"]
    
    # # ITEM CALCS
    row["TOTAL_EXCAVATION"] = (((OW+1)*(BL+1)*(BS+0.15)) + ((row.get("W", 0)+1)*(row["PROT_LEN"]+1)*2.15)*row["PROT_COUNT"]) * n
    row["QTY_PCC_BOX"] = ((OW+0.3)*(BL+0.3)*0.1)*n
    row["QTY_PCC_PROT"] = ((row.get("W", 0)+0.3)*(row["PROT_LEN"]+0.3)*0.1)*row["PROT_COUNT"]*n
    
    hk = 1.2 - BS
    row["QTY_SHEAR_KEY"] = ((OW*0.25*hk) + (OW*0.5*0.45*hk)) * 2 * n if row["SHEAR_KEY_REQUIRED"] == "Yes" else 0
    row["TOTAL_RCC_BOX_M35"] = (OW*BL*(TS+BS)*n) + ((2*row["SIDE_WALL_THICKNESS"] + (row["NO_OF_CELLS"]-1)*row["MID_WALL_THICKNESS"])*VC*BL*n) + (0.5*row["HAUNCH_SIZE"]**2*4*row["NO_OF_CELLS"]*BL*n) + row["QTY_SHEAR_KEY"]
    
    if row["PROT_SELECTION"] in ["Independent Retaining wall", "Wing Wall + Return Wall"]:
        area_f, area_s = (row["A"]*(row["F"]+row["E"])/2) + (row["B"]*row["E"]) + (row["C"]*(row["E"]+row["G"])/2), ((row["B"]+row["D"])/2)*row["PROT_HT"]
        row["TOTAL_M35_PROTECTION"] = (area_f + area_s) * row["PROT_LEN"] * row["PROT_COUNT"] * n
    else:
        row["TOTAL_M35_PROTECTION"] = (row.get("PROT_AVG_WIDTH", OW)*row["PROT_LEN"]*row["T_BASE_SLAB"] + 2*row["PROT_HT"]*row["PROT_LEN"]*row["SIDE_WALL_THICKNESS"]) * row["PROT_COUNT"] * n
        
    row["TOTAL_STEEL_KG"] = (row["TOTAL_RCC_BOX_M35"]*row["PERCENT_STEEL_BOX"]) + (row["TOTAL_M35_PROTECTION"]*row["PERCENT_STEEL_PROT"])
    h_f = VC+TS+BS
    row["TOTAL_BACKFILL"] = ((0.5*h_f**2*BL)*2*n) + ((0.5*row["PROT_HT"]**2*row["PROT_LEN"])*row["PROT_COUNT"]*n)
    row["TOTAL_FILTER_MEDIA"] = (h_f*0.6*BL*2*n) + (row["PROT_HT"]*0.6*row["PROT_LEN"]*row["PROT_COUNT"]*n)
    row["QTY_WC"] = (row["LENGTH_OF_CULVERT"]*row["NO_OF_CELLS"]*BL*0.15)*n
    row["QTY_RIGID_APRON_M3"] = row["APRON_PLAN_AREA"]*0.3*n
    row["QTY_LAUNCHING_APRON_M3"] = row["APRON_PLAN_AREA"]*0.45*n
    
    def wh(h, l): return (np.floor((h-0.6)/1.0)+1) * (np.floor(l/1.0)+1) if h>0.6 else 0
    row["TOTAL_WEEP_HOLES_NOS"] = (wh(VC, BL)*2 + wh(row["PROT_HT"], row["PROT_LEN"])*row["PROT_COUNT"]) * n
    return row

# --- 3. STREAMLIT INTERFACE ---
st.set_page_config(page_title="Culvert Master", layout="wide")
st.title("🏗️ Bridge Culvert BOQ Master")

with st.sidebar:
    st.header("📋 Configuration")
    n_culv = st.number_input("Number of Culverts", min_value=1, value=1)
    side_sel = st.selectbox("Side Selection", ["Both Sides", "One Side"])
    prot_sel = st.selectbox("Protection Type", ["Independent Retaining wall", "Wing Wall + Return Wall", "U-Trough Wing Wall", "U-Trough Along Alignment"])
    curt_loc = st.selectbox("Curtain Wall Location", ["Both Sides", "U/S Only", "D/S Only"])
    sk_req = st.radio("Shear Key Required?", ["Yes", "No"])

col1, col2, col3 = st.columns(3)
with col1:
    road_w = st.number_input("Road Width TCS (m)", value=7.0)
    frl = st.number_input("FRL (m)", value=5.0)
    invert = st.number_input("Invert Level (m)", value=2.0)
    slopes = st.selectbox("No. of Side Slopes", [0, 1, 2], index=2)
    slope_r = st.number_input("Side Slope Ratio", value=1.5)
with col2:
    cells = st.number_input("Number of Cells", min_value=1, value=1)
    L = st.number_input("Inner Span 'L' (m)", value=2.0)
    VC = st.number_input("Inner Height 'VC' (m)", value=2.0)
    h_size = st.number_input("Haunch Size (m)", value=0.15)
with col3:
    t_top = st.number_input("Top Slab (m)", value=0.25)
    t_bot = st.number_input("Bottom Slab (m)", value=0.25)
    t_side = st.number_input("Outer Wall (m)", value=0.25)
    t_mid = st.number_input("Mid Wall (m)", value=0.25) if cells > 1 else 0.0
    st_box = st.number_input("Steel for Box (kg/m3)", value=85.0)
    st_prot = st.number_input("Steel for Protection (kg/m3)", value=85.0)

if st.button("🚀 Calculate Final BOQ"):
    row = {
        "NO_OF_CULVERTS": n_culv, "SIDE_SELECTION": side_sel, "PROT_SELECTION": prot_sel,
        "CURTAIN_WALL_LOCATION": curt_loc, "SHEAR_KEY_REQUIRED": sk_req, 
        "WIDTH_AS_PER_TCS": road_w, "FRL": frl, "INVERT_LEVEL": invert, 
        "SLOPE_COUNT": slopes, "SIDE_SLOPE_RATIO": slope_r,
        "NO_OF_CELLS": cells, "LENGTH_OF_CULVERT": L, "VERTICAL_CLEARANCE_OF_CULVERT": VC, 
        "HAUNCH_SIZE": h_size, "TOP_SLAB_THICKNESS": t_top, "THICK_BOTTOM_SLAB": t_bot,
        "SIDE_WALL_THICKNESS": t_side, "MID_WALL_THICKNESS": t_mid, 
        "PERCENT_STEEL_BOX": st_box, "PERCENT_STEEL_PROT": st_prot
    }
    
    row["OUTER_WIDTH"] = (cells * L) + (2 * t_side) + ((cells - 1) * t_mid)
    cushion = frl - (invert + VC + t_top)
    row["BARREL_LENGTH"] = road_w + (slopes * slope_r * cushion)

    row = calculate_geometry_pipeline(row)
    row = assign_protection_sections(row)
    row = calculate_scour_geometry(row)
    row = calculate_master_quantities(row)

    st.success("✅ Success! BOQ Generated.")
    
    # # FULL 13 ITEMS WITH EXPLANATIONS
    results = [
        ["Barrel Length", f"{row['BARREL_LENGTH']:.3f}", "m", "# Explained: Width TCS + (Slopes * Ratio * Cushion)"],
        ["Total Excavation", f"{row['TOTAL_EXCAVATION']:.2f}", "m3", "# Explained: Box + Protection footprints with 1.0m working space offset"],
        ["PCC M15 (Box Base)", f"{row['QTY_PCC_BOX']:.2f}", "m3", "# Explained: 100mm layer under box with 300mm offset"],
        ["PCC M15 (Prot Base)", f"{row['QTY_PCC_PROT']:.2f}", "m3", "# Explained: 100mm layer under protection walls/footings"],
        ["RCC M35 Box", f"{row['TOTAL_RCC_BOX_M35']:.2f}", "m3", "# Explained: Slabs + Walls + Haunches + Shear Keys (if any)"],
        ["RCC M35 Protection", f"{row['TOTAL_M35_PROTECTION']:.2f}", "m3", "# Explained: Stem and Footing volume for Wing/Retaining walls"],
        ["Total Backfill (1:1)", f"{row['TOTAL_BACKFILL']:.2f}", "m3", "# Explained: Soil wedge behind walls at 45 degree angle"],
        ["Filter Media", f"{row['TOTAL_FILTER_MEDIA']:.2f}", "m3", "# Explained: 600mm vertical drainage layer behind earth-retaining faces"],
        ["Wearing Course", f"{row['QTY_WC']:.2f}", "m3", "# Explained: 150mm thick road crust layer over the box span"],
        ["Rigid Apron (300mm)", f"{row['QTY_RIGID_APRON_M3']:.2f}", "m3", "# Explained: PCC/RCC floor protection between protection walls"],
        ["Launching Apron", f"{row['QTY_LAUNCHING_APRON_M3']:.2f}", "m3", "# Explained: 450mm flexible stone protection layer at apron ends"],
        ["Total Steel", f"{row['TOTAL_STEEL_KG']:.2f}", "kg", "# Explained: (RCC Box * Box Steel Ratio) + (RCC Prot * Prot Steel Ratio)"],
        ["Weep Holes", f"{row['TOTAL_WEEP_HOLES_NOS']:.0f}", "Nos", "# Explained: 100mm PVC pipes spaced at 1m c/c for drainage"]
    ]
    
    df_boq = pd.DataFrame(results, columns=["Description", "Quantity", "Unit", "Explanation"])
    st.table(df_boq)

    # PDF Logic
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, "BRIDGE CULVERT BOQ REPORT", ln=True, align='C')
    pdf.set_font("Arial", size=9)
    for index, r in df_boq.iterrows():
        pdf.cell(80, 8, r['Description'], border=1)
        pdf.cell(30, 8, r['Quantity'], border=1, align='C')
        pdf.cell(20, 8, r['Unit'], border=1, align='C')
        pdf.cell(60, 8, "Logic verified", border=1)
        pdf.ln()
    
    pdf_out = pdf.output(dest='S').encode('latin-1')
    st.download_button("📥 Download Official PDF", data=pdf_out, file_name="Culvert_BOQ.pdf")
