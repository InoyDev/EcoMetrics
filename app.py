import streamlit as st

# --- DONNÉES DE RÉFÉRENCE (STD 2.1, 2.2, 2.3) ---

CONSTANTS = {
    "DEFAULT_PUE_CLOUD": 1.2,
    "DEFAULT_LIFESPAN_HARDWARE": 4,  # ans
    "HOURS_PER_YEAR": 8760
}

HARDWARE_DATA = {
    "h100": {"name": "NVIDIA H100", "tdp_watts": 700, "gwp_fabrication_kg": 2500},
    "a100": {"name": "NVIDIA A100", "tdp_watts": 400, "gwp_fabrication_kg": 1500},
    "t4": {"name": "NVIDIA T4", "tdp_watts": 70, "gwp_fabrication_kg": 200},
    "rtx4090": {"name": "Consumer RTX 4090", "tdp_watts": 450, "gwp_fabrication_kg": 250},
    "cpu_server": {"name": "CPU Server Standard", "tdp_watts": 200, "gwp_fabrication_kg": 800},
    "other": {"name": "Other / I don't know", "tdp_watts": 400, "gwp_fabrication_kg": 1000}
}

REGIONS_DATA = {
    "fr": {"name": "France", "ci_factor": 52},
    "us": {"name": "USA (Average)", "ci_factor": 367},
    "de": {"name": "Germany", "ci_factor": 350},
    "se": {"name": "Sweden", "ci_factor": 45},
    "cn": {"name": "China", "ci_factor": 550},
    "world": {"name": "World Average", "ci_factor": 475}
}

# --- FONCTIONS UTILITAIRES ---

def get_score_grade(impact_kg):
    if impact_kg <= 50: return "A", "🟢 Excellent"
    elif impact_kg <= 250: return "B", "🟢 Very Good"
    elif impact_kg <= 1000: return "C", "🟡 Good"
    elif impact_kg <= 5000: return "D", "🟠 Medium"
    elif impact_kg <= 20000: return "E", "🟠 Poor"
    elif impact_kg <= 100000: return "F", "🔴 Very Poor"
    else: return "G", "🔴 Critical"

# --- INTERFACE STREAMLIT ---

st.set_page_config(page_title="AI Eco-Score", page_icon="🌱", layout="centered")

st.title("🌱 AI Eco-Score Simulator")
st.markdown("Decision support tool to estimate the carbon footprint of your AI projects.")

# Phase 1 : Profil
st.header("Phase 1 — Project Profile")
col1, col2 = st.columns(2)

project_type_options = {
    "A": "A — Using an API (OpenAI, Claude...)",
    "B": "B — Pure Inference (Pre-trained model)",
    "C": "C — Fine-tuning / Retraining",
    "D": "D — Full Training (from scratch)"
}
project_type = col1.selectbox("Q1. Project Nature", options=list(project_type_options.keys()), format_func=lambda x: project_type_options[x])
project_years = col2.number_input("Q2. Project Lifespan (years)", min_value=0.1, value=2.0, step=0.1)

# Phase 2 : Entraînement (Conditionnel)
impact_training = 0
if project_type in ["C", "D"]:
    st.header("Phase 2 — Training")
    c1, c2 = st.columns(2)
    train_region_key = c1.selectbox("Q3. Training Region", options=list(REGIONS_DATA.keys()), format_func=lambda x: REGIONS_DATA[x]["name"])
    train_hw_key = c2.selectbox("Q4. Hardware Used", options=list(HARDWARE_DATA.keys()), format_func=lambda x: HARDWARE_DATA[x]["name"])
    
    c3, c4, c5 = st.columns(3)
    # Valeurs par défaut dynamiques selon le hardware choisi
    default_watts = HARDWARE_DATA[train_hw_key]["tdp_watts"]
    train_power = c3.number_input("Power per unit (W)", value=default_watts)
    train_count = c4.number_input("Number of chips", min_value=1, value=1)
    train_hours = c5.number_input("Q5. Duration (Hours)", min_value=0, value=10)

    # Calculs Entraînement
    train_region = REGIONS_DATA[train_region_key]
    train_hw = HARDWARE_DATA[train_hw_key]
    
    # Énergie (kWh) = (W * N * h * PUE) / 1000
    e_train_kwh = (train_power * train_count * train_hours * CONSTANTS["DEFAULT_PUE_CLOUD"]) / 1000
    # Usage (kgCO2e)
    usage_train = e_train_kwh * (train_region["ci_factor"] / 1000)
    # Fabrication (kgCO2e) = N * GWP * (h / (Lifespan * 8760))
    fab_train = train_count * train_hw["gwp_fabrication_kg"] * (train_hours / (CONSTANTS["DEFAULT_LIFESPAN_HARDWARE"] * CONSTANTS["HOURS_PER_YEAR"]))
    
    impact_training = usage_train + fab_train

# Phase 3 : Inférence
st.header("Phase 3 — Inference & Production")
c1, c2 = st.columns(2)
inf_region_key = c1.selectbox("Q6. Hosting Region", options=list(REGIONS_DATA.keys()), format_func=lambda x: REGIONS_DATA[x]["name"])
inf_hw_key = c2.selectbox("Q7. Production Hardware", options=list(HARDWARE_DATA.keys()), format_func=lambda x: HARDWARE_DATA[x]["name"])

c3, c4, c5 = st.columns(3)
default_inf_watts = HARDWARE_DATA[inf_hw_key]["tdp_watts"]
inf_power = c3.number_input("Power per unit (W) ", value=default_inf_watts, key="inf_w")
inf_count = c4.number_input("Number of chips ", min_value=1, value=1, key="inf_n")

st.subheader("Q8. Estimated Traffic")
tc1, tc2 = st.columns(2)
req_per_day = tc1.number_input("Requests / day", min_value=0, value=1000)
time_per_req = tc2.number_input("Time per request (s)", min_value=0.01, value=0.2, step=0.01, help="Text: 0.2s | LLM: 2s | Image: 4s")

# Calculs Inférence
inf_region = REGIONS_DATA[inf_region_key]
inf_hw = HARDWARE_DATA[inf_hw_key]

# Temps total inférence (heures) sur la durée du projet
total_inf_hours = (req_per_day * time_per_req / 3600) * 365 * project_years

# Énergie (kWh)
e_inf_kwh = (inf_power * inf_count * total_inf_hours * CONSTANTS["DEFAULT_PUE_CLOUD"]) / 1000
# Usage (kgCO2e)
usage_inf = e_inf_kwh * (inf_region["ci_factor"] / 1000)
# Fabrication (kgCO2e) = N * GWP * (DuréeProjet / DuréeVieMatériel)
fab_inf = inf_count * inf_hw["gwp_fabrication_kg"] * (project_years / CONSTANTS["DEFAULT_LIFESPAN_HARDWARE"])

impact_inference = usage_inf + fab_inf

# --- RÉSULTATS ---

if st.button("Calculate Eco-Score", type="primary"):
    st.markdown("---")
    total_impact = impact_training + impact_inference
    grade, label = get_score_grade(total_impact)
    
    st.header(f"Result: Grade {grade}")
    st.subheader(label)
    
    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("Total Impact", f"{total_impact:.1f} kgCO₂e")
    col_res2.metric("Training", f"{impact_training:.1f} kgCO₂e")
    col_res3.metric("Inference", f"{impact_inference:.1f} kgCO₂e")
    
    # Détails
    st.markdown("### Footprint Details")
    
    # Données pour le graphique
    data = {
        "Phase": ["Training (Usage)", "Training (Fab)", "Inference (Usage)", "Inference (Fab)"],
        "kgCO2e": [
            usage_train if 'usage_train' in locals() else 0,
            fab_train if 'fab_train' in locals() else 0,
            usage_inf,
            fab_inf
        ]
    }
    st.bar_chart(data, x="Phase", y="kgCO2e")

    # Recommandations basiques
    st.markdown("### 💡 Recommendations")
    if inf_region["ci_factor"] > 200:
        st.warning(f"Carbon intensity in {inf_region['name']} is high ({inf_region['ci_factor']} g/kWh). Consider hosting your model in Sweden or France.")
    
    if fab_inf > usage_inf * 2:
        st.warning("Manufacturing impact is very high compared to usage. Check if you haven't oversized the hardware (too many GPUs for low traffic).")
        
    if impact_inference > 10 * impact_training and impact_training > 0:
        st.info("Inference largely dominates the carbon footprint. Consider optimizing the model (quantization, distillation) or using caching.")