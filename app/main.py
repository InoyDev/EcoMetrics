# app/main.py
import sys
from pathlib import Path
from datetime import datetime

# Add project root to sys.path to allow 'app' module imports
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from pydantic import ValidationError

from app.models import ProjectInputs, Assumptions, FootprintResult
from app.calculator import compute_footprint, calculate_score, simulate_what_if
from app.utils import load_projects, save_project, delete_project, save_custom_row

from app.constants import HARDWARE_CATALOG, PROJECT_TYPES, INFRASTRUCTURE_PROFILES, DEFAULT_GRID_INTENSITY, API_MODELS

st.set_page_config(page_title="EcoMetrics", layout="wide", page_icon="🌱")

# Mise en page et style
st.markdown("""
<style>
/* Page */
.main {background-color: #ffffff;}
.block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1250px;}

/* Titles */
h1, h2, h3, h4 {color: #0b1220 !important;}
p, li, div, label, .stMarkdown {color: #1a1a1a !important;}

/* Sidebar */
section[data-testid="stSidebar"] {background-color: #07101f; min-width: 350px !important;}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {color: #eaf0ff !important;}
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] li, section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] label {color: #dbe6ff !important;}

/* Cards */
.kpi-card {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.kpi-title {font-size: 12px; opacity: .85; letter-spacing: .05em; text-transform: uppercase; color: #666;}
.kpi-value {font-size: 34px; font-weight: 800; line-height: 1.1; margin-top: 6px; color: #0b1220;}
.kpi-sub {font-size: 12px; opacity: .85; margin-top: 8px; color: #666;}
.badge {
  display: inline-block; padding: 4px 10px; border-radius: 999px;
  border: 1px solid #dee2e6;
  background: #e9ecef;
  font-size: 12px; margin-left: 8px;
  color: #333;
}
</style>
""", unsafe_allow_html=True)

# def pour les kpis
def kpi_card(title: str, value: str, subtitle: str = "", badge: str = ""):
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-title">{title} {"<span class='badge'>"+badge+"</span>" if badge else ""}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)



# --- Sidebar ---
with st.sidebar:
    # Logo LVMH pleine largeur
    st.image(str(Path(__file__).parent / "lvmh_logo.png"), width="stretch")

    st.title("🌱 EcoMetrics")
    st.caption("AI Lifecycle Assessment Tool")
    # Simplified Navigation
    page = st.radio("Navigation", ["Calculator", "Projects"])
    st.divider()
    
    with st.expander("⚙️ Advanced Settings (Assumptions)"):
        assumptions = Assumptions()
        assumptions.water_m3_per_mwh = st.number_input("Water Intensity (m³/MWh)", value=assumptions.water_m3_per_mwh, step=0.1, help="Average water consumption factor for electricity generation and datacenter cooling (Scope 2 Water).")
        assumptions.hardware_lifespan_years = st.number_input("Hardware Lifespan (years)", value=assumptions.hardware_lifespan_years, step=1.0, help="Expected total lifespan of the server hardware. Used to amortize the manufacturing carbon footprint (Scope 3).")
        assumptions.api_energy_kwh_per_query = st.number_input(
            "API Energy (kWh / query)",
            value=float(assumptions.api_energy_kwh_per_query),
            step=0.0001,
            format="%.4f",
            help="Proxy energy for GenAI SaaS/API. Default 0.0003 kWh/query (0.3 Wh)."
        )


# --- Session State Init ---
if "inputs" not in st.session_state:
    st.session_state["inputs"] = ProjectInputs().model_dump()
    st.session_state["inputs"]["storage_network"]["include_storage_network"] = False

def update_input(section, key, widget_key):
    val = st.session_state[widget_key]
    if section:
        st.session_state["inputs"][section][key] = val
    else:
        st.session_state["inputs"][key] = val

def get_filtered_hardware(p_type):
    # Filter hardware based on project type for better UX
    if p_type == "ml_classic":
        return [h for h in HARDWARE_CATALOG if h["type"] == "cpu"]
    return HARDWARE_CATALOG

inputs_data = st.session_state["inputs"]

# --- PAGE: Calculator ---
if page == "Calculator":
    st.markdown(
        "<h1 style='text-align:center;'>AI Project Footprint Calculator</h1>",
        unsafe_allow_html=True
    )


 # --- STEP 1: GLOBAL PROFILE ---
    st.subheader("1. Global Profile")
    st.caption(
        "This section defines the overall context of the project (type, environment and expected duration). "
        "These selections allow the tool to automatically adjust calculation logic and assumptions, "
        "ensuring consistent and comparable environmental assessments across projects."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Project Name", value=inputs_data["project_name"], key="p_name", on_change=update_input, args=(None, "project_name", "p_name"), help="A unique name to identify this simulation.")
        st.selectbox("Project Environment", ["Dev/PoC", "Production"], index=0 if inputs_data["environment"] == "Dev/PoC" else 1, key="p_env", on_change=update_input, args=(None, "environment", "p_env"), help="Categorizes the project context. 'Dev/PoC' implies short-term experiments, while 'Production' implies long-term deployment.")
    with c2:
        # Project Type Selection
        p_types = list(PROJECT_TYPES.keys())
        p_labels = [PROJECT_TYPES[k] for k in p_types]
        curr_type = inputs_data["project_type"]
        idx = p_types.index(curr_type) if curr_type in p_types else 2
        
        def update_type():
            st.session_state["inputs"]["project_type"] = st.session_state["p_type_sel"]
            
        st.selectbox("Project Type", p_types, format_func=lambda x: PROJECT_TYPES[x], index=idx, key="p_type_sel", on_change=update_type, help="Select the archetype that best fits your project:\n- **Classic ML**: Low compute, often CPU-based (e.g., XGBoost).\n- **Deep Learning**: High compute, GPU-based training (e.g., ResNet, BERT).\n- **GenAI**: Large Language Models, either via API or self-hosted.")
        
    with c3:
        st.number_input("Project Duration (years)", value=float(inputs_data["project_duration_years"]), min_value=0.1, step=0.5, key="p_duration", on_change=update_input, args=(None, "project_duration_years", "p_duration"), help="How long will this project run? This is crucial to calculate the share of hardware manufacturing (amortization) attributed to this project.")
    

    # --- STEP 2: DEVELOPMENT & TRAINING ---
    st.subheader("2. Development & Training (MLOps)")
    st.caption(
        "This section captures the resources used during the development and training phases. "
        "It covers exploratory work, model training and retraining activities. "
        "The information provided here is used to estimate both operational emissions and the "
        "allocated share of hardware manufacturing impact over the project lifecycle."
    )

    # Development Phase
    st.markdown("**🛠️ Development Phase (Exploration)**")
    d1, d2, d3 = st.columns(3)
    with d1:
        st.selectbox("Dev Infrastructure", list(INFRASTRUCTURE_PROFILES.keys()), format_func=lambda x: INFRASTRUCTURE_PROFILES[x]["name"], index=list(INFRASTRUCTURE_PROFILES.keys()).index(inputs_data["development"]["infra_type"]), key="d_infra", on_change=update_input, args=("development", "infra_type", "d_infra"), help="The environment where development takes place. Affects energy efficiency (PUE). 'Local' = 1.0, 'Cloud' = 1.2.")
    with d2:
        # Filter hardware for Dev (mostly laptops/CPU)
        dev_hw_opts = [h for h in HARDWARE_CATALOG if h["type"] == "cpu" or "laptop" in h["id"]]
        dev_hw_ids = [h["id"] for h in dev_hw_opts]
        curr_dev_hw = inputs_data["development"]["hardware_id"]
        st.selectbox("Dev Hardware", dev_hw_ids, format_func=lambda x: next((h["name"] for h in dev_hw_opts if h["id"] == x), x), index=dev_hw_ids.index(curr_dev_hw) if curr_dev_hw in dev_hw_ids else 0, key="d_hw", on_change=update_input, args=("development", "hardware_id", "d_hw"), help="The primary hardware used by data scientists. Laptops have high embodied carbon relative to their energy usage.")
    with d3:
        st.number_input("Dev Hours (Coding/Testing)", value=float(inputs_data["development"]["dev_hours"]), min_value=0.0, step=10.0, key="d_hours", on_change=update_input, args=("development", "dev_hours", "d_hours"), help="Total estimated hours spent by the team on exploration, coding, and debugging.")
    
    # --- PIVOT QUESTION (Training Phase Visibility) ---
    st.markdown("---")
    
    def update_training_visibility():
        val = st.session_state["train_vis_radio"]
        if val == "Yes":
            st.session_state["inputs"]["training"]["include_training"] = True
            # GenAI Constraint: Training implies Self-Hosted Inference
            if st.session_state["inputs"]["project_type"] == "genai":
                st.session_state["inputs"]["inference"]["mode"] = "Self-Hosted"
        else:
            st.session_state["inputs"]["training"]["include_training"] = False

    st.radio(
        "Do you have a Training or Fine-tuning phase?", 
        ["Yes", "No (Inference Only)"], 
        index=0 if inputs_data["training"]["include_training"] else 1, 
        horizontal=True,
        key="train_vis_radio",
        on_change=update_training_visibility
    )

    # Training (Conditional)
    if inputs_data["training"]["include_training"]:
        st.markdown("**🏋️ Training Phase (Runs)**")
        t_c1, t_c2, t_c3, t_c4 = st.columns(4)
        
        # Filter Hardware based on Project Type
        train_hw_opts = get_filtered_hardware(inputs_data["project_type"])
        train_hw_ids = [h["id"] for h in train_hw_opts]
        curr_train_hw = inputs_data["training"]["hardware_id"]
        
        with t_c1:
            st.selectbox("Training Region", list(DEFAULT_GRID_INTENSITY.keys()), index=list(DEFAULT_GRID_INTENSITY.keys()).index(inputs_data["training"]["region"]), key="t_reg", on_change=update_input, args=("training", "region", "t_reg"), help="The geographical location of the datacenter. This determines the carbon intensity of the electricity (gCO2e/kWh).")
            st.selectbox("Training Infra", list(INFRASTRUCTURE_PROFILES.keys()), format_func=lambda x: INFRASTRUCTURE_PROFILES[x]["name"], index=list(INFRASTRUCTURE_PROFILES.keys()).index(inputs_data["training"]["infra_type"]), key="t_infra", on_change=update_input, args=("training", "infra_type", "t_infra"), help="The facility type. Cloud datacenters are typically more energy-efficient (lower PUE) than average on-premise server rooms.")
        with t_c2:
            st.selectbox("Training Hardware", train_hw_ids, format_func=lambda x: next((h["name"] for h in train_hw_opts if h["id"] == x), x), index=train_hw_ids.index(curr_train_hw) if curr_train_hw in train_hw_ids else 0, key="t_hw", on_change=update_input, args=("training", "hardware_id", "t_hw"), help="The GPU/TPU model used. High-end GPUs (e.g., A100) consume more power and have a higher manufacturing footprint.")
            st.number_input("Device Count", value=int(inputs_data["training"]["hardware_count"]), min_value=1, key="t_count", on_change=update_input, args=("training", "hardware_count", "t_count"), help="Number of GPUs running in parallel during a training session.")
        with t_c3:
            st.number_input("Duration per Run (hours)", value=float(inputs_data["training"]["duration_run_hours"]), min_value=0.0, key="t_dur", on_change=update_input, args=("training", "duration_run_hours", "t_dur"), help="Time taken to complete one full training run (in hours).")
        with t_c4:
            st.selectbox("Frequency", ["One-off", "Weekly", "Monthly", "Daily"], index=["One-off", "Weekly", "Monthly", "Daily"].index(inputs_data["training"]["frequency"]), key="t_freq", on_change=update_input, args=("training", "frequency", "t_freq"), help="How often is the model retrained? This multiplies the training impact over the project duration.")

    # --- STEP 3: INFERENCE ---
    st.subheader("3. Inference / Production")

    st.caption(
        "This section describes how the model is used in production. "
        "Depending on the deployment strategy (API-based or self-hosted), the tool applies different "
        "calculation approaches to estimate usage-related energy consumption and emissions. "
        "This phase often represents the main long-term environmental impact of the project."
    )

    # Logic: GenAI can be SaaS or Self-Hosted. ML/DL is always Compute (Self-Hosted logic).
    is_genai = inputs_data["project_type"] == "genai"
    
    if is_genai:
        # Lock to Self-Hosted if Training is active
        is_locked = inputs_data["training"]["include_training"]
        st.radio(
            "Inference Mode", 
            ["SaaS / API", "Self-Hosted"], 
            index=0 if inputs_data["inference"]["mode"] == "SaaS / API" else 1, 
            key="inf_mode", 
            on_change=update_input, 
            args=("inference", "mode", "inf_mode"), 
            disabled=is_locked,
            help="**SaaS/API**: Emissions calculated based on token volume (Black-box).\n**Self-Hosted**: Emissions calculated based on hardware power and active time (White-box)."
        )
        if is_locked:
            st.caption("🔒 Inference is set to **Self-Hosted** because a training phase is included.")

    if is_genai and inputs_data["inference"]["mode"] == "SaaS / API":
        # SaaS Flow
        i_c1, i_c2 = st.columns(2)
        with i_c1:
            curr_model = inputs_data["inference"]["api_model"]
            st.selectbox("GenAI Model", list(API_MODELS.keys()), index=list(API_MODELS.keys()).index(curr_model) if curr_model in API_MODELS else 0, key="inf_model", on_change=update_input, args=("inference", "api_model", "inf_model"), help="The specific model used. Larger models (e.g., GPT-4) require more energy per token than smaller ones (e.g., Haiku).")
            st.number_input("Requests per Day", value=int(inputs_data["inference"]["req_per_day"]), min_value=1, key="inf_reqs", on_change=update_input, args=("inference", "req_per_day", "inf_reqs"), help="Average number of API calls per day.")
        with i_c2:
            st.number_input("Avg Tokens per Request", value=int(inputs_data["inference"]["tokens_per_req"]), key="inf_tokens", on_change=update_input, args=("inference", "tokens_per_req", "inf_tokens"), help="Sum of Input (Prompt) and Output (Completion) tokens. 1k tokens ≈ 750 words.")
    else:
        # Compute Flow (ML/DL or Self-Hosted GenAI)
        i_c1, i_c2, i_c3 = st.columns(3)
        
        # Filter Hardware for Inference
        inf_hw_opts = get_filtered_hardware(inputs_data["project_type"])
        inf_hw_ids = [h["id"] for h in inf_hw_opts]
        curr_inf_hw = inputs_data["inference"]["hardware_id"]

        with i_c1:
            st.selectbox("Inference Region", list(DEFAULT_GRID_INTENSITY.keys()), index=list(DEFAULT_GRID_INTENSITY.keys()).index(inputs_data["inference"]["region"]), key="inf_reg", on_change=update_input, args=("inference", "region", "inf_reg"), help="Location of the production servers. Choosing a low-carbon region (e.g., France, Sweden) is the most effective way to reduce usage emissions.")
            st.selectbox("Inference Infra", list(INFRASTRUCTURE_PROFILES.keys()), format_func=lambda x: INFRASTRUCTURE_PROFILES[x]["name"], index=list(INFRASTRUCTURE_PROFILES.keys()).index(inputs_data["inference"]["infra_type"]), key="inf_infra", on_change=update_input, args=("inference", "infra_type", "inf_infra"), help="Facility efficiency for production.")
        with i_c2:
            st.selectbox("Inference Hardware", inf_hw_ids, format_func=lambda x: next((h["name"] for h in inf_hw_opts if h["id"] == x), x), index=inf_hw_ids.index(curr_inf_hw) if curr_inf_hw in inf_hw_ids else 0, key="inf_hw", on_change=update_input, args=("inference", "hardware_id", "inf_hw"), help="The hardware used to serve requests.")
            st.number_input("Device Count", value=int(inputs_data["inference"]["hardware_count"]), min_value=1, key="inf_cnt", on_change=update_input, args=("inference", "hardware_count", "inf_cnt"), help="Number of GPUs/Servers provisioned for inference.")
        with i_c3:
            st.number_input("Requests per Day", value=int(inputs_data["inference"]["req_per_day"]), min_value=1, key="inf_reqs", on_change=update_input, args=("inference", "req_per_day", "inf_reqs"), help="Daily traffic volume.")
            # Default latency based on type
            default_lat = 100.0 if inputs_data["project_type"] != "genai" else 2000.0
            st.number_input("Avg Latency (ms)", value=float(inputs_data["inference"]["latency_ms"]), min_value=1.0, step=10.0, key="inf_lat", on_change=update_input, args=("inference", "latency_ms", "inf_lat"), help="Average time to process one request. Used to calculate the total 'Active Compute Time' per year.")

    # Storage (Expander)
    with st.expander("💾 Storage & Network (Optional)"):
        if st.checkbox("Include Storage & Network", value=inputs_data["storage_network"]["include_storage_network"], key="sn_include", on_change=update_input, args=("storage_network", "include_storage_network", "sn_include")):
            st.number_input("Dataset Size (GB)", value=float(inputs_data["storage_network"]["dataset_gb"]), key="sn_gb", on_change=update_input, args=("storage_network", "dataset_gb", "sn_gb"), help="Total volume of data stored (Datasets + Models).")
            st.number_input("Data Transfer (GB/day)", value=float(inputs_data["storage_network"]["transfer_gb_per_day"]), key="sn_tr", on_change=update_input, args=("storage_network", "transfer_gb_per_day", "sn_tr"), help="Average daily data transfer (Inbound + Outbound).")

    # --- Results ---
    st.divider()
    st.markdown("<h1 style='text-align:center;'>Results & Analysis</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    try:
        inputs_obj = ProjectInputs(**inputs_data)
        res = compute_footprint(inputs_obj, assumptions)
        score = calculate_score(res)
        
        col_score, col_kpi = st.columns([1, 3])
        with col_score:
                    st.markdown(
                f"""
                <div style="
                    height: 100%;
                    min-height: 300px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    background-color: {score.color}20;
                    border: 2px solid {score.color};
                    border-radius: 12px;
                    padding: 30px;
                    text-align: center;
                ">
                    <h3 style="color: {score.color}; margin:0;">Grade</h3>
                    <h1 style="font-size: 3.5em; margin:0;">{score.grade}</h1>
                    <h2 style="margin:0;">{score.score_100}/100</h2>
                    <p style="margin-top:8px;"><b>{score.label}</b></p>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_kpi:
            k1, k2, k3 = st.columns(3)
            with k1: kpi_card("Total CO₂ (lifecycle)", f"{res.total_co2_kg:,.0f} kg", "All phases combined")
            with k2: kpi_card("Total Energy", f"{res.total_energy_kwh:,.0f} kWh", "Usage energy")
            with k3: kpi_card("Total Water", f"{res.total_water_m3:,.1f} m³", "Cooling + electricity proxy")
            st.markdown("<br>", unsafe_allow_html=True)
            st.divider()
            st.markdown("<br>", unsafe_allow_html=True)
            kpi_card(f"<div style='text-align:center'>Annual CO₂", f"<div style='text-align:center'>{res.annual_co2_kg:.0f} kg/y</div>")

        st.divider()
        st.subheader("Impact Dashboard")

        wf_df = pd.DataFrame({
            "Phase": [
                "Development",
                "Training (Usage)",
                "Training (Embodied)",
                "Inference (Usage)",
                "Inference (Embodied)",
                "Storage & Network"
            ],
            "CO₂ (kg)": [
                res.co2_dev,
                res.co2_training_usage,
                res.co2_training_embodied,
                res.co2_inference_usage,
                res.co2_inference_embodied,
                res.co2_storage_network
            ]
        })

        wf_df = wf_df[wf_df["CO₂ (kg)"] > 0]

        fig_wf = px.bar(
            wf_df,
            x="Phase",
            y="CO₂ (kg)",
            color="Phase",
            title="CO₂ Contribution by Phase"
        )

        fig_wf.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#333333",
            title_font_color="#0b1220",
            showlegend=False
        )

        st.plotly_chart(fig_wf, width="stretch")


        # Executive insight
        impact_by_phase = {
            "Development": res.co2_dev,
            "Training": res.co2_training_usage + res.co2_training_embodied,
            "Inference": res.co2_inference_usage + res.co2_inference_embodied,
            "Storage & Network": res.co2_storage_network
        }

        main_driver = max(impact_by_phase, key=impact_by_phase.get)
        main_value = impact_by_phase[main_driver]
        pct = (main_value / res.total_co2_kg) * 100 if res.total_co2_kg > 0 else 0

        st.info(
            f"🔍 **Key insight** — The main contributor to the environmental footprint is "
            f"**{main_driver}**, representing **{pct:.0f}%** of total CO₂ emissions. "
            f"This phase should be prioritized for optimization."
        )

        st.subheader("🎛️ CO₂ Optimization Levers (What-If Simulator)")
        st.caption(
            "Explore how realistic operational decisions can reduce the carbon footprint. "
            "Sliders allow up to 100% for exploration, but recommended realistic ranges are indicated."
        )

        c1, c2, c3 = st.columns(3)

        # --------------------
        # COLUMN 1 — USAGE
        # --------------------
        with c1:
            token_reduction = st.slider(
                "Reduce tokens per request (%)",
                0, 100, 5, 5,
                help="Typical realistic range: 10–40%. "
                    "Achieved via prompt compression, RAG, output limits."
            )
            if token_reduction > 40 and token_reduction != 100:
                st.warning("⚠️ Above 40% usually requires product redesign or strong constraints.")
            if token_reduction == 100:
                st.error(
                    "❌ **100% token reduction is impossible** — "
                    "it would mean no prompt and no model output. "
                    "This scenario cannot exist in a real project."
                )

            traffic_reduction = st.slider(
                "Reduce daily traffic (%)",
                0, 100, 5, 5,
                help="Typical realistic range: 5–30%. "
                    "Achieved via caching, UX optimization, rate limiting."
            )
            if traffic_reduction > 30:
                st.warning("⚠️ Large traffic reduction may impact business usage or adoption.")

        # --------------------
        # COLUMN 2 — INFRA
        # --------------------
        with c2:
            region_gain = st.slider(
                "Cleaner energy region benefit (%)",
                0, 100, 5, 5,
                help="Typical realistic range: 20–60%. "
                    "Represents moving workloads to lower-carbon electricity regions."
            )
            if region_gain > 60:
                st.warning("⚠️ Above 60% assumes best-in-class low-carbon regions only.")

            pue_improvement = st.slider(
                "Datacenter efficiency improvement (PUE) (%)",
                0, 100, 5, 5,
                help="Typical realistic range: 5–25%. "
                    "Achieved via better cloud providers or more efficient facilities."
            )
            if pue_improvement > 25:
                st.warning("⚠️ High PUE gains are rarely achievable without infrastructure change.")

        # --------------------
        # COLUMN 3 — TRAINING
        # --------------------
        with c3:
            training_freq_reduction = st.slider(
                "Reduce training frequency (%)",
                0, 100, 0, 10,
                help="Typical realistic range: 0–50%. "
                    "Achieved by retraining only when data or performance drifts."
            )
            if training_freq_reduction > 50:
                st.warning("⚠️ Strong reduction may affect model accuracy or freshness.")

        
        # --- WHAT-IF SIMULATION (Calculator layer) ---
        what_if = simulate_what_if(
            res,
            token_reduction_pct=token_reduction,
            traffic_reduction_pct=traffic_reduction,
            region_gain_pct=region_gain,
            pue_improvement_pct=pue_improvement,
            training_freq_reduction_pct=training_freq_reduction,
        )

        sim_df = pd.DataFrame({
            "Scenario": ["Current", "After optimization"],
            "Annual CO₂ (kg)": [
                res.annual_co2_kg,
                what_if["optimized_co2_kg"] / inputs_obj.project_duration_years
            ]
        })

        fig_sim = px.bar(
            sim_df,
            x="Scenario",
            y="Annual CO₂ (kg)",
            color="Scenario",
            text_auto=".2s",
            title="Annual CO₂ Impact — What-If Scenario",
            color_discrete_map={
                "Current": "#7f8c8d",            # gris (baseline)
                "After optimization": "#2ecc71"  # vert (gain)
            }
        )

        fig_sim.update_traces(
            textfont=dict(
                size=20,              # plus lisible mais pas agressif
                color="white",        # contraste propre dans les barres
                family="sans-serif",  # police neutre (proche Power BI)
            ),
            textposition="inside",
            insidetextanchor="middle"
        )


        fig_sim.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#333333",
            title_font_color="#0b1220",
            showlegend=False
        )

        st.plotly_chart(fig_sim, width="stretch")




        

        if st.button("💾 Save Project Result"):
            save_project(inputs_obj, res, score)
            st.success("Project saved to CSV!")

    except ValidationError as e:
        st.error(f"Input Validation Error: {e}")

# --- PAGE: Compare ---
elif page == "Projects":
    st.header("Projects")
    df = load_projects()
    if df.empty:
        st.info("No saved projects yet.")
    else:
        # --- 1. Display Projects (Formatted) ---
        display_df = df.copy()
        
        # Format Date
        if "timestamp" in display_df.columns:
            display_df["timestamp"] = pd.to_datetime(display_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")

        # Rename Columns for readability
        column_map = {
            "project_name": "Project Name",
            "project_type": "Type",
            "environment": "Env",
            "project_duration_years": "Duration (y)",
            "total_co2_kg": "Total CO2 (kg)",
            "total_energy_kwh": "Total Energy (kWh)",
            "total_water_m3": "Total Water (m³)",
            "score_grade": "Grade",
            "score_100": "Score (/100)",
            "timestamp": "Date Created"
        }
        
        # Select and rename columns that exist in the dataframe
        cols_to_show = [c for c in column_map.keys() if c in display_df.columns]
        st.dataframe(display_df[cols_to_show].rename(columns=column_map), width="stretch")

        # --- 2. Comparison Logic ---
        if len(df) >= 2:
            st.divider()
            st.subheader("⚔️ Side-by-Side Comparison")
            projects = df["project_name"].unique()
            c_comp1, c_comp2 = st.columns(2)
            p1 = c_comp1.selectbox("Project A", projects, index=0)
            p2 = c_comp2.selectbox("Project B", projects, index=1 if len(projects) > 1 else 0)
            
            if p1 and p2:
                # Get latest entry for selected projects
                row1 = df[df["project_name"] == p1].iloc[-1]
                row2 = df[df["project_name"] == p2].iloc[-1]
                
                k1, k2, k3 = st.columns(3)
                k1.metric(f"{p1} (CO₂)", f"{row1['total_co2_kg']:.0f} kg")
                k2.metric(f"{p2} (CO₂)", f"{row2['total_co2_kg']:.0f} kg")
                delta = row2['total_co2_kg'] - row1['total_co2_kg']
                k3.metric("Delta (B - A)", f"{delta:+.0f} kg", delta_color="inverse")

        # --- 3. Complex Project Creation ---
        st.divider()
        st.subheader("🧩 Create Complex Project (Aggregation)")
        st.caption("Combine multiple existing projects (e.g., a Training project + an Inference project) into a single aggregated result.")
        
        projects_list = df["project_name"].unique()
        selected_projects = st.multiselect("Select projects to combine", projects_list)
        new_complex_name = st.text_input("New Complex Project Name", value="Combined Project")
        
        if st.button("Merge & Save Complex Project"):
            if len(selected_projects) < 2:
                st.error("Please select at least 2 projects to combine.")
            elif not new_complex_name:
                st.error("Please provide a name for the complex project.")
            else:
                # Filter and Sum
                sub_df = df[df["project_name"].isin(selected_projects)]
                # Columns to sum
                sum_cols = ['total_co2_kg', 'total_energy_kwh', 'total_water_m3', 'co2_dev', 'co2_training_usage', 'co2_training_embodied', 'co2_inference_usage', 'co2_inference_embodied', 'co2_storage_network', 'annual_co2_kg']
                # Ensure columns exist (fill 0 if missing)
                for c in sum_cols:
                    if c not in sub_df.columns: sub_df[c] = 0.0
                
                aggregated = sub_df[sum_cols].sum()
                
                # Recalculate Score
                # We create a dummy FootprintResult with summed values
                fp_agg = FootprintResult(**aggregated.to_dict())
                score_agg = calculate_score(fp_agg)
                
                # Create new row
                new_row = aggregated.to_dict()
                new_row["project_name"] = new_complex_name
                new_row["project_type"] = "Complex / Aggregated"
                new_row["environment"] = "Mixed"
                new_row["score_grade"] = score_agg.grade
                new_row["score_100"] = score_agg.score_100
                new_row["timestamp"] = datetime.now().isoformat()
                
                save_custom_row(new_row)
                st.success(f"Complex project '{new_complex_name}' created successfully!")
                st.rerun()

        # --- 4. Delete Project ---
        st.divider()
        st.subheader("🗑️ Manage Projects")
        p_to_delete = st.selectbox("Select project to delete", projects_list, key="del_sel")
        if st.button("Delete Project", type="secondary"):
            delete_project(p_to_delete)
            st.success(f"Project '{p_to_delete}' deleted.")
            st.rerun()