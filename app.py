import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF

# --- 1. THE LOOKUP TABLE ---
lookup_data = {
    'H': [1,2,3,4,5,6,7,8,9,10],
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
    
    # # Explained: Logic for wall Height and Length
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
        # # Mid-Wall used here for inner width 'bw'
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
        # W (Footing Width) is pulled from table here
        for p in ['W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = match[p]
    else:
        # # Explained: Fixing U-Trough Footing Width (W) for Excavation
        # For U-trough, we use Wall Thickness + 0.3m offset as a default for W
        row["W"] = row["SIDE_WALL_THICKNESS"] + 0.3 
        row["T_BASE_SLAB"] = 0.25 if row["PROT_HT"] <= 2 else 0.30 if row["PROT_HT"] <= 3 else 0.40
    return row

def calculate_master_quantities(row):
    n, BL, OW, VC, TS, BS = row["NO_OF_CULVERTS"], row["BARREL_LENGTH"], row["OUTER_WIDTH"], row["VERTICAL_CLEARANCE_OF_CULVERT"], row["TOP_SLAB_THICKNESS"], row["THICK_BOTTOM_SLAB"]
    mw_count = row["NO_OF_CELLS"] - 1
    
    # # ITEM 1: EXCAVATION (Includes Mid-Wall OW)
    row["TOTAL_EXCAVATION"] = (((OW+1)*(BL+1)*(BS+0.15)) + ((row.get("W", 0)+1)*(row["PROT_LEN"]+1)*2.15)*row["PROT_COUNT"]) * n
    
    # # ITEM 2: RCC BOX (Includes Mid-Wall Volume)
    hk = 1.2 - BS
    row["QTY_SHEAR_KEY"] = ((OW*0.25*hk) + (OW*0.5*0.45*hk)) * 2 * n if row["SHEAR_KEY_REQUIRED"] == "Yes" else 0
    # Added (mw_count * MidWall) logic back here:
    row["TOTAL_RCC_BOX_M35"] = (OW*BL*(TS+BS)*n) + ((2*row["SIDE_WALL_THICKNESS"] + mw_count*row["MID_WALL_THICKNESS"])*VC*BL*n) + (0.5*row["HAUNCH_SIZE"]**2*4*row["NO_OF_CELLS"]*BL*n) + row["QTY_SHEAR_KEY"]
    
    # # ITEM 3: PROTECTION RCC
    if row["PROT_SELECTION"] in ["Independent Retaining wall", "Wing Wall + Return Wall"]:
        area_f = (row["A"]*(row["F"]+row["E"])/2) + (row["B"]*row["E"]) + (row["C"]*(row["E"]+row["G"])/2)
        area_s = ((row["B"]+row["D"])/2)*row["PROT_HT"]
        row["TOTAL_M35_PROTECTION"] = (area_f + area_s) * row["PROT_LEN"] * row["PROT_COUNT"] * n
    else:
        # U-Trough logic
        row["TOTAL_M35_PROTECTION"] = (row.get("PROT_AVG_WIDTH", OW)*row["PROT_LEN"]*row["T_BASE_SLAB"] + 2*row["PROT_HT"]*row["PROT_LEN"]*row["SIDE_WALL_THICKNESS"]) * row["PROT_COUNT"] * n
    
    row["TOTAL_STEEL_KG"] = (row["TOTAL_RCC_BOX_M35"]*row["PERCENT_STEEL_BOX"]) + (row["TOTAL_M35_PROTECTION"]*row["PERCENT_STEEL_PROT"])
    
    # Backfill and Filter Media
    h_f = VC+TS+BS
    row["TOTAL_BACKFILL"] = ((0.5*h_f**2*BL)*2*n) + ((0.5*row["PROT_HT"]**2*row["PROT_LEN"])*row["PROT_COUNT"]*n)
    row["TOTAL_FILTER_MEDIA"] = (h_f*0.6*BL*2*n) + (row["PROT_HT"]*0.6*row["PROT_LEN"]*row["PROT_COUNT"]*n)
    
    return row

# --- 3. STREAMLIT INTERFACE ---
st.set_page_config(page_title="Culvert Master", layout="wide")
st.title("🏗️ Bridge Culvert BOQ Master")

with st.sidebar:
    n_culv = st.number_input("Number of Culverts", min_value=1, value=1)
    side_sel = st.selectbox("Side Selection", ["Both Sides", "One Side"])
    prot_sel = st.selectbox("Protection Type", ["Independent Retaining wall", "Wing Wall + Return Wall", "U-Trough Wing Wall", "U-Trough Along Alignment"])
    sk_req = st.radio("Shear Key Required?", ["Yes", "No"])

col1, col2, col3 = st.columns(3)
with col1:
    road_w, frl, invert = st.number_input("TCS (m)", value=7.0), st.number_input("FRL (m)", value=5.0), st.number_input("IL (m)", value=2.0)
    slopes, slope_r = st.selectbox("Slopes", [0, 1, 2], index=2), st.number_input("Ratio", value=1.5)
with col2:
    cells = st.number_input("Cells", min_value=1, value=1)
    L = st.number_input("Span L", value=2.0)
    VC = st.number_input("VC", value=2.0)
    h_size = st.number_input("Haunch", value=0.15)
with col3:
    t_top, t_bot, t_side = st.number_input("Top Slab", value=0.25), st.number_input("Bottom Slab", value=0.25), st.number_input("Wall", value=0.25)
    t_mid = st.number_input("Mid Wall", value=0.25) if cells > 1 else 0.0
    st_box, st_prot = st.number_input("Steel Box", value=85.0), st.number_input("Steel Prot", value=85.0)

if st.button("🚀 Calculate Final BOQ"):
    row = {
        "NO_OF_CULVERTS": n_culv, "SIDE_SELECTION": side_sel, "PROT_SELECTION": prot_sel,
        "SHEAR_KEY_REQUIRED": sk_req, "WIDTH_AS_PER_TCS": road_w, 
        "FRL": frl, "INVERT_LEVEL": invert, "SLOPE_COUNT": slopes, "SIDE_SLOPE_RATIO": slope_r,
        "NO_OF_CELLS": cells, "LENGTH_OF_CULVERT": L, "VERTICAL_CLEARANCE_OF_CULVERT": VC, 
        "HAUNCH_SIZE": h_size, "TOP_SLAB_THICKNESS": t_top, "THICK_BOTTOM_SLAB": t_bot,
        "SIDE_WALL_THICKNESS": t_side, "MID_WALL_THICKNESS": t_mid, 
        "PERCENT_STEEL_BOX": st_box, "PERCENT_STEEL_PROT": st_prot
    }
    
    # # Explained: Mid-Wall logic included in Outer Width calculation
    row["OUTER_WIDTH"] = (cells * L) + (2 * t_side) + ((cells - 1) * t_mid)
    cushion = frl - (invert + VC + t_top)
    row["BARREL_LENGTH"] = road_w + (slopes * slope_r * cushion)

    row = calculate_geometry_pipeline(row); row = assign_protection_sections(row)
    # Protection Excavation Logic (calculate_scour_geometry is replaced by master_quantities for brevity)
    row = calculate_master_quantities(row)

    st.success("✅ BOQ Generated.")
    results = [
        ["Barrel Length", f"{row['BARREL_LENGTH']:.3f}", "m", "Includes slopes"],
        ["Total Excavation", f"{row['TOTAL_EXCAVATION']:.2f}", "m3", "Includes Box & Prot footing"],
        ["RCC M35 Box", f"{row['TOTAL_RCC_BOX_M35']:.2f}", "m3", "Slabs+SideWalls+MidWalls+Haunches"],
        ["RCC M35 Protection", f"{row['TOTAL_M35_PROTECTION']:.2f}", "m3", "Wing/Return walls"],
        ["Total Steel", f"{row['TOTAL_STEEL_KG']:.2f}", "kg", "Box + Prot steel reinforcement"]
    ]
    df_boq = pd.DataFrame(results, columns=["Description", "Quantity", "Unit", "Logic Audit"])
    st.markdown("""<style> table { font-size: 11px !important; } th { background-color: #2e7d32 !important; color: white !important; } </style>""", unsafe_allow_html=True)
    st.table(df_boq)
