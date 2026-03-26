import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF

# --- 1. THE LOOKUP TABLE ---
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

# --- 2. ENGINE BLOCKS (Strict Logic) ---

def calculate_box_geometry(row):
    row["NO_OF_MID_WALLS"] = row["NO_OF_CELLS"] - 1 if row["NO_OF_CELLS"] > 1 else 0
    row["TOTAL_LENGTH"] = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + \
                         (2 * row["SIDE_WALL_THICKNESS"]) + \
                         (row["NO_OF_MID_WALLS"] * row["MID_WALL_THICKNESS"])
    row["CUSHION"] = row["FRL"] - row["GROUND_LEVEL"] - row["VERTICAL_CLEARANCE_OF_CULVERT"] - row["TOP_SLAB_THICKNESS"]
    row["BARREL_LENGTH"] = row["WIDTH_AS_PER_TCS"] + (row["SLOPE_COUNT"] * row["SIDE_SLOPE_RATIO"] * row["CUSHION"])
    return row

def calculate_protection_dimensions(row):
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
        start_w = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
        end_w = start_w + (row["PROT_LEN"] * 2 * np.sin(np.radians(45)))
        row["PROT_AVG_WIDTH"] = (start_w + end_w) / 2
    elif sel == "U-Trough Along Alignment":
        row["PROT_COUNT"], row["PROT_HT"] = (2 if is_both else 1), box_inner_ht
        row["PROT_LEN"] = (2 * row["PROT_HT"]) - row["SIDE_WALL_THICKNESS"]
        row["PROT_AVG_WIDTH"] = row["BARREL_LENGTH"]
    return row

def assign_protection_sections(row):
    h_val, selection = row["PROT_HT"], row["PROT_SELECTION"]
    if selection in ["Wing Wall + Return Wall", "Independent Retaining wall"]:
        h_idx = max(1, min(10, int(round(h_val))))
        match = df_lookup[df_lookup['H'] == h_idx].iloc[0]
        for p in ['H1', 'W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = match[p]
        row["T_BASE_SLAB"] = 0
    else:
        row["T_BASE_SLAB"] = 0.25 if h_val <= 2 else 0.30 if h_val <= 3 else 0.35 if h_val <= 4 else 0.40
        for p in ['H1', 'W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = 0
    return row

def calculate_toe_wall_geometry(row):
    sel, h_prot = row["PROT_SELECTION"], row["PROT_HT"]
    row["TOE_WALL_COUNT"] = row["PROT_COUNT"] if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"] else 0
    if sel == "Wing Wall + Return Wall": row["L_TOE"] = 2 * np.pi * 2 * 0.25
    elif sel == "Independent Retaining wall": row["L_TOE"] = (2 * np.pi * np.sqrt(((h_prot*2)**2 + (1.5*h_prot)**2)/2))/4
    elif sel == "U-Trough Along Alignment": row["L_TOE"] = (h_prot * 2 * np.pi * 2) / 4
    else: row["L_TOE"] = 0
    row["TOE_WALL_WIDTH"], row["TOE_WALL_X_AREA"], row["TOE_WALL_DEPTH"] = (0.6, 0.370, 1.05) if row["L_TOE"] > 0 else (0,0,0)
    return row

def calculate_curtain_wall_geometry(row):
    location = row["CURTAIN_WALL_LOCATION"]
    box_iw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
    l_base = box_iw + (row["PROT_LEN"] * 2 * np.sin(np.radians(45))) if "Wing" in row["PROT_SELECTION"] else (row["PROT_LEN"] * 2) + box_iw
    ds, us = {"DEPTH": 2.5, "AREA": 0.828}, {"DEPTH": 2.0, "AREA": 0.703}
    if location == "Both Sides":
        row["CURTAIN_COUNT"], row["L_CURTAIN_TOTAL"], row["CURTAIN_DEPTH"], row["CURTAIN_AREA_TOTAL"] = 2, l_base * 2, 2.25, (ds["AREA"]+us["AREA"]) * l_base
    else:
        p = ds if location == "D/S Only" else us
        row["CURTAIN_COUNT"], row["L_CURTAIN_TOTAL"], row["CURTAIN_DEPTH"], row["CURTAIN_AREA_TOTAL"] = 1, l_base, p["DEPTH"], p["AREA"] * l_base
    row["CURTAIN_WIDTH"] = 0.7
    return row

def calculate_apron_geometry(row):
    if "U-Trough" in row["PROT_SELECTION"]:
        row["APRON_PLAN_AREA"] = 0
    else:
        box_iw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
        l_base = row["L_CURTAIN_TOTAL"] / row["CURTAIN_COUNT"] if row["CURTAIN_COUNT"] > 0 else box_iw
        area_single = ((box_iw + l_base) / 2) * row["PROT_LEN"]
        row["APRON_PLAN_AREA"] = area_single * row["CURTAIN_COUNT"]
    return row

def calculate_master_quantities(row):
    n, off, sel = row["NO_OF_CULVERTS"], 1.0, row["PROT_SELECTION"]
    # Separate Excavation Items
    row["EXC_BOX"] = ((row["TOTAL_LENGTH"] + off) * (row["BARREL_LENGTH"] + off) * (row["THICK_BOTTOM_SLAB"] + 0.15)) * n
    pw = row["PROT_AVG_WIDTH"] if "U-Trough" in sel else row.get("W", 0.0)
    pd = (row["T_BASE_SLAB"] + 0.15) if "U-Trough" in sel else 2.15
    row["EXC_PROT"] = ((pw + off) * (row["PROT_LEN"] + off) * pd) * row["PROT_COUNT"] * n
    row["EXC_RET"] = (3.1 * 2.5 * 2.15) * row["PROT_COUNT"] * n if "Wing Wall" in sel else 0
    row["EXC_TOE"] = (row["TOE_WALL_WIDTH"] + off) * row["TOE_WALL_DEPTH"] * row["L_TOE"] * row["TOE_WALL_COUNT"] * n
    row["EXC_CURT"] = (row["CURTAIN_WIDTH"] + off) * row["CURTAIN_DEPTH"] * (row["L_CURTAIN_TOTAL"]/row["CURTAIN_COUNT"] if row["CURTAIN_COUNT"]>0 else 0) * row["CURTAIN_COUNT"] * n
    
    # PCC & RCC Grades
    poff, tpcc = 0.3, 0.1
    row["PCC_TOT"] = (((row["TOTAL_LENGTH"]+poff)*(row["BARREL_LENGTH"]+poff)*tpcc) + ((pw+poff)*(row["PROT_LEN"]+poff)*tpcc)*row["PROT_COUNT"] + (2.05*1.80*tpcc)*(row["PROT_COUNT"] if "Wing Wall" in sel else 0) + (row["TOE_WALL_WIDTH"]+poff)*(row["L_TOE"]+poff)*tpcc*row["TOE_WALL_COUNT"] + (row["CURTAIN_WIDTH"]+poff)*(row["L_CURTAIN_TOTAL"]+poff*row["CURTAIN_COUNT"])*tpcc) * n
    
    hk = 1.2 - row["THICK_BOTTOM_SLAB"]
    row["RCC_BOX"] = (row["TOTAL_LENGTH"]*row["BARREL_LENGTH"]*(row["THICK_BOTTOM_SLAB"]+row["TOP_SLAB_THICKNESS"]) + (2*row["SIDE_WALL_THICKNESS"] + row["NO_OF_MID_WALLS"]*row["MID_WALL_THICKNESS"])*row["VERTICAL_CLEARANCE_OF_CULVERT"]*row["BARREL_LENGTH"] + (0.5*row["HAUNCH_SIZE"]**2*4*row["NO_OF_CELLS"]*row["BARREL_LENGTH"]) + ((row["TOTAL_LENGTH"]*0.7*hk)*2 if row["SHEAR_KEY_REQUIRED"]=="Yes" else 0)) * n
    
    if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"]:
        aftg = (row["A"]*(row["F"]+row["E"])/2) + (row["B"]*row["E"]) + (row["C"]*(row["E"]+row["G"])/2)
        row["RCC_PROT"] = ((aftg + ((row["B"]+row["D"])/2)*row["PROT_HT"]) * row["PROT_LEN"] * row["PROT_COUNT"] + (aftg + ((row["B"]+row["D"])/2)*1.0) * 1.5 * row["PROT_COUNT"] if "Wing Wall" in sel else 0) * n
    else:
        row["RCC_PROT"] = (pw*row["PROT_LEN"]*row["T_BASE_SLAB"] + 2*row["PROT_HT"]*row["PROT_LEN"]*row["SIDE_WALL_THICKNESS"]) * row["PROT_COUNT"] * n

    # Finishing Items
    row["RCC_M25_TOE"], row["RCC_M15_CURT"] = row["TOE_WALL_X_AREA"]*row["L_TOE"]*row["TOE_WALL_COUNT"]*n, row["CURTAIN_AREA_TOTAL"]*n
    row["STEEL_TOT"] = (row["RCC_BOX"] * row["PERCENT_STEEL_BOX"]) + (row["RCC_PROT"] * row["PERCENT_STEEL_PROT"])
    
    hbf = row["VERTICAL_CLEARANCE_OF_CULVERT"] + row["TOP_SLAB_THICKNESS"] + row["THICK_BOTTOM_SLAB"]
    row["BF_TOT"] = ((0.5*hbf**2*row["BARREL_LENGTH"]*2) + (0.5*row["PROT_HT"]**2*row["PROT_LEN"]*row["PROT_COUNT"]) + (0.5*1.0**2*1.5*row["PROT_COUNT"] if "Wing Wall" in sel else 0)) * n
    row["WC_TOT"] = (row["LENGTH_OF_CULVERT"]*row["NO_OF_CELLS"]*row["BARREL_LENGTH"]*0.15)*n
    row["RIGID"], row["LAUNCH"] = row["APRON_PLAN_AREA"]*0.3*n, row["APRON_PLAN_AREA"]*0.45*n
    
    if sel in ["Independent Retaining wall", "U-Trough Along Alignment"]:
        slant = np.sqrt(row["PROT_HT"]**2 + (row["PROT_HT"]*2)**2)
        row["PITCH"] = (np.pi*(row["PROT_HT"]*2)*slant/2)*4*0.3*n
    else: row["PITCH"] = 0
    
    def wh(h, l): return (np.floor((h-0.6)/1.0)+1) * (np.floor(l/1.0)+1) if h>0.6 else 0
    row["WEEP"] = (wh(row["VERTICAL_CLEARANCE_OF_CULVERT"], row["BARREL_LENGTH"])*2 + wh(row["PROT_HT"], row["PROT_LEN"])*row["PROT_COUNT"]) * n
    return row

# --- 3. UI SECTION ---
st.set_page_config(page_title="Culvert Master", layout="wide")
st.title("🏗️ Bridge Culvert BOQ Master Engine")

with st.sidebar:
    st.header("📋 Configuration")
    n_culv = st.number_input("Number of Culverts", value=1, min_value=1, key="k1")
    side_sel = st.selectbox("Side Selection", ["Both Sides", "One Side"], key="k2")
    prot_sel = st.selectbox("Protection Type", ["Independent Retaining wall", "Wing Wall + Return Wall", "U-Trough Wing Wall", "U-Trough Along Alignment"], key="k3")
    curt_loc = st.selectbox("Curtain Wall Location", ["Both Sides", "U/S Only", "D/S Only"], key="k4")
    sk_req = st.radio("Shear Key Required?", ["Yes", "No"], key="k5")

c1, c2, c3 = st.columns(3)
with c1:
    rw, frl, gl = st.number_input("TCS Width (m)", value=7.0, key="k6"), st.number_input("FRL (m)", value=5.0, key="k7"), st.number_input("GL (m)", value=2.0, key="k8")
    sl, sr = st.selectbox("Slopes", [0, 1, 2], index=2, key="k9"), st.number_input("Ratio", value=1.5, key="k10")
with c2:
    cl, ln, vc = st.number_input("Cells", value=1, key="k11"), st.number_input("Span L", value=2.0, key="k12"), st.number_input("Height VC", value=2.0, key="k13")
    hz = st.number_input("Haunch", value=0.15, key="k14")
with c3:
    tt, tb, ts = st.number_input("Top Slab", value=0.25, key="k15"), st.number_input("Bottom Slab", value=0.25, key="k16"), st.number_input("Side Wall", value=0.25, key="k17")
    tm = st.number_input("Mid Wall", value=0.25 if cl > 1 else 0.0, key="k18")
    sbx, spr = st.number_input("Steel Box", value=85.0, key="k19"), st.number_input("Steel Prot", value=50.0, key="k20")

if st.button("🚀 Generate Final BOQ", key="k_btn"):
    data = {"NO_OF_CULVERTS": n_culv, "SIDE_SELECTION": side_sel, "PROT_SELECTION": prot_sel, "CURTAIN_WALL_LOCATION": curt_loc, "SHEAR_KEY_REQUIRED": sk_req, "WIDTH_AS_PER_TCS": rw, "FRL": frl, "GROUND_LEVEL": gl, "SLOPE_COUNT": sl, "SIDE_SLOPE_RATIO": sr, "NO_OF_CELLS": cl, "LENGTH_OF_CULVERT": ln, "VERTICAL_CLEARANCE_OF_CULVERT": vc, "HAUNCH_SIZE": hz, "TOP_SLAB_THICKNESS": tt, "THICK_BOTTOM_SLAB": tb, "SIDE_WALL_THICKNESS": ts, "MID_WALL_THICKNESS": tm, "PERCENT_STEEL_BOX": sbx, "PERCENT_STEEL_PROT": spr}
    
    res = calculate_box_geometry(data)
    res = calculate_protection_dimensions(res)
    res = assign_protection_sections(res)
    res = calculate_toe_wall_geometry(res)
    res = calculate_curtain_wall_geometry(res)
    res = calculate_apron_geometry(res)
    res = calculate_master_quantities(res)

    st.success("✅ BOQ Generated.")
    final_data = [
        ["Excavation: Box", f"{res['EXC_BOX']:.2f}", "m3", "1.0m offset paylines"],
        ["Excavation: Protection", f"{res['EXC_PROT']:.2f}", "m3", "Base + offsets"],
        ["Excavation: Return", f"{res['EXC_RET']:.2f}", "m3", "3.1x2.5 footprint"],
        ["Excavation: Toe/Curtain", f"{res['EXC_TOE']+res['EXC_CURT']:.2f}", "m3", "Structure footprint"],
        ["**TOTAL EXCAVATION**", f"{res['EXC_BOX']+res['EXC_PROT']+res['EXC_RET']+res['EXC_TOE']+res['EXC_CURT']:.2f}", "m3", "Grand total earthwork"],
        ["PCC M15 (Grand Total)", f"{res['PCC_TOT']:.2f}", "m3", "100mm thk + 300mm offset"],
        ["RCC M35 (Box Structure)", f"{res['RCC_BOX']:.2f}", "m3", "Slabs+Side+Mid+Haunch+Keys"],
        ["RCC M35 (Prot + Return)", f"{res['RCC_PROT']:.2f}", "m3", "Main and return stems"],
        ["RCC M25 (Toe Walls)", f"{res['RCC_M25_TOE']:.2f}", "m3", "0.370 area logic"],
        ["RCC M15 (Curtain Walls)", f"{res['RCC_M15_CURT']:.2f}", "m3", "0.7m width logic"],
        ["Total Steel Reinforcement", f"{res['STEEL_TOT']:.2f}", "kg", "Concrete * Steel Ratios"],
        ["Total Backfill (1:1)", f"{res['BF_TOT']:.2f}", "m3", "0.5*H^2*L Rule"],
        ["Wearing Course", f"{res['WC_TOT']:.2f}", "m3", "150mm internal PCC"],
        ["Rigid Apron", f"{res['RIGID']:.2f}", "m3", "300mm floor protection"],
        ["Launching Apron", f"{res['LAUNCH']:.2f}", "m3", "450mm scour protection"],
        ["Quadrant Pitching", f"{res['PITCH']:.2f}", "m3", "Quadrant area * 0.3"],
        ["Weep Holes (100mm)", f"{res['WEEP']:.0f}", "Nos", "1m c/c spacing"]
    ]
    st.table(pd.DataFrame(final_data, columns=["Description", "Quantity", "Unit", "Logic Explanation"]))

    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 14); pdf.cell(190, 10, "BRIDGE CULVERT BOQ REPORT", ln=True, align='C')
    pdf.set_font("Arial", size=9)
    for r in final_data:
        pdf.cell(80, 8, r[0].replace("**",""), 1); pdf.cell(30, 8, r[1], 1, 0, 'C'); pdf.cell(20, 8, r[2], 1, 0, 'C'); pdf.cell(60, 8, r[3], 1); pdf.ln()
    pdf_out = pdf.output(dest='S').encode('latin-1')
    st.download_button("📥 Download PDF Report", data=pdf_out, file_name="Culvert_BOQ.pdf", mime="application/pdf", key="pdf_dl")
