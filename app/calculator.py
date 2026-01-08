# Ce fichier contiendra la logique de calcul de l'éco-score.

# Constantes (à charger depuis un fichier de config ou .env)
DEFAULT_PUE_CLOUD = 1.2
DEFAULT_PUE_ONPREM = 1.6
DEFAULT_CI_WORLD = 475  # gCO₂/kWh
DEFAULT_LIFESPAN_HARDWARE = 4  # ans
DEFAULT_PROJECT_YEARS = 2  # ans
HOURS_PER_YEAR = 8760

def calculate_training_impact(w_gpu, n_gpu, t_training_hours, pue, ci, gwp_unit):
    """
    Calcule l'impact carbone de la phase d'entraînement.
    """
    # Énergie consommée (kWh)
    e_training_kWh = (w_gpu * n_gpu * t_training_hours * pue) / 1000

    # Impact usage (kgCO₂e)
    usage_training_kgCO2e = e_training_kWh * (ci / 1000)

    # Impact fabrication (kgCO₂e)
    fab_training_kgCO2e = n_gpu * gwp_unit * (t_training_hours / (DEFAULT_LIFESPAN_HARDWARE * HOURS_PER_YEAR))

    # Total
    impact_training_kgCO2e = usage_training_kgCO2e + fab_training_kgCO2e
    return impact_training_kgCO2e

def calculate_inference_impact(w_gpu, n_gpu, requests_per_day, time_per_request_s, project_years, pue, ci, gwp_unit):
    """
    Calcule l'impact carbone de la phase d'inférence.
    """
    # Temps de calcul total sur la durée du projet (heures)
    t_inference_hours = (requests_per_day * time_per_request_s / 3600) * 365 * project_years

    # Énergie consommée (kWh)
    e_inference_kWh = (w_gpu * n_gpu * t_inference_hours * pue) / 1000

    # Impact usage (kgCO₂e)
    usage_inference_kgCO2e = e_inference_kWh * (ci / 1000)

    # Impact fabrication (kgCO₂e)
    amortization_factor = project_years / DEFAULT_LIFESPAN_HARDWARE
    fab_inference_kgCO2e = n_gpu * gwp_unit * amortization_factor

    # Total
    impact_inference_kgCO2e = usage_inference_kgCO2e + fab_inference_kgCO2e
    return impact_inference_kgCO2e