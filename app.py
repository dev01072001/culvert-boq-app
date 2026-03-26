import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF

# --- 1. THE LOOKUP TABLE (Standard A-G Design) ---
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

# --- 2. ENGINE BLOCKS (Line-by-Line Logic) ---

def calculate_box_geometry(row):
    # 1. Mid Wall Logic
    row["NO_OF_MID_WALLS"] = row["NO_OF_CELLS"] - 1 if row["NO_OF_CELLS"] > 1 else 0
    # 2. Total Length (Transverse)
    row["TOTAL_LENGTH"] = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + \
                         (2 * row["SIDE_WALL_THICKNESS"]) + \
                         (row["NO_OF_MID_WALLS"] * row["MID_WALL_THICKNESS"])
    # 3. Cushion
    row["CUSHION"] = row["FRL"] - row["GROUND_LEVEL"] - \
                     row["VERTICAL_CLEARANCE_OF_CULVERT"] - row["TOP_SLAB_THICKNESS"]
    # 4. Barrel Length
    row["BARREL_LENGTH"] = row["WIDTH_AS_PER_TCS"] + (row["SLOPE_COUNT"] * row["SIDE_SLOPE_RATIO"] * row["CUSHION"])
    return row

def calculate_protection_dimensions(row):
    # Ht and Len based on VC + TS
    box_inner_ht = row["VERTICAL_CLEARANCE_OF_CULVERT"] + row["TOP_SLAB_THICKNESS"]
    is_both = row["SIDE_SELECTION"] == "Both Sides"
    sel = row["PROT_SELECTION"]

    if sel == "Independent Retaining wall":
        row["PROT_COUNT"], row["PROT_HT"] = (4 if is_both else 2), box_inner_ht
        row["PROT_LEN"] = (1.5 * row["PROT_HT"]) - row["SIDE_WALL_THICKNESS"]
    elif sel == "Wing Wall + Return Wall":
        row["PROT_COUNT"], row["PROT_HT"] = (4 if is_both else 2), (box_inner_ht + 1.0) / 2
        row["PROT_LEN"] = (2 * (box_inner_ht - 1.0)) / np.cos(np.radians(45))
    elif sel == "U-Trough Wing Wall":
        row["PROT_COUNT"], row["PROT_HT"] = (2 if is_both else 1), (box_inner_ht + 1.0) / 2
        row["PROT_LEN"] = (2 * (box_inner_ht - 1.0)) / np.cos(np.radians(30))
        bw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
        row["PROT_AVG_WIDTH"] = (bw + (bw + (row["PROT_LEN"] * 2 * np.sin(np.radians(45))))) / 2
    elif sel == "U-Trough Along Alignment":
        row["PROT_COUNT"], row["PROT_HT"] = (2 if is_both else 1), box_inner_ht
        row["PROT_LEN"] = (2 * row["PROT_HT"]) - row["SIDE_WALL_THICKNESS"]
        row["PROT_WIDTH"] = row["BARREL_LENGTH"]
    return row

def assign_protection_sections(row):
    h_val, sel = row["PROT_HT"], row["PROT_SELECTION"]
    if sel in ["Wing Wall + Return Wall", "Independent Retaining wall"]:
        h_idx = max(1, min(10, int(round(h_val))))
        match = df_lookup[df_lookup['H'] == h_idx].iloc[0]
        for p in ['H1', 'W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = match[p]
        row["T_WALL_TOP"] = row["T_WALL_BASE"] = row["T_PROT_BASE_SLAB"] = 0
    else:
        # U-Trough Base Slab Logic (Different from box)
        row["T_WALL_TOP"] = 0.20
        row["T_WALL_BASE"] = 0.25 if h_val <= 2 else 0.30 if h_val <= 3 else 0.35 if h_val <= 4 else 0.40
        row["T_PROT_BASE_SLAB"] = row["T_WALL_BASE"]
        for p in ['H1', 'W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = 0
    return row

def calculate_toe_wall_geometry(row):
    sel, h_p = row["PROT_SELECTION"], row["PROT_HT"]
    row["TOE_WALL_COUNT"] = row["PROT_COUNT"] if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"] else 0
    if sel == "Wing Wall + Return Wall": row["L_TOE"] = 2 * np.pi * 2 * 0.25
    elif sel == "Independent Retaining wall": row["L_TOE"] = (2 * np.pi * np.sqrt(((h_p*2)**2 + (1.5*h_p)**2)/2))/4
    elif sel == "U-Trough Along Alignment": row["L_TOE"] = (h_p * 2 * np.pi * 2) / 4
    else: row["L_TOE"] = 0
    row["TOE_W"], row["TOE_A"], row["TOE_D"] = (0.6, 0.370, 1.05) if row["L_TOE"] > 0 else (0,0,0)
    return row

def calculate_curtain_wall_geometry(row):
    sel, loc = row["PROT_SELECTION"], row["CURTAIN_WALL_LOCATION"]
    box_iw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
    l_base = box_iw + (row["PROT_LEN"] * 2 * np.sin(np.radians(45))) if "Wing" in sel else (row["PROT_LEN"] * 2) + box_iw
    ds, us = {"D": 2.5, "A": 0.828, "W": 0.7}, {"D": 2.0, "A": 0.703, "W": 0.7}
    if loc == "Both Sides":
        row["CURT_COUNT"], row["L_CURT_T"], row["CURT_A_T"], row["CURT_D"] = 2, l_base*2, (ds["A"]+us["A"])*l_base, 2.25
    else:
        p = ds if loc == "D/S Only" else us
        row["CURT_COUNT"], row["L_CURT_T"], row["CURT_A_T"], row["CURT_D"] = 1, l_base, p["A"]*l_base, p["D"]
    row["CURT_W"] = 0.7
    row["L_BASE_SINGLE"] = l_base
    return row

def calculate_apron_geometry(row):
    sel, loc = row["PROT_SELECTION"], row["CURTAIN_WALL_LOCATION"]
    if "U-Trough" in sel: row["APRON_COUNT"], row["APRON_PLAN_AREA"] = 0, 0
    else:
        box_iw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
        area_single = ((box_iw + row["L_BASE_SINGLE"]) / 2) * row["PROT_LEN"]
        row["APRON_COUNT"] = 2 if loc == "Both Sides" else 1 if loc in ["U/S Only", "D/S Only"] else 0
        row["APRON_PLAN_AREA"] = area_single * row["APRON_COUNT"]
    return row

def calculate_master_quantities(row):
    n, off, sel = row["NO_OF_CULVERTS"], 1.0, row["PROT_SELECTION"]
    # 1. EXCAVATION (Separated)
    row["EXC_BOX"] = ((row["TOTAL_LENGTH"] + off) * (row["BARREL_LENGTH"] + off) * (row["THICK_BOTTOM_SLAB"] + 0.15)) * n
    pw = row["PROT_AVG_WIDTH"] if "U-Trough" in sel else row.get("W", 0.0)
    pd = (row["T_PROT_BASE_SLAB"] + 0.15) if "U-Trough" in sel else 2.15
    row["EXC_PROT"] = ((pw + off) * (row["PROT_LEN"] + off) * pd) * row["PROT_COUNT"] * n
    row["EXC_RET"] = (3.1 * 2.5 * 2.15) * row["PROT_COUNT"] * n if "Wing Wall" in sel else 0
    row["EXC_TOE"] = (0.6 + off) * row["TOE_D"] * row["L_TOE"] * row["TOE_WALL_COUNT"] * n
    row["EXC_CURT"] = (0.7 + off) * row["CURT_D"] * row["L_BASE_SINGLE"] * row["CURT_COUNT"] * n
    row["GRAND_EXC"] = row["EXC_BOX"] + row["EXC_PROT"] + row["EXC_RET"] + row["EXC_TOE"] + row["EXC_CURT"]

    # 2. PCC M15 (Unified offset)
    poff, tpcc = 0.3, 0.1
    p_box = (row["TOTAL_LENGTH"] + poff) * (row["BARREL_LENGTH"] + poff) * tpcc
    p_prot = ((pw + poff) * (row["PROT_LEN"] + poff) * tpcc) * row["PROT_COUNT"]
    p_ret = (2.05 * 1.80 * tpcc) * row["PROT_COUNT"] if "Wing Wall" in sel else 0
    p_toe = (0.6 + poff) * (row["L_TOE"] + poff) * tpcc * row["TOE_WALL_COUNT"]
    p_curt = (0.7 + poff) * (row["L_BASE_SINGLE"] + poff) * tpcc * row["CURT_COUNT"]
    row["GRAND_PCC"] = (p_box + p_prot + p_ret + p_toe + p_curt) * n

    # 3. RCC M35 (Box + Prot + Return)
    hk = 1.2 - row["THICK_BOTTOM_SLAB"]
    row["RCC_BOX"] = (row["TOTAL_LENGTH"]*row["BARREL_LENGTH"]*(row["THICK_BOTTOM_SLAB"]+row["TOP_SLAB_THICKNESS"]) + 
                     (2*row["SIDE_WALL_THICKNESS"] + row["NO_OF_MID_WALLS"]*row["MID_WALL_THICKNESS"])*row["VERTICAL_CLEARANCE_OF_CULVERT"]*row["BARREL_LENGTH"] + 
                     (0.5 * row["HAUNCH_SIZE"]**2 * 4 * row["NO_OF_CELLS"] * row["BARREL_LENGTH"]) + 
                     ((row["TOTAL_LENGTH"]*0.7*hk)*2 if row["SHEAR_KEY_REQUIRED"]=="Yes" else 0)) * n

    if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"]:
        aftg = (row["A"]*(row["F"]+row["E"])/2) + (row["B"]*row["E"]) + (row["C"]*(row["E"]+row["G"])/2)
        row["RCC_PROT"] = ((aftg + ((row["B"]+row["D"])/2)*row["PROT_HT"]) * row["PROT_LEN"] * row["PROT_COUNT"] + 
                          (aftg + ((row["B"]+row["D"])/2)*1.0) * 1.5 * row["PROT_COUNT"] if "Wing Wall" in sel else 0) * n
    else:
        row["RCC_PROT"] = (pw*row["PROT_LEN"]*row["T_PROT_BASE_SLAB"] + 2*row["PROT_HT"]*row["PROT_LEN"]*row["SIDE_WALL_THICKNESS"]) * row["PROT_COUNT"] * n

    # 4. Separate Grades (M25, M15)
    row["RCC_M25_TOE"] = row["TOE_A"] * row["L_TOE"] * row["TOE_WALL_COUNT"] * n
    row["RCC_M15_CURT"] = row["CURT_A_T"] * n

    # 5. Finishing & Drainage
    hbf = row["VERTICAL_CLEARANCE_OF_CULVERT"] + row["TOP_SLAB_THICKNESS"] + row["THICK_BOTTOM_SLAB"]
    row["TOT_BF"] = ((0.5*hbf**2*row["BARREL_LENGTH"]*2) + (0.5*row["PROT_HT"]**2*row["PROT_LEN"]*row["PROT_COUNT"]) + (0.5*1.0**2*1.5*row["PROT_COUNT"] if "Wing Wall" in sel else 0)) * n
    row["TOT_FM"] = ((hbf*0.6*row["BARREL_LENGTH"]*2) + (row["PROT_HT"]*0.6*row["PROT_LEN"]*row["PROT_COUNT"]) + (1.0*0.6*1.5*row["PROT_COUNT"] if "Wing Wall" in sel else 0)) * n
    row["STEEL_BOX"] = row["RCC_BOX"] * row["PERCENT_STEEL_BOX"]
    row["STEEL_PROT"] = row["RCC_PROT"] * row["PERCENT_STEEL_PROT"]
    row["TOT_WC"] = (row["LENGTH_OF_CULVERT"]*row["NO_OF_CELLS"]*row["BARREL_LENGTH"]*0.15)*n
    row["TOT_RIGID"] = row["APRON_PLAN_AREA"]*0.3*n
    row["TOT_LAUNCH"] = row["APRON_PLAN_AREA"]*0.45*n
    
    if sel in ["Independent Retaining wall", "U-Trough Along Alignment"]:
        slant = np.sqrt(row["PROT_HT"]**2 + (row["PROT_HT"]*2)**2)
        row["PITCH"] = (np.pi*(row["PROT_HT"]*2)*slant/2)*4*0.3*n
    else: row["PITCH"] = 0
    row["PITCH_FM"] = row["PITCH"]

    def wh(h, l): return (np.floor((h-0.6)/1.0)+1) * (np.floor(l/1.0)+1) if h>0.6 else 0
    row["WEEP"] = (wh(row["VERTICAL_CLEARANCE_OF_CULVERT"], row["BARREL_LENGTH"])*2 + wh(row["PROT_HT"], row["PROT_LEN"])*row["PROT_COUNT"]) * n
    return row

# --- 3. STREAMLIT INTERFACE ---

st.set_page_config(page_title="Culvert BOQ", layout="wide")
st.title("🏗️ Bridge Culvert BOQ Master Engine")

with st.sidebar:
    st.header("📋 Configuration")
    n_culv = st.number_input("Number of Culverts", value=1, min_value=1, key="sb_n")
    side_sel = st.selectbox("Side Selection", ["Both Sides", "One Side"], key="sb_s")
    prot_sel = st.selectbox("Protection Type", ["Independent Retaining wall", "Wing Wall + Return Wall", "U-Trough Wing Wall", "U-Trough Along Alignment"], key="sb_p")
    curt_loc = st.selectbox("Curtain Wall Location", ["Both Sides", "U/S Only", "D/S Only"], key="sb_c")
    sk_req = st.radio("Shear Key Required?", ["Yes", "No"], key="sb_sk")

c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("📍 Site Levels")
    rw, frl, gl = st.number_input("TCS Width (m)", value=7.0), st.number_input("FRL (m)", value=5.0), st.number_input("GL (m)", value=2.0)
    sl, sr = st.selectbox("Slopes", [0, 1, 2], index=2), st.number_input("Ratio", value=1.5)
with c2:
    st.subheader("📦 Box Specs")
    cl, ln, vc = st.number_input("Cells", value=1, min_value=1), st.number_input("Span L", value=2.0), st.number_input("Height VC", value=2.0)
    hz = st.number_input("Haunch", value=0.15)
with c3:
    st.subheader("🧱 Concrete/Steel")
    tt, tb, ts = st.number_input("Top Slab", value=0.25), st.number_input("Bottom Slab", value=0.25), st.number_input("Outer Wall", value=0.25)
    tm = st.number_input("Mid Wall", value=0.25) if cl > 1 else 0.0
    sbx, spr = st.number_input("Steel Box (kg/m3)", value=85.0), st.number_input("Steel Prot (kg/m3)", value=50.0)

if st.button("🚀 Calculate Final BOQ"):
    data = {"NO_OF_CULVERTS": n_culv, "SIDE_SELECTION": side_sel, "PROT_SELECTION": prot_sel, "CURTAIN_WALL_LOCATION": curt_loc, "SHEAR_KEY_REQUIRED": sk_req, "WIDTH_AS_PER_TCS": rw, "FRL": frl, "GROUND_LEVEL": gl, "SLOPE_COUNT": sl, "SIDE_SLOPE_RATIO": sr, "NO_OF_CELLS": cl, "LENGTH_OF_CULVERT": ln, "VERTICAL_CLEARANCE_OF_CULVERT": vc, "HAUNCH_SIZE": hz, "TOP_SLAB_THICKNESS": tt, "THICK_BOTTOM_SLAB": tb, "SIDE_WALL_THICKNESS": ts, "MID_WALL_THICKNESS": tm, "PERCENT_STEEL_BOX": sbx, "PERCENT_STEEL_PROT": spr}
    
    res = calculate_box_geometry(data)
    res = calculate_protection_dimensions(res); res = assign_protection_sections(res)
    res = calculate_toe_wall_geometry(res); res = calculate_curtain_wall_geometry(res)
    res = calculate_apron_geometry(res); res = calculate_master_quantities(res)

    st.success("✅ Success! All quantities calculated.")
    
    final_rows = [
        ["Excavation (Box Structure)", f"{res['EXC_BOX']:.2f}", "m3", "1.0m offset paylines"],
        ["Excavation (Protection Walls)", f"{res['EXC_PROT']:.2f}", "m3", "Footing logic"],
        ["Excavation (Return Walls)", f"{res['EXC_RET']:.2f}", "m3", "3.1x2.5 fixed"],
        ["Excavation (Toe & Curtain)", f"{res['EXC_TOE']+res['EXC_CURT']:.2f}", "m3", "Structural footprint"],
        ["**TOTAL EXCAVATION**", f"{res['GRAND_EXC']:.2f}", "m3", "Sum of all earthwork"],
        ["PCC Grade M15 (Grand Total)", f"{res['GRAND_PCC']:.2f}", "m3", "100mm layer + 300mm offset"],
        ["RCC Grade M35 (Box Structure)", f"{res['RCC_BOX']:.2f}", "m3", "Slabs+Side+Mid+Haunch+Keys"],
        ["RCC Grade M35 (Prot + Return)", f"{res['RCC_PROT']:.2f}", "m3", "Stem and Footing volumes"],
        ["RCC Grade M25 (Toe Walls)", f"{res['RCC_M25_TOE']:.2f}", "m3", "0.370 area logic"],
        ["RCC Grade M15 (Curtain Walls)", f"{res['RCC_M15_CURT']:.2f}", "m3", "0.7m width logic"],
        ["Steel: Box Reinforcement", f"{res['STEEL_BOX']:.2f}", "kg", "Box Concrete * Ratio"],
        ["Steel: Protection Reinforcement", f"{res['STEEL_PROT']:.2f}", "kg", "Prot Concrete * Ratio"],
        ["**GRAND TOTAL STEEL**", f"{res['STEEL_BOX']+res['STEEL_PROT']:.2f}", "kg", "Total HYSD bars"],
        ["Total Backfill (1:1 Slope)", f"{res['TOT_BF']:.2f}", "m3", "0.5*H^2*L Rule"],
        ["Total Filter Media", f"{res['TOT_FM']:.2f}", "m3", "600mm vertical drainage"],
        ["Wearing Course (150mm)", f"{res['TOT_WC']:.2f}", "m3", "Internal floor PCC"],
        ["Rigid Apron (300mm)", f"{res['TOT_RIGID']:.2f}", "m3", "Floor protection"],
        ["Launching Apron (450mm)", f"{res['TOT_LAUNCH']:.2f}", "m3", "Scour protection"],
        ["Quadrant Slope Pitching", f"{res['PITCH']:.2f}", "m3", "Slant quadrant area * 0.3"],
        ["Pitching Filter Media", f"{res['PITCH_FM']:.2f}", "m3", "0.3m thk layer"],
        ["Weep Holes (100mm PVC)", f"{res['WEEP']:.0f}", "Nos", "1m c/c spacing"]
    ]
    st.table(pd.DataFrame(final_rows, columns=["Description", "Quantity", "Unit", "Logic Audit"]))

    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 14); pdf.cell(190, 10, "BRIDGE CULVERT BOQ REPORT", ln=True, align='C')
    pdf.set_font("Arial", size=9)
    for r in final_rows:
        pdf.cell(80, 8, r[0].replace("**",""), 1); pdf.cell(30, 8, r[1], 1, 0, 'C'); pdf.cell(20, 8, r[2], 1, 0, 'C'); pdf.cell(60, 8, r[3], 1); pdf.ln()
    pdf_out = pdf.output(dest='S').encode('latin-1')
    st.download_button("📥 Download Official PDF", data=pdf_out, file_name="Detailed_BOQ.pdf", mime="application/pdf", key="pdf_dl")
