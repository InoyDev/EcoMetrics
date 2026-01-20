# app/utils.py
import pandas as pd
from pathlib import Path
from datetime import datetime
from app.models import ProjectInputs, FootprintResult
from app.calculator import ScoreResult

# Paths relative to the project root (assuming run from root)
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_CSV = DATA_DIR / "projects.csv"

def load_projects() -> pd.DataFrame:
    if PROJECTS_CSV.exists():
        return pd.read_csv(PROJECTS_CSV)
    return pd.DataFrame()

def save_project(inputs: ProjectInputs, fp: FootprintResult, score: ScoreResult):
    df = load_projects()
    row = inputs.model_dump()
    
    # Flatten nested dicts
    flat_row = {}
    for k, v in row.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                flat_row[f"{k}_{sub_k}"] = sub_v
        else:
            flat_row[k] = v
            
    flat_row.update({"total_co2_kg": fp.total_co2_kg, "total_water_m3": fp.total_water_m3, "score_grade": score.grade, "score_100": score.score_100, "timestamp": datetime.now().isoformat()})
    
    df = pd.concat([df, pd.DataFrame([flat_row])], ignore_index=True)
    df.to_csv(PROJECTS_CSV, index=False)