# app/models.py
from __future__ import annotations
from datetime import datetime, timezone
from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator
from app.constants import DEFAULT_GRID_INTENSITY, DEFAULT_PUE, DEFAULT_LIFESPAN

# --- Defaults ---
DEFAULT_WATER_M3_PER_MWH = 0.5
DEFAULT_GCO2_PER_100_TOKENS = 0.02
DEFAULT_GCO2_PER_GB_TRANSFER = 5.0
DEFAULT_KWH_PER_GB_YEAR_STORAGE = 1.2e-3

class Assumptions(BaseModel):
    water_m3_per_mwh: float = Field(default=DEFAULT_WATER_M3_PER_MWH, ge=0.0)
    default_gco2_per_100_tokens: float = Field(default=DEFAULT_GCO2_PER_100_TOKENS, ge=0.0)
    default_gco2_per_gb_transfer: float = Field(default=DEFAULT_GCO2_PER_GB_TRANSFER, ge=0.0)
    default_kwh_per_gb_year_storage: float = Field(default=DEFAULT_KWH_PER_GB_YEAR_STORAGE, ge=0.0)
    hardware_lifespan_years: float = Field(default=DEFAULT_LIFESPAN, ge=1.0)
    version: str = Field(default="v2-hybrid")

class TrainingInputs(BaseModel):
    include_training: bool = True
    hardware_model: str = Field(default="NVIDIA A100 (80GB)")
    hardware_count: int = Field(default=8, ge=1)
    train_hours: float = Field(default=100.0, ge=0.0)
    water_m3: float = Field(default=0.0, ge=0.0) # Override manuel

class InferenceInputs(BaseModel):
    include_inference: bool = True
    mode: str = Field(default="SaaS / API") # "SaaS / API" or "Self-Hosted"
    
    # Mode SaaS
    req_per_day: int = Field(default=1000, ge=0)
    tokens_per_req: int = Field(default=1000, ge=0)
    gco2_per_100_tokens: float = Field(default=DEFAULT_GCO2_PER_100_TOKENS, ge=0.0)
    
    # Mode Self-Hosted
    hardware_model: str = Field(default="NVIDIA T4")
    hardware_count: int = Field(default=1, ge=1)
    latency_per_req_s: float = Field(default=0.5, ge=0.0) # Temps de calcul par requête

class InfraInputs(BaseModel):
    region: str = Field(default="EU (avg)")
    grid_intensity_g_per_kwh: float = Field(default=DEFAULT_GRID_INTENSITY["EU (avg)"], ge=0.0)
    pue: float = Field(default=DEFAULT_PUE, ge=1.0)

class StorageNetworkInputs(BaseModel):
    include_storage_network: bool = True
    dataset_gb: float = Field(default=50.0, ge=0.0)
    transfer_gb_per_day: float = Field(default=1.0, ge=0.0)

class ProjectInputs(BaseModel):
    project_name: str = Field(default="New AI Project")
    owner: str = Field(default="Data Team")
    project_duration_years: float = Field(default=2.0, ge=0.1)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    training: TrainingInputs = TrainingInputs()
    inference: InferenceInputs = InferenceInputs()
    infra: InfraInputs = InfraInputs()
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
    co2_training_usage: float; co2_training_embodied: float
    co2_inference_usage: float; co2_inference_embodied: float
    co2_storage_network: float
    water_training: float; water_inference: float
    annual_co2_kg: float