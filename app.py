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

# --- 2. ENGINE BLOCKS ---

def calculate_full_boq(row):
    n = row["NO_OF_CULVERTS"]
    row["NO_OF_MID_WALLS"] = row["NO_OF_CELLS"] - 1 if row["NO_OF_CELLS"] > 1 else 0
    
    # 1. Box Geometry
    row["OUTER_WIDTH"] = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + \
                         (2 * row["SIDE_WALL_THICKNESS"]) + \
                         (row["NO_OF_MID_WALLS"] * row["MID_WALL_THICKNESS"])
    row["CUSHION"] = row["FRL"] - row["GROUND_LEVEL"] - row["VERTICAL_CLEARANCE_OF_CULVERT"] - row["TOP_SLAB_THICKNESS"]
    row["BARREL_LENGTH"] = row["WIDTH_AS_PER_TCS"] + (row["SLOPE_COUNT"] * row["SIDE_SLOPE_RATIO"] * row["CUSHION"])
    
    # 2. Protection Dimensions
    VC, TS, SW = row["VERTICAL_CLEARANCE_OF_CULVERT"], row["TOP_SLAB_THICKNESS"], row["SIDE_WALL_THICKNESS"]
    box_inner_ht = VC + TS
    sel = row["PROT_SELECTION"]
    is_both = row["SIDE_SELECTION"] == "Both Sides"
    
    if sel == "Independent Retaining wall":
        row["PROT_COUNT"], row["PROT_HT"] = (4 if is_both else 2), box_inner_ht
        row["PROT_LEN"] = (1.5 * row["PROT_HT"]) - SW
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
        row["PROT_LEN"] = (2 * row["PROT_HT"]) - SW
        row["PROT_AVG_WIDTH"] = row["BARREL_LENGTH"]

    # 3. Lookup or U-Trough Slab
    if sel in ["Wing Wall + Return Wall", "Independent Retaining wall"]:
        h_idx = max(1, min(10, int(round(row["PROT_HT"]))))
        match = df_lookup[df_lookup['H'] == h_idx].iloc[0]
        for p in ['W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = match[p]
        row["T_PROT_BASE_SLAB"] = 0
    else:
        row["T_PROT_BASE_SLAB"] = 0.25 if row["PROT_HT"] <= 2 else 0.30 if row["PROT_HT"] <= 3 else 0.40
        for p in ['W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = 0

    # 4. Scour/Toe/Curtain
    row["TOE_COUNT"] = row["PROT_COUNT"] if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"] else 0
    if sel == "Wing Wall + Return Wall": row["L_TOE"] = 2 * np.pi * 2 * 0.25
    elif sel == "Independent Retaining wall": row["L_TOE"] = (2 * np.pi * np.sqrt(((row["PROT_HT"]*2)**2 + (1.5*row["PROT_HT"])**2)/2))/4
    elif sel == "U-Trough Along Alignment": row["L_TOE"] = (row["PROT_HT"] * 2 * np.pi * 2) / 4
    else: row["L_TOE"] = 0
    row["TOE_AREA"], row["TOE_D"] = (0.370, 1.05) if row["L_TOE"] > 0 else (0,0)

    box_iw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
    l_base = box_iw + (row["PROT_LEN"] * 2 * np.sin(np.radians(45))) if "Wing" in sel else (row["PROT_LEN"] * 2) + box_iw
    ds_a, us_a, ds_d, us_d = 0.828, 0.703, 2.5, 2.0
    if row["CURTAIN_WALL_LOCATION"] == "Both Sides":
        row["CURT_COUNT"], row["CURT_A_T"], row["CURT_D"] = 2, (ds_a + us_a) * l_base, 2.25
    else:
        row["CURT_COUNT"], row["CURT_A_T"] = 1, (ds_a if "D/S" in row["CURTAIN_WALL_LOCATION"] else us_a) * l_base
        row["CURT_D"] = ds_d if "D/S" in row["CURTAIN_WALL_LOCATION"] else us_d

    row["APRON_PLAN"] = 0 if "U-Trough" in sel else ((box_iw + l_base) / 2) * row["PROT_LEN"] * row["CURT_COUNT"]

    # 5. Quantities (RCC)
    hk = 1.2 - row["THICK_BOTTOM_SLAB"]
    row["RCC_BOX"] = (row["OUTER_WIDTH"] * row["BARREL_LENGTH"] * (row["THICK_BOTTOM_SLAB"] + row["TOP_SLAB_THICKNESS"]) + 
                     (2*SW + row["NO_OF_MID_WALLS"]*row["MID_WALL_THICKNESS"])*VC*row["BARREL_LENGTH"] + 
                     (0.5 * row["HAUNCH_SIZE"]**2 * 4 * row["NO_OF_CELLS"] * row["BARREL_LENGTH"]) + 
                     ((row["OUTER_WIDTH"]*0.7*hk)*2 if row["SHEAR_KEY_REQUIRED"]=="Yes" else 0)) * n

    # FIXED PROTECTION RCC LOGIC
    if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"]:
        # area = footing + stem
        area_f = (row["A"]*(row["F"]+row["E"])/2) + (row["B"]*row["E"]) + (row["C"]*(row["E"]+row["G"])/2)
        area_s = ((row["B"] + row.get("D", 0.3))/2) * row["PROT_HT"]
        # Return wall uses fixed 1.5m length and 1.0m stem ht
        v_main = (area_f + area_s) * row["PROT_LEN"] * row["PROT_COUNT"]
        v_ret = (area_f + (((row["B"] + 0.3)/2) * 1.0)) * 1.5 * row["PROT_COUNT"] if "Wing Wall" in sel else 0
        row["RCC_PROT"] = (v_main + v_ret) * n
    else:
        pw = row["PROT_AVG_WIDTH"]
        row["RCC_PROT"] = (pw*row["PROT_LEN"]*row["T_PROT_BASE_SLAB"] + 2*row["PROT_HT"]*row["PROT_LEN"]*SW) * row["PROT_COUNT"] * n

    row["RCC_M25_TOE"] = row["TOE_AREA"] * row["L_TOE"] * row["TOE_COUNT"] * n
    row["RCC_M15_CURT"] = row["CURT_A_T"] * n

    # 6. Earthwork / Others
    off, poff, tpcc = 1.0, 0.3, 0.1
    row["EXC_BOX"] = ((row["OUTER_WIDTH"] + off) * (row["BARREL_LENGTH"] + off) * (row["THICK_BOTTOM_SLAB"] + 0.15)) * n
    pw_exc = row["PROT_AVG_WIDTH"] if "U-Trough" in sel else row["W"]
    pd_exc = (row["T_PROT_BASE_SLAB"] + 0.15) if "U-Trough" in sel else 2.15
    row["EXC_PROT"] = ((pw_exc + off) * (row["PROT_LEN"] + off) * pd_exc) * row["PROT_COUNT"] * n
    row["EXC_RET"] = (3.1 * 2.5 * 2.15) * row["PROT_COUNT"] * n if "Wing Wall" in sel else 0
    row["EXC_TOE_CURT"] = ((0.6+off)*row["TOE_D"]*row["L_TOE"]*row["TOE_COUNT"] + (0.7+off)*row["CURT_D"]*l_base*row["CURT_COUNT"]) * n
    row["GRAND_EXC"] = row["EXC_BOX"] + row["EXC_PROT"] + row["EXC_RET"] + row["EXC_TOE_CURT"]

    row["PCC_TOT"] = (((row["OUTER_WIDTH"]+poff)*(row["BARREL_LENGTH"]+poff)*tpcc) + \
                     ((pw_exc+poff)*(row["PROT_LEN"]+poff)*tpcc)*row["PROT_COUNT"] + \
                     (2.05*1.80*tpcc)*(row["PROT_COUNT"] if "Wing Wall" in sel else 0) + \
                     (0.6+poff)*(row["L_TOE"]+poff)*tpcc*row["TOE_COUNT"] + \
                     (0.7+poff)*(l_base+poff)*tpcc*row["CURT_COUNT"]) * n

    row["STEEL_TOT"] = (row["RCC_BOX"] * row["PERCENT_STEEL_BOX"]) + (row["RCC_PROT"] * row["PERCENT_STEEL_PROT"])
    hbf = VC + TS + row["THICK_BOTTOM_SLAB"]
    row["BF_TOT"] = ((0.5*hbf**2*row["BARREL_LENGTH"]*2) + (0.5*row["PROT_HT"]**2*row["PROT_LEN"]*row["PROT_COUNT"]) + (0.5*1.0**2*1.5*row["PROT_COUNT"] if "Wing Wall" in sel else 0)) * n
    row["FM_TOT"] = ((hbf*0.6*row["BARREL_LENGTH"]*2) + (row["PROT_HT"]*0.6*row["PROT_LEN"]*row["PROT_COUNT"]) + (1.0*0.6*1.5*row["PROT_COUNT"] if "Wing Wall" in sel else 0)) * n
    row["WC_TOT"] = (row["LENGTH_OF_CULVERT"]*row["NO_OF_CELLS"]*row["BARREL_LENGTH"]*0.15)*n
    row["RIGID"], row["LAUNCH"] = row["APRON_PLAN"]*0.3*n, row["APRON_PLAN"]*0.45*n
    
    if sel in ["Independent Retaining wall", "U-Trough Along Alignment"]:
        slant = np.sqrt(row["PROT_HT"]**2 + (row["PROT_HT"]*2)**2)
        row["PITCH"] = (np.pi*(row["PROT_HT"]*2)*slant/2)*4*0.3*n
    else: row["PITCH"] = 0
    
    def wh(h, l): return (np.floor((h-0.6)/1.0)+1) * (np.floor(l/1.0)+1) if h>0.6 else 0
    row["WEEP"] = (wh(VC, row["BARREL_LENGTH"])*2 + wh(row["PROT_HT"], row["PROT_LEN"])*row["PROT_COUNT"]) * n
    return row

# --- 3. UI ---
st.set_page_config(page_title="Culvert Master", layout="wide")
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
    cl, ln, vc = st.number_input("Cells", value=1), st.number_input("Span L", value=2.0), st.number_input("VC", value=2.0)
    hz = st.number_input("Haunch Size", value=0.15)
with c3:
    st.subheader("🧱 Concrete/Steel")
    tt, tb, ts = st.number_input("Top Slab", value=0.25), st.number_input("Bottom Slab", value=0.25), st.number_input("Side Wall", value=0.25)
    tm = st.number_input("Mid Wall", value=0.25) if cl > 1 else 0.0
    sbx, spr = st.number_input("Steel Box", value=85.0), st.number_input("Steel Prot", value=50.0)

if st.button("🚀 Generate Final BOQ"):
    inputs = {"NO_OF_CULVERTS": n_culv, "SIDE_SELECTION": side_sel, "PROT_SELECTION": prot_sel, "CURTAIN_WALL_LOCATION": curt_loc, "SHEAR_KEY_REQUIRED": sk_req, "WIDTH_AS_PER_TCS": rw, "FRL": frl, "GROUND_LEVEL": gl, "SLOPE_COUNT": sl, "SIDE_SLOPE_RATIO": sr, "NO_OF_CELLS": cl, "LENGTH_OF_CULVERT": ln, "VERTICAL_CLEARANCE_OF_CULVERT": vc, "HAUNCH_SIZE": hz, "TOP_SLAB_THICKNESS": tt, "THICK_BOTTOM_SLAB": tb, "SIDE_WALL_THICKNESS": ts, "MID_WALL_THICKNESS": tm, "PERCENT_STEEL_BOX": sbx, "PERCENT_STEEL_PROT": spr}
    
    res = calculate_full_boq(inputs)
    st.success("✅ BOQ Generated.")
    
    final_rows = [
        ["Excavation (Box)", f"{res['EXC_BOX']:.2f}", "m3", "1.0m offset"],
        ["Excavation (Protection)", f"{res['EXC_PROT']:.2f}", "m3", "Footing/Trough Logic"],
        ["Excavation (Return Wall)", f"{res['EXC_RET']:.2f}", "m3", "3.1x2.5 footprint"],
        ["Excavation (Toe/Curtain)", f"{res['EXC_TOE_CURT']:.2f}", "m3", "Structural footprint"],
        ["**TOTAL EXCAVATION**", f"{res['GRAND_EXC']:.2f}", "m3", "Total Earthwork"],
        ["PCC M15 (Grand Total)", f"{res['PCC_TOT']:.2f}", "m3", "100mm layer + offset"],
        ["RCC Grade M35 (Box Structure)", f"{res['RCC_BOX']:.2f}", "m3", "Main structure"],
        ["RCC Grade M35 (Prot + Return)", f"{res['RCC_PROT']:.2f}", "m3", "Stem & Footing volumes"],
        ["RCC Grade M25 (Toe Walls)", f"{res['RCC_M25_TOE']:.2f}", "m3", "0.370 area logic"],
        ["RCC Grade M15 (Curtain Walls)", f"{res['RCC_M15_CURT']:.2f}", "m3", "0.7m width logic"],
        ["Total Steel Reinforcement", f"{res['STEEL_TOT']:.2f}", "kg", "Concrete * Steel Ratios"],
        ["Total Backfill (1:1)", f"{res['TOT_BF']:.2f}", "m3", "0.5*H^2*L rule"],
        ["Total Filter Media", f"{res['TOT_FM']:.2f}", "m3", "600mm layer"],
        ["Wearing Course (150mm)", f"{res['TOT_WC']:.2f}", "m3", "Internal PCC"],
        ["Rigid Apron (300mm)", f"{res['RIGID']:.2f}", "m3", "Floor protection"],
        ["Launching Apron (450mm)", f"{res['LAUNCH']:.2f}", "m3", "Scour protection"],
        ["Quadrant Slope Pitching", f"{res['PITCH']:.2f}", "m3", "Quadrant area * 0.3"],
        ["Weep Holes (100mm)", f"{res['WEEP']:.0f}", "Nos", "1m spacing"]
    ]
    st.table(pd.DataFrame(final_rows, columns=["Description", "Quantity", "Unit", "Logic Audit"]))

    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 14); pdf.cell(190, 10, "BRIDGE CULVERT BOQ REPORT", ln=True, align='C')
    pdf.set_font("Arial", size=9)
    for r in final_rows:
        pdf.cell(80, 8, r[0].replace("**",""), 1); pdf.cell(30, 8, r[1], 1, 0, 'C'); pdf.cell(20, 8, r[2], 1, 0, 'C'); pdf.cell(60, 8, r[3], 1); pdf.ln()
    st.download_button("📥 Download PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="Detailed_BOQ.pdf", mime="application/pdf", key="pdf_dl")
