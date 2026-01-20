# TECHNICAL DESIGN DOCUMENT (TDD) — EcoMetrics

**Project:** EcoMetrics — AI Project Lifecycle Assessment Tool
**Version:** 2.0 (Hybrid MVP/STD)
**Date:** January 2026

## 1. VISION & PHILOSOPHY

EcoMetrics is a decision-support tool designed to estimate the environmental footprint (Carbon & Water) of Artificial Intelligence projects throughout their entire lifecycle.

This version combines the fluid user experience of a consultant MVP with the methodological rigor of a scientific Life Cycle Assessment (LCA).

### Key Principles:
- **Lifecycle Approach (LCA):** We systematically integrate the manufacturing footprint (Scope 3 Upstream) amortized over the usage duration, in addition to electricity consumption (Scope 2).
- **Hybrid Inference:** Clear distinction between "SaaS/API" mode (token-based calculation) and "Self-Hosted" mode (physical machine time + hardware calculation).
- **Multi-criteria Scoring:** A composite score (CO₂ + Water) normalized on a logarithmic scale to handle the vast orders of magnitude in AI.

## 2. DATA MODEL & CONSTANTS

The calculation engine relies on physical constants and reference databases stored in JSON files (`app/data/`).

### 2.1 Global Assumptions

| Parameter | Default Value | Description |
|---|---|---|
| **PUE (Power Usage Effectiveness)** | 1.2 | Efficiency ratio of the datacenter (Total Energy / IT Energy). 1.2 represents efficient Hyperscalers. |
| **Server Lifespan** | 4 years | Standard accounting and physical lifespan of IT hardware. Used for amortization. |
| **Water Intensity** | 0.5 m³/MWh | Average water consumption (evaporation) for electricity generation and cooling. |

### 2.2 Hardware Database

Each hardware component is defined by its power consumption under load and its manufacturing carbon footprint.

| Model | TDP (kW) | Manufacturing GWP (kgCO₂e) |
|---|---|---|
| NVIDIA H100 | 0.70 | 2500 |
| NVIDIA A100 (80GB) | 0.40 | 1500 |
| NVIDIA T4 | 0.07 | 200 |
| CPU Server Std | 0.20 | 800 |

### 2.3 Grid Intensity

Carbon intensity of electricity depends on the selected region.

| Region | Intensity (gCO₂e/kWh) |
|---|---|
| France (FR) | 52 |
| USA (Average) | 367 |
| World (Average) | 475 |

## 3. CALCULATION ALGORITHMS

### 3.1 Phase 1: Training (One-shot)

This phase calculates the impact of training or fine-tuning a model.

**Formulas:**
1.  **Energy (kWh):**
    $$ E_{train} = P_{device} \times N_{devices} \times Hours \times PUE $$
2.  **Carbon Usage (Scope 2):**
    $$ CO2_{usage} = E_{train} \times I_{grid} $$
3.  **Carbon Embodied (Scope 3):**
    Amortized based on the actual usage time vs. total lifespan.
    $$ CO2_{embodied} = N_{devices} \times GWP_{device} \times \frac{Hours}{Lifespan_{years} \times 8760} $$
4.  **Water Footprint:**
    $$ Water = E_{train} \times I_{water} $$

### 3.2 Phase 2: Inference (Recurring)

This phase calculates the impact of running the model in production over the **Project Duration**.

#### Mode A: SaaS / API (Proxy Token)
Used when the underlying hardware is unknown (e.g., GPT-4 API).
$$ CO2_{total} = N_{req/year} \times N_{tokens/req} \times F_{emission\_token} \times Duration_{years} $$
*Note: The token emission factor is an assumption implicitly including usage and manufacturing.*

#### Mode B: Self-Hosted (Physical)
Used when the infrastructure is controlled.
1.  **Annual Compute Time:**
    $$ T_{annual} (h) = \frac{N_{req/day} \times Latency_{sec}}{3600} \times 365 $$
2.  **Energy (kWh):**
    $$ E_{inf} = P_{device} \times N_{devices} \times T_{annual} \times PUE $$
3.  **Carbon Embodied (Scope 3):**
    Amortized over the project duration.
    $$ Ratio = \min(1.0, \frac{ProjectDuration}{Lifespan}) $$
    $$ CO2_{embodied} = N_{devices} \times GWP_{device} \times Ratio $$

### 3.3 Phase 3: Storage & Network

- **Storage:** Based on volume (GB) and annual energy factor.
  $$ E_{storage} = Volume_{GB} \times kWh/GB/Year \times PUE $$
- **Network:** Based on data transfer volume and carbon intensity of data transmission.
  $$ CO2_{network} = Transfer_{GB/day} \times 365 \times Factor_{gCO2/GB} $$

## 4. SCORING SYSTEM

The score provides an immediate visual indicator (0-100) and a standard grade (A-G).

### 4.1 Logarithmic Normalization
Since AI projects vary from kilograms to tons of CO₂, a linear scale is unsuitable.
$$ Score_{CO2} = 100 - (20 \times \log_{10}(Impact_{kg})) $$
*Calibration: 100kg ≈ 80/100, 10t ≈ 40/100*

### 4.2 Aggregation
$$ Score_{Final} = 70\% \times Score_{CO2} + 30\% \times Score_{Water} $$

### 4.3 Grading Scale (Absolute Thresholds)
The letter grade is determined solely by the total Carbon impact to ensure alignment with climate goals.

| Grade | Total Impact (kgCO₂e) | Reference |
|---|---|---|
| **A** | < 50 kg | Light bulb / year |
| **B** | < 250 kg | Train trip (Medium) |
| **C** | < 1,000 kg | Smartphone lifecycle |
| **D** | < 5,000 kg | Transatlantic flight |
| **E** | < 20,000 kg | Car / year |
| **F** | < 100,000 kg | Small company |
| **G** | > 100,000 kg | Industrial scale |