# app/calculator.py
import math
from dataclasses import dataclass
from app.constants import HARDWARE_DICT, INFRASTRUCTURE_PROFILES, HOURS_PER_YEAR, DEFAULT_GRID_INTENSITY, API_MODELS
from app.models import ProjectInputs, Assumptions, FootprintResult

@dataclass
class ScoreResult:
    score_100: int
    grade: str
    color: str
    label: str

def get_hardware_specs(hw_id: str) -> dict:
    return HARDWARE_DICT.get(hw_id, HARDWARE_DICT["laptop_std"])

def compute_footprint(inputs: ProjectInputs, assumptions: Assumptions) -> FootprintResult:
    # --- 1. Common Factors ---
    water_factor = assumptions.water_m3_per_mwh / 1000.0 # m3/MWh -> m3/kWh
    project_years = inputs.project_duration_years
    lifespan = assumptions.hardware_lifespan_years

    # --- A. Development (Exploration) ---
    d_in = inputs.development
    # Use training region for dev or default to local/avg? Using Training Region as proxy for Dev location if not specified
    grid_intensity_dev = DEFAULT_GRID_INTENSITY.get(inputs.training.region, 475.0) / 1000.0
    
    hw_dev = get_hardware_specs(d_in.hardware_id)
    pue_dev = INFRASTRUCTURE_PROFILES[d_in.infra_type]["pue"]
    
    # Energy Dev = Watts * 1 * Hours * PUE
    dev_energy = (hw_dev["watts"] / 1000.0) * 1 * d_in.dev_hours * pue_dev
    dev_co2_usage = dev_energy * grid_intensity_dev
    
    # Embodied Dev: Allocation
    dev_amortization = d_in.dev_hours / (lifespan * HOURS_PER_YEAR)
    dev_co2_embodied = 1 * hw_dev["gwp"] * dev_amortization
    
    total_co2_dev = dev_co2_usage + dev_co2_embodied

    # --- B. Training (Recurring) ---
    train_energy = 0.0
    train_co2_usage = 0.0
    train_co2_embodied = 0.0

    if inputs.training.include_training:
        t_in = inputs.training
        grid_intensity_train = DEFAULT_GRID_INTENSITY.get(t_in.region, 475.0) / 1000.0
        hw_train = get_hardware_specs(t_in.hardware_id)
        pue_train = INFRASTRUCTURE_PROFILES[t_in.infra_type]["pue"]
        
        # Calculate N_runs based on frequency
        if t_in.frequency == "One-off":
            n_runs = 1
        elif t_in.frequency == "Weekly":
            n_runs = 52 * project_years
        elif t_in.frequency == "Monthly":
            n_runs = 12 * project_years
        elif t_in.frequency == "Daily":
            n_runs = 365 * project_years
        else:
            n_runs = 1
            
        total_train_hours = t_in.duration_run_hours * n_runs
        
        # Energy = Watts * Count * PUE * TotalHours
        train_energy = (hw_train["watts"] / 1000.0) * t_in.hardware_count * total_train_hours * pue_train
        train_co2_usage = train_energy * grid_intensity_train
        
        # Embodied: Allocation
        train_amortization = total_train_hours / (lifespan * HOURS_PER_YEAR)
        train_co2_embodied = t_in.hardware_count * hw_train["gwp"] * train_amortization

    # --- C. Inference (Production) ---
    inf_energy_annual = 0.0
    inf_co2_usage_total = 0.0
    inf_co2_embodied_total = 0.0

    if inputs.inference.include_inference:
        i_in = inputs.inference
        grid_intensity_inf = DEFAULT_GRID_INTENSITY.get(i_in.region, 475.0) / 1000.0
        
        # Logic: GenAI API vs Compute (Self-Hosted OR ML/DL)
        is_genai_api = (inputs.project_type == "genai" and i_in.mode == "SaaS / API")
        
        if is_genai_api:
            annual_reqs = i_in.req_per_day * 365
            model_factor = API_MODELS.get(i_in.api_model, 0.02)
            annual_gco2 = annual_reqs * i_in.tokens_per_req * (model_factor / 1000.0) # per 1k tokens
            inf_co2_usage_total = (annual_gco2 / 1000.0) * project_years
        else:
            # Compute Mode (ML Classic, DL, Self-Hosted GenAI)
            hw_inf = get_hardware_specs(i_in.hardware_id)
            pue_inf = INFRASTRUCTURE_PROFILES[i_in.infra_type]["pue"]
            
            # Active Time
            t_active_annual = (i_in.req_per_day * (i_in.latency_ms / 1000.0) / 3600.0) * 365.0
            
            # Total Time (Billed/Powered)
            if i_in.server_24_7:
                t_total_annual = HOURS_PER_YEAR
            else:
                t_total_annual = t_active_annual
            
            inf_energy_annual = (hw_inf["watts"] / 1000.0) * i_in.hardware_count * t_total_annual * pue_inf
            inf_co2_usage_total = inf_energy_annual * grid_intensity_inf * project_years
            
            # Embodied: Allocation based on Total Time
            inf_amortization = (t_total_annual * project_years) / (lifespan * HOURS_PER_YEAR)
            inf_co2_embodied_total = i_in.hardware_count * hw_inf["gwp"] * inf_amortization

    # --- D. Storage & Network ---
    sn_co2_total = 0.0
    sn_energy_annual = 0.0
    
    if inputs.storage_network.include_storage_network:
        sn_in = inputs.storage_network
        grid_intensity_avg = DEFAULT_GRID_INTENSITY.get("World Average", 475.0) / 1000.0
        # Assume Cloud PUE for storage
        storage_kwh_year = sn_in.dataset_gb * assumptions.default_kwh_per_gb_year_storage * 1.2
        transfer_gco2_year = sn_in.transfer_gb_per_day * 365 * assumptions.default_gco2_per_gb_transfer
        
        sn_energy_annual = storage_kwh_year
        sn_co2_total = (storage_kwh_year * grid_intensity_avg * project_years) + ((transfer_gco2_year / 1000.0) * project_years)

    # --- Totals ---
    total_co2 = total_co2_dev + train_co2_usage + train_co2_embodied + inf_co2_usage_total + inf_co2_embodied_total + sn_co2_total
    total_energy = train_energy + (inf_energy_annual * project_years) + (sn_energy_annual * project_years)
    total_water = total_energy * water_factor
    annual_co2 = total_co2 / max(0.1, project_years)

    return FootprintResult(
        total_co2_kg=total_co2, total_energy_kwh=total_energy, total_water_m3=total_water,
        co2_dev=total_co2_dev,
        co2_training_usage=train_co2_usage, co2_training_embodied=train_co2_embodied,
        co2_inference_usage=inf_co2_usage_total, co2_inference_embodied=inf_co2_embodied_total,
        co2_storage_network=sn_co2_total,
        annual_co2_kg=annual_co2
    )

def calculate_score(fp: FootprintResult) -> ScoreResult:
    co2_val = max(1.0, fp.total_co2_kg)
    co2_score = max(0, min(100, 100 - (math.log10(co2_val) * 20)))
    
    water_val = max(0.1, fp.total_water_m3)
    water_score = max(0, min(100, 100 - (math.log10(water_val * 10) * 20)))
    
    final_score = int(0.7 * co2_score + 0.3 * water_score)
    
    impact = fp.total_co2_kg
    if impact <= 50: grade, color, label = "A", "#2ecc71", "Excellent"
    elif impact <= 250: grade, color, label = "B", "#27ae60", "Very Good"
    elif impact <= 1000: grade, color, label = "C", "#f1c40f", "Good"
    elif impact <= 5000: grade, color, label = "D", "#e67e22", "Average"
    elif impact <= 20000: grade, color, label = "E", "#d35400", "Poor"
    elif impact <= 100000: grade, color, label = "F", "#c0392b", "Very Poor"
    else: grade, color, label = "G", "#8e44ad", "Critical"
    
    return ScoreResult(final_score, grade, color, label)


def simulate_what_if(
    fp: FootprintResult,
    *,
    token_reduction_pct: float = 0.0,
    traffic_reduction_pct: float = 0.0,
    region_gain_pct: float = 0.0,
    pue_improvement_pct: float = 0.0,
    training_freq_reduction_pct: float = 0.0,
) -> dict:
    """
    Simulate CO₂ reduction using realistic operational levers.
    Percentages are expected between 0 and 100.
    """

    baseline = fp.total_co2_kg
    co2_after = baseline

    # --- Inference usage levers ---
    inference_usage = fp.co2_inference_usage

    co2_after -= inference_usage * (token_reduction_pct / 100)
    co2_after -= inference_usage * (traffic_reduction_pct / 100)

    # --- Infrastructure levers (usage-based only) ---
    infra_usage = (
        fp.co2_training_usage +
        fp.co2_inference_usage +
        fp.co2_storage_network
    )

    co2_after -= infra_usage * (region_gain_pct / 100)
    co2_after -= infra_usage * (pue_improvement_pct / 100)

    # --- Training frequency lever ---
    co2_after -= fp.co2_training_usage * (training_freq_reduction_pct / 100)

    co2_after = max(0.0, co2_after)

    return {
        "baseline_co2_kg": baseline,
        "optimized_co2_kg": co2_after,
        "absolute_reduction_kg": baseline - co2_after,
        "relative_reduction_pct": (
            (baseline - co2_after) / baseline * 100
            if baseline > 0 else 0
        ),
    }
