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

# --- 2. THE ENGINE BLOCK ---

def run_engine(row):
    n = row["NO_OF_CULVERTS"]
    # Box Setup
    row["NO_OF_MID_WALLS"] = row["NO_OF_CELLS"] - 1 if row["NO_OF_CELLS"] > 1 else 0
    row["TRANSVERSE_W"] = (row["L_INNER"] * row["NO_OF_CELLS"]) + (2 * row["T_SIDE_WALL"]) + (row["NO_OF_MID_WALLS"] * row["T_MID_WALL"])
    row["CUSHION"] = row["FRL"] - row["GL"] - row["VC_INNER"] - row["T_TOP_SLAB"]
    row["BARREL_L"] = row["ROAD_W"] + (row["SLOPE_COUNT"] * row["SLOPE_RATIO"] * row["CUSHION"])
    
    # Protection Setup
    box_inner_ht = row["VC_INNER"] + row["T_TOP_SLAB"]
    is_both = row["SIDE_SEL"] == "Both Sides"
    sel = row["PROT_SEL"]
    
    for p in ['W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = 0.0
    row["P_AVG_W"] = 0.0

    if sel == "Independent Retaining wall":
        row["P_COUNT"], row["P_HT"] = (4 if is_both else 2), box_inner_ht
        row["P_LEN"] = (1.5 * row["P_HT"]) - row["T_SIDE_WALL"]
    elif sel == "Wing Wall + Return Wall":
        row["P_COUNT"], row["P_HT"] = (4 if is_both else 2), (box_inner_ht + 1.0) / 2
        row["P_LEN"] = (2 * (box_inner_ht - 1.0)) / np.cos(np.radians(45))
    elif sel == "U-Trough Wing Wall":
        row["P_COUNT"], row["P_HT"] = (2 if is_both else 1), (box_inner_ht + 1.0) / 2
        row["P_LEN"] = (2 * (box_inner_ht - 1.0)) / np.cos(np.radians(30))
        bw = (row["L_INNER"] * row["NO_OF_CELLS"]) + (row["T_MID_WALL"] * row["NO_OF_MID_WALLS"])
        end_w = bw + (row["P_LEN"] * 2 * np.sin(np.radians(45)))
        row["P_AVG_W"] = (bw + end_w) / 2
    else: # Alignment
        row["P_COUNT"], row["P_HT"] = (2 if is_both else 1), box_inner_ht
        row["P_LEN"] = (2 * row["P_HT"]) - row["T_SIDE_WALL"]
        row["P_AVG_W"] = row["BARREL_L"]

    if sel in ["Wing Wall + Return Wall", "Independent Retaining wall"]:
        h_idx = max(1, min(10, int(round(row["P_HT"]))))
        match = df_lookup[df_lookup['H'] == h_idx].iloc[0]
        for p in ['W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = float(match[p])
        row["T_PROT_BASE_SLAB"] = 0.0
    else:
        row["T_PROT_BASE_SLAB"] = 0.25 if row["P_HT"] <= 2 else 0.30 if row["P_HT"] <= 3 else 0.40

    row["TOE_COUNT"] = row["P_COUNT"] if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"] else 0
    if sel == "Wing Wall + Return Wall": row["L_TOE"] = 2 * np.pi * 2 * 0.25
    elif sel == "Independent Retaining wall": row["L_TOE"] = (2 * np.pi * np.sqrt(((row["P_HT"]*2)**2 + (1.5*row["P_HT"])**2)/2))/4
    elif sel == "U-Trough Along Alignment": row["L_TOE"] = (row["P_HT"] * 2 * np.pi * 2) / 4
    else: row["L_TOE"] = 0.0
    row["TOE_X_A"], row["TOE_DEPTH"] = (0.370, 1.05) if row["L_TOE"] > 0 else (0.0, 0.0)

    box_iw = (row["L_INNER"] * row["NO_OF_CELLS"]) + (row["T_MID_WALL"] * row["NO_OF_MID_WALLS"])
    l_base = box_iw + (row["P_LEN"] * 2 * np.sin(np.radians(45))) if "Wing" in sel else (row["P_LEN"] * 2) + box_iw
    ds_a, us_a, ds_d, us_d = 0.828, 0.703, 2.5, 2.0
    if row["CURT_LOC"] == "Both Sides":
        row["C_COUNT"], row["C_A_T"], row["C_D"] = 2, (ds_a + us_a) * l_base, 2.25
    else:
        row["C_COUNT"] = 1
        row["C_A_T"] = (ds_a if "D/S" in row["CURT_LOC"] else us_a) * l_base
        row["C_D"] = ds_d if "D/S" in row["CURT_LOC"] else us_d

    off, poff, tpcc = 1.0, 0.3, 0.1
    row["E_BOX"] = ((row["TRANSVERSE_W"] + off) * (row["BARREL_L"] + off) * (row["T_BOT_SLAB"] + 0.15)) * n
    pw = row["P_AVG_W"] if "U-Trough" in sel else row["W"]
    pd = (row["T_PROT_BASE_SLAB"] + 0.15) if "U-Trough" in sel else 2.15
    row["E_PROT"] = ((pw + off) * (row["P_LEN"] + off) * pd) * row["P_COUNT"] * n
    row["E_RET"] = (3.1 * 2.5 * 2.15) * row["P_COUNT"] * n if "Wing Wall" in sel else 0.0
    row["E_SCOUR"] = ((0.6+off)*row["TOE_DEPTH"]*row["L_TOE"]*row["TOE_COUNT"] + (0.7+off)*row["C_D"]*l_base*row["C_COUNT"]) * n
    row["GRAND_EXC"] = row["E_BOX"] + row["E_PROT"] + row["E_RET"] + row["E_SCOUR"]

    row["P_BOX"] = ((row["TRANSVERSE_W"]+poff)*(row["BARREL_L"]+poff)*tpcc) * n
    row["P_PROT"] = ((pw+poff)*(row["P_LEN"]+poff)*tpcc) * row["P_COUNT"] * n
    row["P_RET"] = (2.05*1.80*tpcc) * row["P_COUNT"] * n if "Wing Wall" in sel else 0.0
    row["P_SCOUR"] = ((0.6+poff)*(row["L_TOE"]+poff)*tpcc*row["TOE_COUNT"] + (0.7+poff)*(l_base+poff)*tpcc*row["C_COUNT"]) * n
    row["GRAND_PCC"] = row["P_BOX"] + row["P_PROT"] + row["P_RET"] + row["P_SCOUR"]

    hk = 1.2 - row["T_BOT_SLAB"]
    row["R_BOX"] = (row["TRANSVERSE_W"]*row["BARREL_L"]*(row["T_BOT_SLAB"]+row["T_TOP_SLAB"]) + 
                   (2*row["T_SIDE_WALL"] + row["NO_OF_MID_WALLS"]*row["T_MID_WALL"])*row["VC_INNER"]*row["BARREL_L"] + 
                   (0.5*row["HAUNCH"]**2*4*row["NO_OF_CELLS"]*row["BARREL_L"]) + 
                   ((row["TRANSVERSE_W"]*0.7*hk)*2 if row["SK_REQ"]=="Yes" else 0.0)) * n

    if sel in ["Independent Retaining wall", "Wing Wall + Return Wall"]:
        aftg = (row["A"]*(row["F"]+row["E"])/2) + (row["B"]*row["E"]) + (row["C"]*(row["E"]+row["G"])/2)
        astem = ((row["B"] + 0.3)/2) * row["P_HT"]
        row["R_PROT"] = (aftg + astem) * row["P_LEN"] * row["P_COUNT"] * n
        row["R_RET"] = (aftg + (((row["B"] + 0.3)/2)*1.0)) * 1.5 * row["P_COUNT"] * n if "Wing Wall" in sel else 0.0
    else:
        row["R_PROT"] = (pw*row["PROT_LEN"]*row["T_PROT_BASE_SLAB"] + 2*row["P_HT"]*row["PROT_LEN"]*row["T_SIDE_WALL"]) * row["P_COUNT"] * n
        row["R_RET"] = 0.0

    row["R_M25_TOE"] = row["TOE_X_A"] * row["L_TOE"] * row["TOE_COUNT"] * n
    row["R_M15_CURT"] = row["C_A_T"] * n

    row["S_BOX"] = row["R_BOX"] * row["ST_BOX"]
    row["S_PROT"] = (row["R_PROT"] + row["R_RET"]) * row["ST_PROT"]
    hb = row["VC_INNER"] + row["T_TOP_SLAB"] + row["T_BOT_SLAB"]
    row["BF"] = ((0.5*hb**2*row["BARREL_L"]*2) + (0.5*row["P_HT"]**2*row["P_LEN"]*row["P_COUNT"]) + (0.5*1.0**2*1.5*row["P_COUNT"] if "Wing Wall" in sel else 0.0)) * n
    row["FM"] = ((hb*0.6*row["BARREL_L"]*2) + (row["P_HT"]*0.6*row["P_LEN"]*row["P_COUNT"]) + (1.0*0.6*1.5*row["P_COUNT"] if "Wing Wall" in sel else 0.0)) * n
    row["WC"] = (row["L_INNER"]*row["NO_OF_CELLS"]*row["BARREL_L"]*0.15)*n
    
    ap_area = 0.0 if "U-Trough" in sel else ((box_iw + l_base) / 2) * row["P_LEN"] * row["C_COUNT"]
    row["RIGID"], row["LAUNCH"] = ap_area*0.3*n, ap_area*0.45*n
    
    if sel in ["Independent Retaining wall", "U-Trough Along Alignment"]:
        slant = np.sqrt(row["P_HT"]**2 + (row["P_HT"]*2)**2)
        row["PITCH"] = (np.pi*(row["P_HT"]*2)*slant/2)*4*0.3*n
        row["PITCH_FM"] = row["PITCH"]
    else:
        row["PITCH"] = 0.0
        row["PITCH_FM"] = 0.0
    
    def get_wh(h, l):
        rows = np.floor((h - 0.6) / 1.0) + 1 if h > 0.6 else 1.0
        cols = np.floor(l / 1.0) + 1
        return rows * cols
    row["WEEP"] = (get_wh(row["VC_INNER"], row["BARREL_L"]) * 2 + get_wh(row["P_HT"], row["P_LEN"]) * row["P_COUNT"]) * n
    return row

# --- 3. UI ---
st.set_page_config(page_title="Culvert Master", layout="wide")
st.title("🏗️ Bridge Culvert BOQ Master Engine")

with st.sidebar:
    st.header("📋 Configuration")
    n_culv = st.number_input("Number of Culverts", value=1, min_value=1)
    side_sel = st.selectbox("Side Selection", ["Both Sides", "One Side"])
    prot_sel = st.selectbox("Protection Type", ["Independent Retaining wall", "Wing Wall + Return Wall", "U-Trough Wing Wall", "U-Trough Along Alignment"])
    curt_loc = st.selectbox("Curtain Wall Location", ["Both Sides", "U/S Only", "D/S Only"])
    sk_req = st.radio("Shear Key Required?", ["Yes", "No"])

c1, c2, c3 = st.columns(3)
with c1:
    rw, frl, gl = st.number_input("TCS Width (m)", value=7.0), st.number_input("FRL (m)", value=5.0), st.number_input("GL (m)", value=2.0)
    sl, sr = st.selectbox("Slope Count", [0, 1, 2], index=2), st.number_input("Ratio", value=1.5)
with c2:
    cl, ln, vc = st.number_input("Cells", value=1), st.number_input("Span L", value=2.0), st.number_input("VC", value=2.0)
    hz = st.number_input("Haunch", value=0.15)
with c3:
    tt, tb, ts = st.number_input("Top Slab", value=0.25), st.number_input("Bottom Slab", value=0.25), st.number_input("Wall", value=0.25)
    tm = st.number_input("Mid Wall", value=0.25) if cl > 1 else 0.0
    sbx, spr = st.number_input("Steel Box", value=85.0), st.number_input("Steel Prot", value=50.0)

if st.button("🚀 Generate Final BOQ"):
    d = {"NO_OF_CULVERTS": n_culv, "SIDE_SEL": side_sel, "PROT_SEL": prot_sel, "CURT_LOC": curt_loc, "SK_REQ": sk_req, "ROAD_W": rw, "FRL": frl, "GL": gl, "SLOPE_COUNT": sl, "SLOPE_RATIO": sr, "NO_OF_CELLS": cl, "L_INNER": ln, "VC_INNER": vc, "HAUNCH": hz, "T_TOP_SLAB": tt, "T_BOT_SLAB": tb, "T_SIDE_WALL": ts, "T_MID_WALL": tm, "ST_BOX": sbx, "ST_PROT": spr}
    res = run_engine(d)
    
    col_res, col_img = st.columns([2, 1])

    with col_res:
        st.success("✅ Results Table")
        table = [
            ["--- PROJECT SPECIFICATIONS ---", "", "", ""],
            ["Final Barrel Length", f"{res['BARREL_L']:.3f}", "m", "Road Width + Slopes"],
            ["Total Transverse Width", f"{res['TRANSVERSE_W']:.3f}", "m", "Spans + All Walls"],
            ["Available Cushion", f"{res['CUSHION']:.3f}", "m", "FRL to Top Slab"],
            ["--- EARTHWORK ---", "", "", ""],
            ["Excavation (Box)", f"{res['E_BOX']:.2f}", "m3", "1.0m offset"],
            ["Excavation (Protection)", f"{res['E_PROT']:.2f}", "m3", "Base + offsets"],
            ["Excavation (Return Walls)", f"{res['E_RET']:.2f}", "m3", "3.1x2.5 fixed"],
            ["Excavation (Toe & Curtain)", f"{res['E_SCOUR']:.2f}", "m3", "Scour footprint"],
            ["**TOTAL EXCAVATION**", f"{res['GRAND_EXC']:.2f}", "m3", ""],
            ["--- PCC GRADE M15 ---", "", "", ""],
            ["PCC (Box Foundation)", f"{res['P_BOX']:.2f}", "m3", "300mm offset"],
            ["PCC (Protection Foundation)", f"{res['P_PROT']:.2f}", "m3", "300mm offset"],
            ["PCC (Return Wall Foundation)", f"{res['P_RET']:.2f}", "m3", "Fixed footprint"],
            ["PCC (Scour Components)", f"{res['P_SCOUR']:.2f}", "m3", "Toe/Curtain base"],
            ["**TOTAL PCC M15**", f"{res['GRAND_PCC']:.2f}", "m3", ""],
            ["--- RCC WORKS ---", "", "", ""],
            ["RCC M35 (Box Structure)", f"{res['R_BOX']:.2f}", "m3", "Main barrel"],
            ["RCC M35 (Main Protections)", f"{res['R_PROT']:.2f}", "m3", "Wall stems"],
            ["RCC M35 (Return Walls)", f"{res['R_RET']:.2f}", "m3", "1.0m stem height"],
            ["RCC M25 (Toe Walls)", f"{res['R_M25_TOE']:.2f}", "m3", "0.370 area logic"],
            ["RCC M15 (Curtain Walls)", f"{res['R_M15_CURT']:.2f}", "m3", "0.7m width logic"],
            ["--- REINFORCEMENT & FINISH ---", "", "", ""],
            ["Steel for Box", f"{res['S_BOX']:.2f}", "kg", "Ratio applied"],
            ["Steel for Protection", f"{res['S_PROT']:.2f}", "kg", "Ratio applied"],
            ["**GRAND TOTAL STEEL**", f"{res['S_BOX']+res['S_PROT']:.2f}", "kg", ""],
            ["Backfill (1:1 Slope)", f"{res['BF']:.2f}", "m3", "0.5*H^2*L"],
            ["Filter Media", f"{res['FM']:.2f}", "m3", "600mm layer"],
            ["Rigid Apron (300mm)", f"{res['RIGID']:.2f}", "m3", "Floor protection"],
            ["Launching Apron (450mm)", f"{res['LAUNCH']:.2f}", "m3", "Scour protection"],
            ["Quadrant Slope Pitching", f"{res['PITCH']:.2f}", "m3", "Slant quadrant logic"],
            ["Pitching Filter Media", f"{res['PITCH_FM']:.2f}", "m3", "Drainage layer"],
            ["Weep Holes (100mm PVC)", f"{res['WEEP']:.0f}", "Nos", "Col x Row logic"]
        ]
        st.table(pd.DataFrame(table, columns=["Description", "Quantity", "Unit", "Logic Audit"]))

    with col_img:
        st.info("📦 Visual Reference")
        st.image("https://www.civilengineersforum.com/wp-content/uploads/2018/01/Box-Culvert-Design.jpg", caption="Box Culvert Sectional View Detail")
        st.metric("Final Barrel Length", f"{res['BARREL_L']:.2f} m")
        st.metric("Total Transverse Width", f"{res['TRANSVERSE_W']:.2f} m")
        st.metric("Design Cushion", f"{res['CUSHION']:.2f} m")

    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 14); pdf.cell(190, 10, "BRIDGE CULVERT BOQ REPORT", ln=True, align='C')
    pdf.set_font("Arial", size=8)
    for r in table:
        if r[1] != "":
            pdf.cell(85, 7, r[0].replace("**",""), 1); pdf.cell(25, 7, r[1], 1, 0, 'C'); pdf.cell(20, 7, r[2], 1, 0, 'C'); pdf.cell(60, 7, r[3], 1); pdf.ln()
    st.download_button("📥 Download PDF Report", data=pdf.output(dest='S').encode('latin-1'), file_name="Culvert_BOQ.pdf", mime="application/pdf", key="dl_pdf")
