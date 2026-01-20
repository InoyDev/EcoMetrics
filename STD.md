# SPÉCIFICATIONS TECHNIQUES DÉTAILLÉES (STD) — EcoMetrics Hybride

**Version :** 2.0 (Hybride MVP/STD)
**Date :** Janvier 2026

## 1. Philosophie de la Solution

Cette version combine l'expérience utilisateur fluide du MVP avec la rigueur méthodologique du STD initial.

- **Approche Cycle de Vie (LCA) :** Nous intégrons systématiquement l'empreinte de fabrication (Scope 3 amont) amortie sur la durée d'usage, en plus de la consommation électrique (Scope 2).
- **Dualité Inférence :** Distinction claire entre le mode "SaaS/API" (calcul par token) et le mode "Self-Hosted" (calcul physique temps machine + matériel).
- **Scoring Multicritère :** Un score composite (CO₂ + Eau) normalisé sur une échelle logarithmique pour gérer les ordres de grandeur très variés de l'IA.

## 2. Modèle de Données

### 2.1 Constantes Physiques

| Paramètre | Valeur par défaut | Source / Justification |
|---|---|---|
| **PUE (Power Usage Effectiveness)** | 1.2 | Moyenne Cloud efficient (Hyperscalers) |
| **Durée de vie Serveur** | 4 ans | Standard comptable et physique IT |
| **Facteur Eau** | 0.5 m³/MWh | Moyenne consommation eau (directe + indirecte) pour refroidissement |

### 2.2 Base de Données Matériel (Unifiée)

Chaque équipement est défini par sa puissance en charge (TDP) et son empreinte carbone de fabrication (GWP - Global Warming Potential).

| Modèle | TDP (kW) | GWP Fabrication (kgCO₂e) |
|---|---|---|
| NVIDIA H100 | 0.70 | 2500 |
| NVIDIA A100 (80GB) | 0.40 | 1500 |
| NVIDIA T4 | 0.07 | 200 |
| CPU Server Std | 0.20 | 800 |

## 3. Algorithmes de Calcul

### 3.1 Phase Entraînement (Training)

Calcul "One-shot".

$$ E_{train} (kWh) = P_{device} \times N_{devices} \times Hours \times PUE $$
$$ CO2_{usage} = E_{train} \times I_{grid} $$
$$ CO2_{fab} = N_{devices} \times GWP_{device} \times \frac{Hours}{Lifespan_{hours}} $$

### 3.2 Phase Inférence (Production)

Calcul annualisé, projeté sur la durée du projet.

**Mode A : SaaS / API (Proxy Token)**
Approche simplifiée quand le matériel est inconnu (ex: GPT-4).
$$ CO2_{total} = N_{req/an} \times N_{tokens/req} \times F_{emission\_token} $$
*Note : Le facteur d'émission par token est une hypothèse incluant implicitement usage et fabrication.*

**Mode B : Self-Hosted (Physique)**
Approche rigoureuse quand l'infrastructure est maîtrisée.
1. Calcul du temps machine annuel nécessaire :
$$ T_{annual} (h) = \frac{N_{req/jour} \times Latency_{sec}}{3600} \times 365 $$
2. Calcul énergétique et fabrication (amortissement) identique au training, mais sur la durée du projet.

### 3.3 Stockage & Réseau

- **Stockage :** Basé sur le volume (GB) et un facteur énergétique annuel (kWh/GB/an).
- **Réseau :** Basé sur le volume transféré (GB) et l'intensité carbone du réseau (gCO₂/GB).

## 4. Système de Notation (Scoring)

Le score est une note de 0 à 100, convertie en lettre (A-G).

1. **Normalisation Logarithmique :**
   Comme un projet peut émettre 100kg ou 1000t de CO₂, une échelle linéaire est impossible.
   $$ Score_{CO2} = 100 - (20 \times \log_{10}(Impact_{kg})) $$
   *Calibrage : 100kg ≈ 80/100 (A), 10t ≈ 40/100 (D)*

2. **Agrégation :**
   $$ Score_{Final} = 70\% \times Score_{CO2} + 30\% \times Score_{Eau} $$

3. **Grade (Lettre) :**
   Basé sur des seuils absolus alignés avec les objectifs climatiques (ex: < 50kg = A).