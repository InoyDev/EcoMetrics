# app/constants.py
import json
from pathlib import Path

# Relative paths definition
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

def load_json_data(filename: str, default: dict) -> dict:
    """Loads a JSON file from app/data/ or returns default."""
    file_path = DATA_DIR / filename
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

# --- V3.0 UNIVERSAL DATA ---

PROJECT_TYPES = {
    "ml_classic": "🏛️ Classic Machine Learning (XGBoost, Sklearn)",
    "deep_learning": "🧠 Deep Learning (Vision, NLP, Custom Models)",
    "genai": "🤖 GenAI & LLM (GPT, Llama, RAG)"
}

INFRASTRUCTURE_PROFILES = {
    "local": { "name": "Local Workstation / Laptop", "pue": 1.0 },
    "cloud": { "name": "Cloud Instance (AWS/Azure/GCP)", "pue": 1.2 },
    "on_prem": { "name": "On-Premise Datacenter", "pue": 1.6 },
    "cloud_serverless": { "name": "Cloud Serverless (Scale-to-Zero)", "pue": 1.2 }
}

HARDWARE_CATALOG = [
    { "id": "laptop_std", "name": "Laptop Standard (i7/M1)", "type": "cpu", "watts": 30, "gwp": 250 },
    { "id": "laptop_pro", "name": "Laptop Pro (M3 Max/RTX Mobile)", "type": "gpu", "watts": 60, "gwp": 350 },
    { "id": "server_cpu", "name": "CPU Server (Ex: AWS m5.xlarge)", "type": "cpu", "watts": 200, "gwp": 800 },
    { "id": "gpu_t4", "name": "NVIDIA T4 (Inference)", "type": "gpu", "watts": 70, "gwp": 200 },
    { "id": "gpu_a100", "name": "NVIDIA A100 (Training)", "type": "gpu", "watts": 400, "gwp": 1500 },
    { "id": "gpu_h100", "name": "NVIDIA H100 (HPC)", "type": "gpu", "watts": 700, "gwp": 2500 }
]

# Helper for lookups
HARDWARE_DICT = {hw["id"]: hw for hw in HARDWARE_CATALOG}

# Region Data
DEFAULT_GRID_INTENSITY = load_json_data("regions.json", {})

# --- Constants ---
DEFAULT_LIFESPAN = 4.0      # Server lifespan (years) (STD)
HOURS_PER_YEAR = 8760

# gCO2e estimations per 1000 tokens (Source: Research & Hardware Benchmarks)
API_MODELS = {
    "GPT-3.5 Turbo / Haiku / Flash": 0.008,  # Light / optimized models
    "GPT-4 / Opus / Ultra": 0.12,            # Massive models (MoE)
    "Llama 3 70B (SaaS)": 0.04,              # Hosted open-weight model
    "Mistral Large": 0.06,
    "Embedding (Ada v2 / Cohere)": 0.001     # Very light
}