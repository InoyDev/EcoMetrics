# TECHNICAL DESIGN DOCUMENT (TDD) — EcoMetrics

**Project:** EcoMetrics — Universal AI Carbon Footprint Calculator
**Version:** 3.0 (Universal & Aggregation)
**Date:** January 2026
**Status:** Implemented

## 1. SYSTEM OBJECTIVES

EcoMetrics is a decision-support tool designed to estimate the environmental footprint (Carbon & Water) of Data Science and AI projects throughout their entire lifecycle ("Cradle-to-Grave").

**Version 3.0** expands the scope from GenAI to a **Universal Calculator** covering:
1.  **Classic Machine Learning:** Low compute, CPU-bound (e.g., XGBoost, Scikit-learn).
2.  **Deep Learning:** High compute, GPU-bound training (e.g., Computer Vision, NLP).
3.  **GenAI:** Large Language Models (SaaS API or Self-Hosted).

It also introduces **Complex Project Aggregation** to combine multiple components (e.g., RAG pipeline = Embedding Model + Vector DB + LLM).

## 2. USER PARAMETERS (INPUTS)

The interface is adaptive based on the "Project Type" and "Expert Mode".

### 2.1 Global Profile
| Variable | Description | Type | Default |
|---|---|---|---|
| `Project Name` | Unique identifier | Text | "New AI Project" |
| `Environment` | Context (Dev/PoC vs Production) | List | "Production" |
| `Project Type` | Archetype (Classic ML, DL, GenAI) | List | "GenAI" |
| `Duration` | Project exploitation duration (years) | Float | 2.0 |

### 2.2 Phase 0: Development (Exploration)
*New in V3.0: Accounts for the "human" phase of coding and testing.*

| Variable | Description | Unit | Default |
|---|---|---|---|
| `Dev Infra` | Environment (Local, Cloud, On-Prem) | List | "Local" |
| `Dev Hardware` | Workstation type (Laptop, Workstation) | List | "Laptop Std" |
| `Dev Hours` | Total time spent coding/testing | Hours | 50.0 |

### 2.3 Phase 1: Training (Conditional)
*Visible only if "Include Training" is checked (via Pivot Question).*

| Variable | Description | Unit | Default |
|---|---|---|---|
| `Region` | Datacenter location | List | "EU (avg)" |
| `Infra Profile` | Facility type (Cloud/On-Prem) | List | "Cloud" |
| `Hardware` | GPU/TPU Model | List | "A100" |
| `Count` | Number of devices | Int | 8 |
| `Duration` | Time per single run | Hours | 10.0 |
| `Frequency` | Repetition (One-off, Weekly, Daily...) | List | "One-off" |

### 2.4 Phase 2: Inference (Production)

**Mode A: GenAI SaaS (API)**
| Variable | Description | Unit | Default |
|---|---|---|---|
| `Model` | Target API Model (e.g., GPT-4) | List | "GPT-3.5" |
| `Volume` | Requests per day | Int | 1000 |
| `Tokens` | Avg tokens per request (In + Out) | Int | 1000 |

**Mode B: Compute (Self-Hosted / ML / DL)**
| Variable | Description | Unit | Default |
|---|---|---|---|
| `Region` | Hosting location | List | "EU (avg)" |
| `Hardware` | Inference Device | List | "T4" |
| `Count` | Number of devices | Int | 1 |
| `Server 24/7` | Is hardware reserved/on all the time? | Bool | False |
| `Volume` | Requests per day | Int | 1000 |
| `Latency` | Processing time per request | ms | 100 |

### 2.5 Storage (Optional)
| Variable | Description | Unit | Default |
|---|---|---|---|
| `Dataset` | Storage volume | GB | 50.0 |
| `Transfer` | Network traffic | GB/day | 1.0 |

## 3. REFERENCE DATA (CONSTANTS)

### 3.1 Infrastructure Profiles
| Profile | PUE | Description |
|---|---|---|
| **Local** | 1.0 | Laptops/Workstations (No cooling overhead calculated here). |
| **Cloud** | 1.2 | Efficient Hyperscalers. |
| **On-Prem** | 1.6 | Standard Enterprise Datacenter. |

### 3.2 Hardware Catalog (Extract)
| ID | Name | Type | Power (W) | GWP (kgCO₂e) |
|---|---|---|---|---|
| `laptop_std` | Laptop Standard | CPU | 30 | 250 |
| `server_cpu` | Server CPU | CPU | 200 | 800 |
| `gpu_t4` | NVIDIA T4 | GPU | 70 | 200 |
| `gpu_a100` | NVIDIA A100 | GPU | 400 | 1500 |

## 4. CALCULATION LOGIC

### 4.1 Development Impact
$$ E_{dev} = P_{device} \times 1 \times Hours_{dev} \times PUE_{local} $$
$$ CO2_{dev} = E_{dev} \times I_{grid} + (GWP \times \frac{Hours_{dev}}{Lifespan \times 8760}) $$

### 4.2 Training Impact (Recurring)
1.  **Total Hours:**
    $$ H_{total} = Duration_{run} \times N_{runs} $$
    *(Where $N_{runs}$ depends on Frequency & Project Duration)*
2.  **Energy:**
    $$ E_{train} = P_{device} \times Count \times H_{total} \times PUE $$
3.  **Embodied:**
    $$ CO2_{emb} = Count \times GWP \times \frac{H_{total}}{Lifespan \times 8760} $$

### 4.3 Inference Impact

**Case A: SaaS (Token-based)**
$$ CO2_{usage} = Vol_{annual} \times Tokens \times Factor_{model} $$

**Case B: Compute (Time-based)**
1.  **Active Time (h/year):**
    $$ T_{active} = \frac{Req_{day} \times Latency_{sec}}{3600} \times 365 $$
2.  **Billed Time (h/year):**
    - If `Server 24/7` is True: $8760$
    - Else: $T_{active}$
3.  **Energy:**
    $$ E_{inf} = P_{device} \times Count \times T_{billed} \times PUE $$
4.  **Embodied:**
    $$ CO2_{emb} = Count \times GWP \times \frac{T_{billed} \times Duration_{years}}{Lifespan \times 8760} $$

## 5. FEATURES & WORKFLOW

### 5.1 Expert Mode
- **Standard:** Hides complex options (Training for SaaS, detailed params).
- **Expert:** Reveals all toggles, allowing hybrid configurations (e.g., SaaS + Fine-tuning).

### 5.2 Complex Project Aggregation
Allows combining multiple saved projects into one.
- **Use Case:** A RAG pipeline consisting of:
    1.  *Project A:* Vector DB Hosting (Storage/Compute).
    2.  *Project B:* Embedding Model (Inference).
    3.  *Project C:* LLM Generation (SaaS API).
- **Logic:** Sums CO₂, Energy, and Water. Recalculates the global Score.

### 5.3 Comparison & Management
- Side-by-side comparison of KPIs.
- Ability to delete projects from the local database (`projects.csv`).

## 6. SCORING SYSTEM

| Grade | Impact CO₂ (kg) | Reference |
|---|---|---|
| **A** | < 50 | Light bulb / year |
| **B** | < 250 | Train trip |
| **C** | < 1,000 | Smartphone |
| **D** | < 5,000 | Flight |
| **E** | < 20,000 | Car / year |
| **F** | < 100,000 | SME |
| **G** | > 100,000 | Industrial |

## 7. TECHNICAL STACK
- **Frontend:** Streamlit
- **Logic:** Python (Pydantic Models)
- **Data:** JSON (Constants) + CSV (Persistence)
- **Viz:** Plotly Express