import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF

# --- 1. THE LOOKUP TABLE ---
# # Explained: This table contains standard dimensions (A to G) for 
# # Independent Retaining Walls. 'H' is the rounded height of the wall.
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
# # Explained: This function determines the geometry (height/length) 
# # of the Protection Walls (Wing Walls, Retaining Walls, etc.)
def calculate_geometry_pipeline(row):
    VC, TS, SW = row["VERTICAL_CLEARANCE_OF_CULVERT"], row["TOP_SLAB_THICKNESS"], row["SIDE_WALL_THICKNESS"]
    box_inner_ht = VC
    sel = row["PROT_SELECTION"]
    is_both = row["SIDE_SELECTION"] == "Both Sides"
    row["PROT_COUNT"] = 4 if is_both else 2
    
    # Logic for Independent Walls (Height = VC + Top Slab)
    if sel == "Independent Retaining wall":
        row["PROT_HT"] = box_inner_ht + TS
        row["PROT_LEN"] = (1.5 * row["PROT_HT"]) - SW
    
    # Logic for Wing Walls (Uses Average Height and 45-degree cosine length)
    elif sel == "Wing Wall + Return Wall":
        row["PROT_HT"] = (box_inner_ht + TS + 1.0) / 2
        row["PROT_LEN"] = (2 * (box_inner_ht + TS - 1.0)) / np.cos(np.radians(45))
    
    # Logic for U-Trough Wing Walls (Uses 30-degree cosine length)
    elif sel == "U-Trough Wing Wall":
        row["PROT_COUNT"] = 2 if is_both else 1
        row["PROT_HT"] = (box_inner_ht + TS + 1.0) / 2
        row["PROT_LEN"] = (2 * (box_inner_ht + TS - 1.0)) / np.cos(np.radians(30))
        bw = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
        # # Explained: Average width for U-Trough geometry using 30-deg spread
        row["PROT_AVG_WIDTH"] = (bw + (bw + (row["PROT_LEN"] * 2 * np.sin(np.radians(30))))) / 2
    
    elif sel == "U-Trough Along Alignment":
        row["PROT_COUNT"] = 2 if is_both else 1
        row["PROT_HT"] = box_inner_ht + TS
        row["PROT_LEN"] = (2 * row["PROT_HT"]) - SW
    return row

# # Explained: This function maps the PROT_HT to the nearest whole number 
# # to fetch the A-G parameters from our lookup table.
def assign_protection_sections(row):
    if row["PROT_SELECTION"] in ["Wing Wall + Return Wall", "Independent Retaining wall"]:
        h_idx = max(1, min(10, int(round(row["PROT_HT"]))))
        match = df_lookup[df_lookup['H'] == h_idx].iloc[0]
        for p in ['W', 'A', 'B', 'C', 'D', 'E', 'F', 'G']: row[p] = match[p]
    else:
        # For U-Troughs, slab thickness is defined by height brackets
        row["T_BASE_SLAB"] = 0.25 if row["PROT_HT"] <= 2 else 0.30 if row["PROT_HT"] <= 3 else 0.40
    return row

# # Explained: This function calculates the Curtain Walls and Apron plan area 
# # for scour protection based on the upstream/downstream location.
def calculate_scour_geometry(row):
    box_w = (row["LENGTH_OF_CULVERT"] * row["NO_OF_CELLS"]) + (row["MID_WALL_THICKNESS"] * row["NO_OF_MID_WALLS"])
    l_c = box_w + (row["PROT_LEN"] * 2 * np.sin(np.radians(45))) if row["PROT_SELECTION"] in ["U-Trough Wing Wall", "Wing Wall + Return Wall"] else (row["PROT_LEN"] * 2) + box_w
    row["L_CURTAIN"] = l_c
    ds, us = {"D":
