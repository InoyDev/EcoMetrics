# app/calculator.py
import math
from dataclasses import dataclass
from app.constants import HARDWARE_DATA, HOURS_PER_YEAR
from app.models import ProjectInputs, Assumptions, FootprintResult

@dataclass
class ScoreResult:
    score_100: int
    grade: str
    color: str
    label: str

def get_hardware_specs(model_name: str) -> dict:
    return HARDWARE_DATA.get(model_name, HARDWARE_DATA["Other / Unknown"])

def compute_footprint(inputs: ProjectInputs, assumptions: Assumptions) -> FootprintResult:
    # --- 1. Common Factors ---
    grid_intensity = inputs.infra.grid_intensity_g_per_kwh / 1000.0 # g -> kg
    pue = inputs.infra.pue
    water_factor = assumptions.water_m3_per_mwh / 1000.0 # m3/MWh -> m3/kWh
    project_years = inputs.project_duration_years
    lifespan = assumptions.hardware_lifespan_years

    # --- 2. Training (One-shot) ---
    train_energy = 0.0
    train_co2_usage = 0.0
    train_co2_embodied = 0.0
    train_water = 0.0

    if inputs.training.include_training:
        t_in = inputs.training
        hw = get_hardware_specs(t_in.hardware_model)
        
        # Usage: Power * Count * Hours * PUE
        train_energy = hw["tdp_kw"] * t_in.hardware_count * t_in.train_hours * pue
        train_co2_usage = train_energy * grid_intensity
        
        # Embodied: Amortissement sur la durée d'utilisation réelle
        total_lifespan_hours = lifespan * HOURS_PER_YEAR
        amortization_ratio = t_in.train_hours / total_lifespan_hours
        train_co2_embodied = t_in.hardware_count * hw["gwp_kg"] * amortization_ratio
        
        # Water
        if t_in.water_m3 > 0:
            train_water = t_in.water_m3
        else:
            train_water = train_energy * water_factor

    # --- 3. Inference (Recurring) ---
    inf_energy_annual = 0.0
    inf_co2_usage_total = 0.0
    inf_co2_embodied_total = 0.0
    inf_water_total = 0.0

    if inputs.inference.include_inference:
        i_in = inputs.inference
        
        if i_in.mode == "SaaS / API":
            annual_reqs = i_in.req_per_day * 365
            annual_gco2 = annual_reqs * i_in.tokens_per_req * (i_in.gco2_per_100_tokens / 100.0)
            inf_co2_usage_total = (annual_gco2 / 1000.0) * project_years
            
            # Estimation énergie inverse pour l'eau (Back-calculation approximative)
            est_kwh_annual = annual_reqs * i_in.tokens_per_req * 0.0003
            inf_water_total = est_kwh_annual * water_factor * project_years

        else:
            hw = get_hardware_specs(i_in.hardware_model)
            daily_seconds = i_in.req_per_day * i_in.latency_per_req_s
            annual_hours = (daily_seconds / 3600.0) * 365.0
            
            inf_energy_annual = hw["tdp_kw"] * i_in.hardware_count * annual_hours * pue
            inf_co2_usage_total = inf_energy_annual * grid_intensity * project_years
            
            amortization_ratio = min(1.0, project_years / lifespan)
            inf_co2_embodied_total = i_in.hardware_count * hw["gwp_kg"] * amortization_ratio
            inf_water_total = (inf_energy_annual * project_years) * water_factor

    # --- 4. Storage & Network (Recurring) ---
    sn_co2_total = 0.0
    sn_energy_annual = 0.0
    
    if inputs.storage_network.include_storage_network:
        sn_in = inputs.storage_network
        storage_kwh_year = sn_in.dataset_gb * assumptions.default_kwh_per_gb_year_storage * pue
        transfer_gco2_year = sn_in.transfer_gb_per_day * 365 * assumptions.default_gco2_per_gb_transfer
        
        sn_energy_annual = storage_kwh_year
        sn_co2_total = (storage_kwh_year * grid_intensity * project_years) + ((transfer_gco2_year / 1000.0) * project_years)

    # --- Totals ---
    total_co2 = train_co2_usage + train_co2_embodied + inf_co2_usage_total + inf_co2_embodied_total + sn_co2_total
    total_water = train_water + inf_water_total
    total_energy = train_energy + (inf_energy_annual * project_years) + (sn_energy_annual * project_years)
    annual_co2 = total_co2 / max(0.1, project_years)

    return FootprintResult(
        total_co2_kg=total_co2, total_energy_kwh=total_energy, total_water_m3=total_water,
        co2_training_usage=train_co2_usage, co2_training_embodied=train_co2_embodied,
        co2_inference_usage=inf_co2_usage_total, co2_inference_embodied=inf_co2_embodied_total,
        co2_storage_network=sn_co2_total, water_training=train_water, water_inference=inf_water_total,
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
    elif impact <= 250: grade, color, label = "B", "#27ae60", "Très Bon"
    elif impact <= 1000: grade, color, label = "C", "#f1c40f", "Bon"
    elif impact <= 5000: grade, color, label = "D", "#e67e22", "Moyen"
    elif impact <= 20000: grade, color, label = "E", "#d35400", "Médiocre"
    elif impact <= 100000: grade, color, label = "F", "#c0392b", "Mauvais"
    else: grade, color, label = "G", "#8e44ad", "Critique"
    
    return ScoreResult(final_score, grade, color, label)