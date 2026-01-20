# app/main.py
import sys
from pathlib import Path

# Add project root to sys.path to allow 'app' module imports
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from pydantic import ValidationError

from app.models import ProjectInputs, Assumptions
from app.calculator import compute_footprint, calculate_score
from app.utils import load_projects, save_project
from app.constants import HARDWARE_DATA, DEFAULT_GRID_INTENSITY

st.set_page_config(page_title="EcoMetrics", layout="wide", page_icon="🌱")

# --- Sidebar ---
with st.sidebar:
    st.title("🌱 EcoMetrics")
    st.caption("AI Lifecycle Assessment Tool")
    page = st.radio("Navigation", ["Project Profile", "Infrastructure", "Usage", "Results", "Compare"])
    st.divider()
    
    with st.expander("⚙️ Advanced Settings (Assumptions)"):
        assumptions = Assumptions()
        assumptions.water_m3_per_mwh = st.number_input("Water Intensity (m³/MWh)", value=assumptions.water_m3_per_mwh, step=0.1, help="Average water consumption factor for electricity generation and datacenter cooling (Scope 2 Water).")
        assumptions.hardware_lifespan_years = st.number_input("Hardware Lifespan (years)", value=assumptions.hardware_lifespan_years, step=1.0, help="Expected total lifespan of the server hardware. Used to amortize the manufacturing carbon footprint (Scope 3).")

# --- Session State Init ---
if "inputs" not in st.session_state:
    st.session_state["inputs"] = ProjectInputs().model_dump()

def update_input(section, key, value):
    if section:
        st.session_state["inputs"][section][key] = value
    else:
        st.session_state["inputs"][key] = value

inputs_data = st.session_state["inputs"]

# --- PAGE 1: Project Profile ---
if page == "Project Profile":
    st.header("1. Project Profile")
    st.markdown("Define the identity and the expected lifespan of the project.")
    c1, c2 = st.columns(2)
    with c1:
        val = st.text_input("Project Name", value=inputs_data["project_name"], help="A unique name to identify this simulation.")
        update_input(None, "project_name", val)
        val = st.text_input("Owner / Team", value=inputs_data["owner"], help="The team or department responsible for this project.")
        update_input(None, "owner", val)
    with c2:
        val = st.number_input("Project Duration (years)", value=float(inputs_data["project_duration_years"]), min_value=0.1, step=0.5, help="How long will this project run? This is crucial to calculate the share of hardware manufacturing (amortization) attributed to this project.")
        update_input(None, "project_duration_years", val)
    
    amortization_pct = min(100, (val/assumptions.hardware_lifespan_years)*100)
    st.info(f"ℹ️ A project duration of **{val} years** means you are responsible for **{amortization_pct:.0f}%** of the hardware's manufacturing carbon footprint (based on a {assumptions.hardware_lifespan_years}-year server lifespan).")

# --- PAGE 2: Infrastructure ---
elif page == "Infrastructure":
    st.header("2. Infrastructure & Hardware")
    col_infra, col_hw = st.columns(2)
    with col_infra:
        st.subheader("Location & Efficiency")
        curr_region = inputs_data["infra"]["region"]
        
        # Region Selection
        new_region = st.selectbox("Region", list(DEFAULT_GRID_INTENSITY.keys()), index=list(DEFAULT_GRID_INTENSITY.keys()).index(curr_region) if curr_region in DEFAULT_GRID_INTENSITY else 0)
        update_input("infra", "region", new_region)
        
        # Auto-update Grid Intensity (Disabled/Read-only)
        intensity = float(DEFAULT_GRID_INTENSITY[new_region])
        update_input("infra", "grid_intensity_g_per_kwh", intensity)
        st.number_input("Grid Intensity (gCO2e/kWh)", value=intensity, disabled=True, help="Carbon intensity of the electricity grid in the selected region. Automatically determined by the region.")
        
        # PUE
        pue = st.number_input("PUE (Power Usage Effectiveness)", value=float(inputs_data["infra"]["pue"]), min_value=1.0, step=0.1, help="Ratio of total facility energy to IT equipment energy. 1.0 is ideal (no cooling cost). 1.2 is very efficient (Hyperscale Cloud). 1.6 is average on-premise.")
        update_input("infra", "pue", pue)
    with col_hw:
        st.subheader("Hardware Specs Reference")
        st.dataframe(pd.DataFrame(HARDWARE_DATA).T.style.format("{:.2f}"), use_container_width=True)
        st.caption("Reference values for Power (TDP) and Manufacturing Impact (GWP).")

# --- PAGE 3: Usage ---
elif page == "Usage":
    st.header("3. Usage & Compute")
    tab_train, tab_infer, tab_store = st.tabs(["Training", "Inference", "Storage"])
    
    with tab_train:
        do_train = st.checkbox("Include Training Phase", value=inputs_data["training"]["include_training"])
        update_input("training", "include_training", do_train)
        if do_train:
            c1, c2 = st.columns(2)
            with c1:
                hw = st.selectbox("Hardware Model", list(HARDWARE_DATA.keys()), index=list(HARDWARE_DATA.keys()).index(inputs_data["training"]["hardware_model"]), help="The GPU or TPU model used for training.")
                update_input("training", "hardware_model", hw)
                cnt = st.number_input("Count (GPUs)", value=int(inputs_data["training"]["hardware_count"]), min_value=1, help="Number of GPUs used in parallel.")
                update_input("training", "hardware_count", cnt)
            with c2:
                hrs = st.number_input("Total Training Duration (hours)", value=float(inputs_data["training"]["train_hours"]), min_value=0.0, help="Total computation time in hours.")
                update_input("training", "train_hours", hrs)

    with tab_infer:
        do_inf = st.checkbox("Include Inference Phase", value=inputs_data["inference"]["include_inference"])
        update_input("inference", "include_inference", do_inf)
        if do_inf:
            mode = st.radio("Calculation Mode", ["SaaS / API", "Self-Hosted"], index=0 if inputs_data["inference"]["mode"] == "SaaS / API" else 1, help="Choose 'SaaS / API' if you use a provider like OpenAI (Token based). Choose 'Self-Hosted' if you manage your own servers (Time/Hardware based).")
            update_input("inference", "mode", mode)
            reqs = st.number_input("Requests per Day", value=int(inputs_data["inference"]["req_per_day"]), min_value=1, help="Average number of queries/prompts processed daily.")
            update_input("inference", "req_per_day", reqs)
            if mode == "SaaS / API":
                tok = st.number_input("Avg Tokens per Request", value=int(inputs_data["inference"]["tokens_per_req"]), help="Sum of Input + Output tokens per request.")
                update_input("inference", "tokens_per_req", tok)
            else:
                hw_inf = st.selectbox("Inference Hardware", list(HARDWARE_DATA.keys()), key="inf_hw", index=list(HARDWARE_DATA.keys()).index(inputs_data["inference"]["hardware_model"]), help="The hardware used for serving the model.")
                update_input("inference", "hardware_model", hw_inf)
                cnt_inf = st.number_input("Hardware Count", value=int(inputs_data["inference"]["hardware_count"]), min_value=1, key="inf_cnt", help="Number of GPUs dedicated to inference.")
                update_input("inference", "hardware_count", cnt_inf)
                lat = st.number_input("Avg Latency (s)", value=float(inputs_data["inference"]["latency_per_req_s"]), min_value=0.01, help="Time taken to process one request (in seconds).")
                update_input("inference", "latency_per_req_s", lat)

    with tab_store:
        do_sn = st.checkbox("Include Storage & Network", value=inputs_data["storage_network"]["include_storage_network"])
        update_input("storage_network", "include_storage_network", do_sn)
        if do_sn:
            gb = st.number_input("Dataset Size (GB)", value=float(inputs_data["storage_network"]["dataset_gb"]), help="Total volume of data stored (Datasets + Models).")
            update_input("storage_network", "dataset_gb", gb)
            tr = st.number_input("Data Transfer (GB/day)", value=float(inputs_data["storage_network"]["transfer_gb_per_day"]), help="Average daily data transfer (Inbound + Outbound).")
            update_input("storage_network", "transfer_gb_per_day", tr)

# --- PAGE 4: Results ---
elif page == "Results":
    st.header("4. Results & Analysis")
    try:
        inputs_obj = ProjectInputs(**inputs_data)
        res = compute_footprint(inputs_obj, assumptions)
        score = calculate_score(res)
        
        col_score, col_kpi = st.columns([1, 2])
        with col_score:
            st.markdown(f"""
            <div style="background-color: {score.color}20; border: 2px solid {score.color}; border-radius: 10px; padding: 20px; text-align: center;">
                <h3 style="color: {score.color}; margin:0;">Grade {score.grade}</h3>
                <h1 style="font-size: 4em; margin:0;">{score.score_100}</h1>
                <p style="margin:0;"><b>{score.label}</b></p>
            </div>
            """, unsafe_allow_html=True)
        with col_kpi:
            k1, k2, k3 = st.columns(3)
            k1.metric("Total CO₂ (Lifecycle)", f"{res.total_co2_kg:.0f} kg")
            k2.metric("Total Energy", f"{res.total_energy_kwh:.0f} kWh")
            k3.metric("Total Water", f"{res.total_water_m3:.1f} m³")
            st.divider()
            st.metric("Annual CO₂", f"{res.annual_co2_kg:.0f} kg/y")

        st.subheader("Detailed Breakdown")
        breakdown_data = {
            "Phase": ["Training", "Training", "Inference", "Inference", "Storage/Network"],
            "Type": ["Usage", "Embodied", "Usage", "Embodied", "Usage"],
            "CO2 (kg)": [res.co2_training_usage, res.co2_training_embodied, res.co2_inference_usage, res.co2_inference_embodied, res.co2_storage_network]
        }
        df_chart = pd.DataFrame(breakdown_data)
        fig = px.bar(df_chart, x="Phase", y="CO2 (kg)", color="Type", title="CO₂ Impact by Phase & Scope")
        st.plotly_chart(fig, use_container_width=True)

        if st.button("💾 Save Project Result"):
            save_project(inputs_obj, res, score)
            st.success("Project saved to CSV!")

    except ValidationError as e:
        st.error(f"Input Validation Error: {e}")

# --- PAGE 5: Compare ---
elif page == "Compare":
    st.header("5. Compare Projects")
    df = load_projects()
    if df.empty:
        st.info("No saved projects yet.")
    else:
        st.dataframe(df, use_container_width=True)
        if len(df) >= 2:
            st.subheader("Comparison")
            projects = df["project_name"].unique()
            p1 = st.selectbox("Project A", projects, index=0)
            p2 = st.selectbox("Project B", projects, index=1)
            if p1 and p2:
                row1 = df[df["project_name"] == p1].iloc[-1]
                row2 = df[df["project_name"] == p2].iloc[-1]
                col1, col2, col3 = st.columns(3)
                col1.metric("CO₂ Total (A)", f"{row1['total_co2_kg']:.0f} kg")
                col2.metric("CO₂ Total (B)", f"{row2['total_co2_kg']:.0f} kg")
                col3.metric("Delta (B - A)", f"{row2['total_co2_kg'] - row1['total_co2_kg']:+.0f} kg")