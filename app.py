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

# --- 2. THE BLOCKS (Exactly as provided) ---

def calculate_box_geometry(row):
    row["NO_OF_MID_WALLS"] = row["NO_OF_CELLS"] - 1 if row["NO_OF_CELLS"] > 1 else 0
    row["TOTAL_LENGTH"] = (
        (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) +
        (2 * row["SIDE_WALL_THICKNESS"]) +
        (row["NO_OF_MID_WALLS"] * row["MID_WALL_THICKNESS"])
    )
    row["CUSHION"] = (
        row["FRL"] - row["GROUND_LEVEL"] -
        row["VERTICAL_CLEARANCE_OF_CULVERT"] - row["TOP_SLAB_THICKNESS"]
    )
    row["BARREL_LENGTH"] = row["WIDTH_AS_PER_TCS"] + (row["SLOPE_COUNT"] * row["SIDE_SLOPE_RATIO"] * row["CUSHION"])
    return row

def calculate_protection_dimensions(row):
    box_inner_ht = row["VERTICAL_CLEARANCE_OF_CULVERT"] + row["TOP_SLAB_THICKNESS"]
    is_both = row["SIDE_SELECTION"] == "Both Sides"
    selection = row["PROT_SELECTION"]

    if selection == "Independent Retaining wall":
        row["PROT_COUNT"] = 4 if is_both else 2
        row["PROT_HT"] = box_inner_ht
        row["PROT_LEN"] = (1.5 * row["PROT_HT"]) - row["SIDE_WALL_THICKNESS"]
    elif selection == "Wing Wall + Return Wall":
        row["PROT_COUNT"] = 4 if is_both else 2
        row["PROT_HT"] = (box_inner_ht + 1.0) / 2
        row["PROT_LEN"] = (2 * (box_inner_ht - 1.0)) / np.cos(np.radians(45))
    elif selection == "U-Trough Wing Wall":
        row["PROT_COUNT"] = 2 if is_both else 1
        row["PROT_HT"] = (box_inner_ht + 1.0) / 2
        row["PROT_LEN"] = (2 * (box_inner_ht - 1.0)) / np.cos(np.radians(30))
        start_w = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
        end_w = start_w + (row["PROT_LEN"] * 2 * np.sin(np.radians(45)))
        row["PROT_AVG_WIDTH"] = (start_w + end_w) / 2
    elif selection == "U-Trough Along Alignment":
        row["PROT_COUNT"] = 2 if is_both else 1
        row["PROT_HT"] = box_inner_ht
        row["PROT_LEN"] = (2 * row["PROT_HT"]) - row["SIDE_WALL_THICKNESS"]
        row["PROT_WIDTH"] = row["BARREL_LENGTH"]
    return row

def assign_protection_sections(row):
    h_val = row["PROT_HT"]
    selection = row["PROT_SELECTION"]
    if selection in ["Wing Wall + Return Wall", "Independent Retaining wall"]:
        h_idx = max(1, min(10, int(round(h_val))))
        match = df_lookup[df_lookup['H'] == h_idx].iloc[0]
        for param in ['H1', 'W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']:
            row[param] = match[param]
    elif selection in ["U-Trough Wing Wall", "U-Trough Along Alignment"]:
        row["T_WALL_TOP"] = 0.20
        if h_val <= 2: row["T_WALL_BASE"] = 0.25
        elif h_val <= 3: row["T_WALL_BASE"] = 0.30
        elif h_val <= 4: row["T_WALL_BASE"] = 0.35
        else: row["T_WALL_BASE"] = 0.40
        row["T_BASE_SLAB"] = row["T_WALL_BASE"]
    return row

def calculate_toe_wall_geometry(row):
    selection = row["PROT_SELECTION"]
    h_prot = row["PROT_HT"]
    row["TOE_WALL_COUNT"] = row["PROT_COUNT"] if selection in ["Independent Retaining wall", "Wing Wall + Return Wall"] else 0
    if selection == "Wing Wall + Return Wall":
        row["L_TOE"] = 2 * np.pi * 2 * 0.25
    elif selection == "Independent Retaining wall":
        row["L_TOE"] = (2 * np.pi * np.sqrt(((h_prot * 2)**2 + (1.5 * h_prot)**2) / 2)) / 4
    elif selection == "U-Trough Along Alignment":
        row["L_TOE"] = (h_prot * 2 * np.pi * 2) / 4
    else: row["L_TOE"] = 0
    
    if row["L_TOE"] > 0:
        row["TOE_WALL_WIDTH"], row["TOE_WALL_X_AREA"], row["TOE_WALL_DEPTH"] = 0.6, 0.370, 1.05
    else:
        row["TOE_WALL_WIDTH"], row["TOE_WALL_X_AREA"], row["TOE_WALL_DEPTH"] = 0, 0, 0
    return row

def calculate_curtain_wall_geometry(row):
    selection, location = row["PROT_SELECTION"], row["CURTAIN_WALL_LOCATION"]
    box_iw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
    if selection in ["U-Trough Wing Wall", "Wing Wall + Return Wall"]:
        l_base = box_iw + (row["PROT_LEN"] * 2 * np.sin(np.radians(45)))
    else: l_base = (row["PROT_LEN"] * 2) + box_iw
    
    ds = {"DEPTH": 2.500, "AREA": 0.828, "WIDTH": 0.700, "THK": 0.250}
    us = {"DEPTH": 2.000, "AREA": 0.703, "WIDTH": 0.700, "THK": 0.250}
    
    if location == "Both Sides":
        row["CURTAIN_COUNT"], row["L_CURTAIN_TOTAL"] = 2, l_base * 2
        row["CURTAIN_AREA_TOTAL"] = (ds["AREA"] + us["AREA"]) * l_base
        row["CURTAIN_DEPTH"] = 2.25 # Average for display
    elif location == "D/S Only":
        row["CURTAIN_COUNT"], row["L_CURTAIN_TOTAL"] = 1, l_base
        row["CURTAIN_DEPTH"], row["CURTAIN_X_AREA"] = ds["DEPTH"], ds["AREA"]
    elif location == "U/S Only":
        row["CURTAIN_COUNT"], row["L_CURTAIN_TOTAL"] = 1, l_base
        row["CURTAIN_DEPTH"], row["CURTAIN_X_AREA"] = us["DEPTH"], us["AREA"]
    row["CURTAIN_WIDTH"] = 0.700
    return row

def calculate_apron_geometry(row):
    selection, location = row["PROT_SELECTION"], row["CURTAIN_WALL_LOCATION"]
    if selection in ["U-Trough Wing Wall", "U-Trough Along Alignment"]:
        row["APRON_COUNT"], row["APRON_PLAN_AREA"] = 0, 0
        return row
    w_start = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
    w_end = row["L_CURTAIN_TOTAL"] / row["CURTAIN_COUNT"] if row["CURTAIN_COUNT"] > 0 else w_start
    area_single = ((w_start + w_end) / 2) * row["PROT_LEN"]
    row["APRON_COUNT"] = 2 if location == "Both Sides" else 1 if location in ["U/S Only", "D/S Only"] else 0
    row["APRON_PLAN_AREA"] = area_single * row["APRON_COUNT"]
    return row

def calculate_filter_media_geometry(row):
    T_FM = 0.60
    row["FM_BOX_HEIGHT"] = row["VERTICAL_CLEARANCE_OF_CULVERT"] + row["TOP_SLAB_THICKNESS"]
    row["FM_BOX_WIDTH"], row["FM_BOX_LENGTH"], row["FM_BOX_SIDE_COUNT"] = T_FM, row["BARREL_LENGTH"], 2
    row["FM_PROT_HEIGHT"], row["FM_PROT_WIDTH"], row["FM_PROT_LENGTH"] = row["PROT_HT"], T_FM, row["PROT_LEN"]
    row["FM_PROT_COUNT"] = row["PROT_COUNT"]
    return row

def calculate_master_quantities(row):
    n, offset, sel = row["NO_OF_CULVERTS"], 1.0, row["PROT_SELECTION"]
    # Excavation
    row["QTY_EXC_BOX"] = ((row["TOTAL_LENGTH"] + offset) * (row["BARREL_LENGTH"] + offset) * (row["THICK_BOTTOM_SLAB"] + 0.150)) * n
    if sel == "U-Trough Along Alignment": p_w, p_d = row["BARREL_LENGTH"], row["T_BASE_SLAB"] + 0.150
    elif sel == "U-Trough Wing Wall": p_w, p_d = row["PROT_AVG_WIDTH"], row["T_BASE_SLAB"] + 0.150
    else: p_w, p_d = row.get("W", 0.0), 2.15
    row["QTY_EXC_PROT"] = ((p_w + offset) * (row["PROT_LEN"] + offset) * p_d) * row["PROT_COUNT"] * n
    row["QTY_EXC_RETURN"] = (3.1 * 2.5 * 2.15) * row["PROT_COUNT"] * n if "Wing Wall" in sel else 0
    row["QTY_EXC_TOE"] = (row["TOE_WALL_WIDTH"] + offset) * row["TOE_WALL_DEPTH"] * row["L_TOE"] * row["TOE_WALL_COUNT"] * n
    row["QTY_EXC_CURTAIN"] = (row["CURTAIN_WIDTH"] + offset) * row["CURTAIN_DEPTH"] * (row["L_CURTAIN_TOTAL"]/row["CURTAIN_COUNT"] if row["CURTAIN_COUNT"]>0 else 0) * row["CURTAIN_COUNT"] * n
    row["TOTAL_EXCAVATION"] = row["QTY_EXC_BOX"] + row["QTY_EXC_PROT"] + row["QTY_EXC_RETURN"] + row["QTY_EXC_TOE"] + row["QTY_EXC_CURTAIN"]

    # PCC
    poff, tpcc = 0.3, 0.1
    row["QTY_PCC_BOX"] = ((row["TOTAL_LENGTH"]+poff)*(row["BARREL_LENGTH"]+poff)*tpcc)*n
    row["QTY_PCC_PROT"] = ((p_w+poff)*(row["PROT_LEN"]+poff)*tpcc)*row["PROT_COUNT"]*n
    row["QTY_PCC_RET"] = (2.05*1.80*tpcc)*row["PROT_COUNT"]*n if "Wing Wall" in sel else 0
    row["QTY_PCC_TOE"] = (row["TOE_WALL_WIDTH"]+poff)*(row["L_TOE"]+poff)*tpcc*row["TOE_WALL_COUNT"]*n
    row["QTY_PCC_CURT"] = (row["CURTAIN_WIDTH"]+poff)*( (row["L_CURTAIN_TOTAL"]/row["CURTAIN_COUNT"] if row["CURTAIN_COUNT"]>0 else 0)+poff)*tpcc*row["CURTAIN_COUNT"]*n
    row["TOTAL_PCC"] = row["QTY_PCC_BOX"] + row["QTY_PCC_PROT"] + row["QTY_PCC_RET"] + row["QTY_PCC_TOE"] + row["QTY_PCC_CURT"]

    # RCC Box
    hk = 1.2 - row["THICK_BOTTOM_SLAB"]
    v_slab = row["TOTAL_LENGTH"] * row["BARREL_LENGTH"] * (row["THICK_BOTTOM_SLAB"] + row["TOP_SLAB_THICKNESS"])
    v_wall = (2*row["SIDE_WALL_THICKNESS"] + row["NO_OF_MID_WALLS"]*row["MID_WALL_THICKNESS"]) * row["VERTICAL_CLEARANCE_OF_CULVERT"] * row["BARREL_LENGTH"]
    v_haunch = (0.5 * row["HAUNCH_SIZE"]**2 * 4 * row["NO_OF_CELLS"] * row["BARREL_LENGTH"])
    v_key = (row["TOTAL_LENGTH"] * 0.25 * hk + row["TOTAL_LENGTH"] * 0.5 * 0.45 * hk) * 2 if row["SHEAR_KEY_REQUIRED"] == "Yes" else 0
    row["TOTAL_RCC_BOX"] = (v_slab + v_wall + v_haunch + v_key) * n

    # RCC Prot
    area_f = (row["A"]*(row["F"]+row["E"])/2) + (row["B"]*row["E"]) + (row["C"]*(row["E"]+row["G"])/2)
    if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"]:
        v_p = (area_f + ((row["B"]+row["D"])/2)*row["PROT_HT"]) * row["PROT_LEN"] * row["PROT_COUNT"]
        v_r = (area_f + ((row["B"]+row["D"])/2)*1.0) * 1.5 * row["PROT_COUNT"] if "Wing Wall" in sel else 0
        row["TOTAL_RCC_PROT"] = (v_p + v_r) * n
    else:
        sw = row["PROT_AVG_WIDTH"] if sel == "U-Trough Wing Wall" else row["BARREL_LENGTH"]
        row["TOTAL_RCC_PROT"] = (sw * row["PROT_LEN"] * row["T_BASE_SLAB"] + 2 * row["PROT_HT"] * row["PROT_LEN"] * row["SIDE_WALL_THICKNESS"]) * row["PROT_COUNT"] * n

    # Others
    row["TOTAL_M15_CURT"] = row["CURTAIN_AREA_TOTAL"] * n
    row["TOTAL_M25_TOE"] = row["TOE_WALL_X_AREA"] * row["L_TOE"] * row["TOE_WALL_COUNT"] * n
    row["TOTAL_STEEL"] = (row["TOTAL_RCC_BOX"] * row["PERCENT_STEEL_BOX"]) + (row["TOTAL_RCC_PROT"] * row["PERCENT_STEEL_PROT"])
    
    h_bf_box = row["VERTICAL_CLEARANCE_OF_CULVERT"] + row["TOP_SLAB_THICKNESS"] + row["THICK_BOTTOM_SLAB"]
    row["TOTAL_BF"] = ((0.5*h_bf_box**2*row["BARREL_LENGTH"]*2) + (0.5*row["PROT_HT"]**2*row["PROT_LEN"]*row["PROT_COUNT"]) + (0.5*1.0**2*1.5*row["PROT_COUNT"] if "Wing Wall" in sel else 0)) * n
    row["TOTAL_FM"] = ((h_bf_box*0.6*row["BARREL_LENGTH"]*2) + (row["PROT_HT"]*0.6*row["PROT_LEN"]*row["PROT_COUNT"]) + (1.0*0.6*1.5*row["PROT_COUNT"] if "Wing Wall" in sel else 0)) * n
    
    row["QTY_WC"] = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"] * row["BARREL_LENGTH"] * 0.15) * n
    row["QTY_RIGID"] = row["APRON_PLAN_AREA"] * 0.3 * n
    row["QTY_LAUNCH"] = row["APRON_PLAN_AREA"] * 0.45 * n
    
    if sel in ["Independent Retaining wall", "U-Trough Along Alignment"]:
        slant = np.sqrt(row["PROT_HT"]**2 + (row["PROT_HT"]*2)**2)
        row["QTY_PITCH"] = (np.pi * (row["PROT_HT"]*2) * slant / 2) * 4 * 0.3 * n
        row["QTY_PITCH_FM"] = row["QTY_PITCH"]
    else: row["QTY_PITCH"] = row["QTY_PITCH_FM"] = 0
    
    def wh(h, l): return (np.floor((h-0.6)/1.0)+1) * (np.floor(l/1.0)+1) if h>0.6 else 0
    row["WEEP_NOS"] = (wh(row["VERTICAL_CLEARANCE_OF_CULVERT"], row["BARREL_LENGTH"])*2 + wh(row["PROT_HT"], row["PROT_LEN"])*row["PROT_COUNT"]) * n
    return row

# --- 3. STREAMLIT UI ---
st.set_page_config(page_title="Bridge Culvert BOQ", layout="wide")
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
    st.subheader("📍 Levels")
    road_w = st.number_input("Road Width TCS (m)", value=7.0, key="r_w")
    frl = st.number_input("FRL (m)", value=5.0, key="frl")
    gl = st.number_input("Ground Level (m)", value=2.0, key="gl")
    slopes = st.selectbox("Slope Count", [0, 1, 2], index=2, key="sl")
    slope_r = st.number_input("Slope Ratio", value=1.5, key="sr")
with c2:
    st.subheader("📦 Box Specs")
    cells = st.number_input("Cells", value=1, key="cl")
    L = st.number_input("Span L", value=2.0, key="ln")
    VC = st.number_input("VC", value=2.0, key="vc")
    h_dim = st.number_input("Haunch (m)", value=0.15, key="hz")
with c3:
    st.subheader("🧱 Concrete/Steel")
    t_top = st.number_input("Top Slab", value=0.25, key="tt")
    t_bot = st.number_input("Bottom Slab", value=0.25, key="tb")
    t_side = st.number_input("Outer Wall", value=0.25, key="ts")
    t_mid = st.number_input("Mid Wall", value=0.25 if cells > 1 else 0.0, key="tm")
    st_box = st.number_input("Steel Box (kg/m3)", value=85.0, key="sbx")
    st_prot = st.number_input("Steel Prot (kg/m3)", value=50.0, key="spr")

if st.button("🚀 Calculate Final BOQ", key="main_btn"):
    inputs = {
        "NO_OF_CULVERTS": n_culv, "SIDE_SELECTION": side_sel, "PROT_SELECTION": prot_sel,
        "CURTAIN_WALL_LOCATION": curt_loc, "SHEAR_KEY_REQUIRED": sk_req, "WIDTH_AS_PER_TCS": road_w,
        "FRL": frl, "GROUND_LEVEL": gl, "SLOPE_COUNT": slopes, "SIDE_SLOPE_RATIO": slope_r,
        "NO_OF_CELLS": cells, "LENGTH_OF_CULVERT": L, "VERTICAL_CLEARANCE_OF_CULVERT": VC,
        "HAUNCH_SIZE": h_dim, "TOP_SLAB_THICKNESS": t_top, "THICK_BOTTOM_SLAB": t_bot,
        "SIDE_WALL_THICKNESS": t_side, "MID_WALL_THICKNESS": t_mid, "PERCENT_STEEL_BOX": st_box, "PERCENT_STEEL_PROT": st_prot
    }
    
    # Run Blocks in Order
    res = calculate_box_geometry(inputs)
    res = calculate_protection_dimensions(res)
    res = assign_protection_sections(res)
    res = calculate_toe_wall_geometry(res)
    res = calculate_curtain_wall_geometry(res)
    res = calculate_apron_geometry(res)
    res = calculate_filter_media_geometry(res)
    res = calculate_master_quantities(res)

    st.success("✅ Success! All quantities calculated.")

    # Individual Categories for Audit
    res_list = [
        ["Excavation: Box Structure", f"{res['QTY_EXC_BOX']:.2f}", "m3"],
        ["Excavation: Protection Walls", f"{res['QTY_EXC_PROT']:.2f}", "m3"],
        ["Excavation: Return Walls", f"{res['QTY_EXC_RETURN']:.2f}", "m3"],
        ["Excavation: Toe Wall", f"{res['QTY_EXC_TOE']:.2f}", "m3"],
        ["Excavation: Curtain Wall", f"{res['QTY_EXC_CURTAIN']:.2f}", "m3"],
        ["**Total Excavation**", f"{res['TOTAL_EXCAVATION']:.2f}", "m3"],
        ["---", "---", "---"],
        ["PCC M15 (Grand Total)", f"{res['TOTAL_PCC']:.2f}", "m3"],
        ["RCC M35 (Box Structure)", f"{res['TOTAL_RCC_BOX']:.2f}", "m3"],
        ["RCC M35 (Prot + Return)", f"{res['TOTAL_RCC_PROT']:.2f}", "m3"],
        ["RCC M25 (Toe Walls)", f"{res['TOTAL_M25_TOE']:.2f}", "m3"],
        ["RCC M15 (Curtain Walls)", f"{res['TOTAL_M15_CURT']:.2f}", "m3"],
        ["---", "---", "---"],
        ["Steel: Box", f"{res['TOTAL_RCC_BOX']*res['PERCENT_STEEL_BOX']:.2f}", "kg"],
        ["Steel: Protection", f"{res['TOTAL_RCC_PROT']*res['PERCENT_STEEL_PROT']:.2f}", "kg"],
        ["**Grand Total Steel**", f"{res['TOTAL_STEEL']:.2f}", "kg"],
        ["---", "---", "---"],
        ["Total Backfill (1:1)", f"{res['TOTAL_BF']:.2f}", "m3"],
        ["Total Filter Media", f"{res['TOTAL_FM']:.2f}", "m3"],
        ["Wearing Course", f"{res['QTY_WC']:.2f}", "m3"],
        ["Rigid Apron", f"{res['QTY_RIGID']:.2f}", "m3"],
        ["Launching Apron", f"{res['QTY_LAUNCH']:.2f}", "m3"],
        ["Quadrant Pitching", f"{res['QTY_PITCH']:.2f}", "m3"],
        ["Pitching Filter Media", f"{res['QTY_PITCH_FM']:.2f}", "m3"],
        ["Weep Holes (100mm)", f"{res['WEEP_NOS']:.0f}", "Nos"]
    ]
    st.table(pd.DataFrame(res_list, columns=["Description", "Quantity", "Unit"]))
