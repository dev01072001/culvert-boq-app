import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("🏗️ Bridge Culvert BOQ Master (DPR Level)")

# =========================
# SIDEBAR CONFIG
# =========================
st.sidebar.header("Configuration")

n_culverts = st.sidebar.number_input("Number of Culverts", 1, 20, 1)

side_selection = st.sidebar.selectbox("Side Selection", ["Left", "Right", "Both"])

protection_type = st.sidebar.selectbox(
    "Protection Type",
    ["Independent Retaining Wall", "Pitching", "Both"]
)

curtain_wall_loc = st.sidebar.selectbox(
    "Curtain Wall Location",
    ["Left", "Right", "Both"]
)

shear_key = st.sidebar.radio("Shear Key Required?", ["Yes", "No"])

# =========================
# SITE LEVELS
# =========================
st.subheader("📍 Site Levels")

road_width = st.number_input("Road Width (m)", value=7.0)
frl = st.number_input("FRL (m)", value=5.0)
il = st.number_input("IL (m)", value=2.0)

n_slopes = st.number_input("No. of Slopes", 1, 4, 2)
slope_ratio = st.number_input("Slope Ratio", value=1.5)

# =========================
# BOX SPECS
# =========================
st.subheader("📦 Box Specs")

cells = st.number_input("No. of Cells", 1, 5, 1)
span = st.number_input("Span L (m)", value=2.0)
height = st.number_input("Height VC (m)", value=2.0)
haunch = st.number_input("Haunch (m)", value=0.15)

# =========================
# CONCRETE & STEEL
# =========================
st.subheader("🧱 Concrete & Steel")

top_slab = st.number_input("Top Slab (m)", value=0.25)
bottom_slab = st.number_input("Bottom Slab (m)", value=0.25)
wall_thickness = st.number_input("Wall Thickness (m)", value=0.25)

steel_box = st.number_input("Steel Box (kg/m3)", value=85.0)
steel_prot = st.number_input("Steel Protection (kg/m3)", value=85.0)

# =========================
# DERIVED VALUES (KEEP FLEXIBLE)
# =========================
length = road_width

clear_height = frl - il

# ⚠️ IMPORTANT: You can modify this logic as per your original code
prot_ht = clear_height   # Replace with your formula if needed

# =========================
# BOX CALCULATIONS
# =========================
top_slab_vol = cells * span * length * top_slab
bottom_slab_vol = cells * span * length * bottom_slab
wall_vol = 2 * height * length * wall_thickness * cells

box_rcc = top_slab_vol + bottom_slab_vol + wall_vol
box_steel_qty = box_rcc * steel_box

# =========================
# EXCAVATION (BOX)
# =========================
exc_depth = clear_height + bottom_slab
exc_width = (cells * span) + 2 * wall_thickness

excavation_box = exc_depth * exc_width * length

# =========================
# PCC (BOX)
# =========================
pcc_box = exc_width * length * 0.1  # thickness can be made input later

# =========================
# CURTAIN WALL (INPUT DRIVEN)
# =========================
cw_thickness = st.number_input("Curtain Wall Thickness (m)", value=0.3)

cw_height = clear_height
cw_length = length

cw_rcc = 2 * cw_height * cw_thickness * cw_length

exc_cw = 2 * cw_height * cw_thickness * cw_length
pcc_cw = 2 * cw_length * cw_thickness * 0.1

# =========================
# PROTECTION WORK (INPUT DRIVEN)
# =========================
prot_thickness = st.number_input("Protection Thickness (m)", value=0.15)

prot_length = prot_ht * slope_ratio

prot_rcc = 2 * prot_length * length * prot_thickness

prot_steel_qty = prot_rcc * steel_prot

exc_prot = prot_rcc
pcc_prot = 2 * prot_length * length * 0.1

# =========================
# BOQ TABLE
# =========================
data = [
    # Excavation
    [1, "Excavation for Box", "m3", excavation_box],
    [2, "Excavation for Curtain Wall", "m3", exc_cw],
    [3, "Excavation for Protection", "m3", exc_prot],

    # PCC
    [4, "PCC for Box", "m3", pcc_box],
    [5, "PCC for Curtain Wall", "m3", pcc_cw],
    [6, "PCC for Protection", "m3", pcc_prot],

    # RCC - BOX
    [7, "RCC Top Slab", "m3", top_slab_vol],
    [8, "RCC Bottom Slab", "m3", bottom_slab_vol],
    [9, "RCC Walls", "m3", wall_vol],

    # Curtain Wall
    [10, "RCC Curtain Walls", "m3", cw_rcc],

    # Protection
    [11, "RCC Protection Works", "m3", prot_rcc],

    # Steel
    [12, "Steel in Box", "kg", box_steel_qty],
    [13, "Steel in Protection", "kg", prot_steel_qty],
]

df = pd.DataFrame(data, columns=["Item No", "Description", "Unit", "Quantity"])

# Multiply by number of culverts
df["Quantity"] = df["Quantity"] * n_culverts

# =========================
# DISPLAY
# =========================
st.subheader("📊 BOQ Schedule")
st.dataframe(df, use_container_width=True)

# =========================
# SUMMARY
# =========================
st.subheader("📌 Summary")

summary = df.groupby("Unit")["Quantity"].sum().reset_index()
st.dataframe(summary)

# =========================
# DOWNLOAD
# =========================
excel_file = "BOQ_Output.xlsx"
df.to_excel(excel_file, index=False)

with open(excel_file, "rb") as f:
    st.download_button(
        "📥 Download BOQ Excel",
        f,
        file_name="BOQ.xlsx"
    )
