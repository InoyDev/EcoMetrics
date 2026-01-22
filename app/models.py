# app/models.py
from __future__ import annotations
from datetime import datetime, timezone
from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator
from app.constants import DEFAULT_GRID_INTENSITY, DEFAULT_LIFESPAN, API_MODELS

# --- Defaults ---
DEFAULT_WATER_M3_PER_MWH = 0.5
DEFAULT_GCO2_PER_100_TOKENS = 0.02
DEFAULT_GCO2_PER_GB_TRANSFER = 5.0
DEFAULT_KWH_PER_GB_YEAR_STORAGE = 1.2e-3

class Assumptions(BaseModel):
    api_energy_kwh_per_query: float = Field(default=0.0003, ge=0.0)  # 0.3 Wh / query
    water_m3_per_mwh: float = Field(default=DEFAULT_WATER_M3_PER_MWH, ge=0.0)
    default_gco2_per_100_tokens: float = Field(default=DEFAULT_GCO2_PER_100_TOKENS, ge=0.0)
    default_gco2_per_gb_transfer: float = Field(default=DEFAULT_GCO2_PER_GB_TRANSFER, ge=0.0)
    default_kwh_per_gb_year_storage: float = Field(default=DEFAULT_KWH_PER_GB_YEAR_STORAGE, ge=0.0)
    hardware_lifespan_years: float = Field(default=DEFAULT_LIFESPAN, ge=1.0)
    version: str = Field(default="v2-hybrid")

class DevelopmentInputs(BaseModel):
    infra_type: str = Field(default="local") # local, cloud, on_prem
    hardware_id: str = Field(default="laptop_std")
    dev_hours: float = Field(default=50.0, ge=0.0)

class TrainingInputs(BaseModel):
    include_training: bool = True
    region: str = Field(default="EU (avg)")
    infra_type: str = Field(default="cloud")
    hardware_id: str = Field(default="gpu_a100")
    hardware_count: int = Field(default=8, ge=1)
    duration_run_hours: float = Field(default=10.0, ge=0.0)
    frequency: str = Field(default="One-off") # One-off, Weekly, Monthly, Daily

class InferenceInputs(BaseModel):
    include_inference: bool = True
    region: str = Field(default="EU (avg)")
    mode: str = Field(default="SaaS / API") # "SaaS / API" or "Self-Hosted" (Compute)
    
    # Compute Mode (ML/DL/Self-Hosted)
    infra_type: str = Field(default="cloud")
    hardware_id: str = Field(default="gpu_t4")
    hardware_count: int = Field(default=1, ge=1)
    server_24_7: bool = Field(default=True) # Is server always on?
    latency_ms: float = Field(default=100.0, ge=0.0)

    # Mode SaaS
    api_model: str = Field(default="GPT-3.5 Turbo / Haiku / Flash")
    req_per_day: int = Field(default=1500, ge=0)
    tokens_per_req: int = Field(default=1500, ge=0)

class StorageNetworkInputs(BaseModel):
    include_storage_network: bool = True
    dataset_gb: float = Field(default=50.0, ge=0.0)
    transfer_gb_per_day: float = Field(default=1.0, ge=0.0)

class ProjectInputs(BaseModel):
    project_name: str = Field(default="New AI Project")
    owner: str = Field(default="Data Team")
    project_type: str = Field(default="genai") # ml_classic, deep_learning, genai
    environment: str = Field(default="Production") # Dev/PoC, Production
    project_duration_years: float = Field(default=2.0, ge=0.1)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    development: DevelopmentInputs = DevelopmentInputs()
    training: TrainingInputs = TrainingInputs()
    inference: InferenceInputs = InferenceInputs()
    storage_network: StorageNetworkInputs = StorageNetworkInputs()

    @field_validator("project_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        return v.strip() or "Unnamed Project"

@dataclass
class FootprintResult:
    total_co2_kg: float
    total_energy_kwh: float
    total_water_m3: float
    co2_dev: float
    co2_training_usage: float; co2_training_embodied: float
    co2_inference_usage: float; co2_inference_embodied: float
    co2_storage_network: float
    annual_co2_kg: float