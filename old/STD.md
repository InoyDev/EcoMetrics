
# SPÉCIFICATIONS TECHNIQUES DÉTAILLÉES (STD) — EcoMetrics

- **Projet :** EcoMetrics — Calculateur d'Empreinte Carbone & Eau pour Projets IA
- **Version :** 2.1 (Détail complet des paramètres et calculs)
- **Date :** Janvier 2026
- **Statut :** Validé pour implémentation

## 1. OBJECTIFS DU SYSTÈME

L'outil a pour but de fournir une estimation "Cradle-to-Grave" (du berceau à la tombe) de l'impact environnemental d'un projet d'Intelligence Artificielle. Il couvre les phases de fabrication du matériel (Scope 3 amont), l'usage électrique (Scope 2) et la consommation d'eau.

Il gère trois archétypes de projets :
1.  **GenAI API (SaaS) :** Consommation basée sur les tokens (ex: GPT-4).
2.  **Self-Hosted Inference :** Hébergement sur serveurs dédiés ou cloud (ex: Llama 3 sur AWS).
3.  **Fine-Tuning / Training :** Entraînement de modèles spécifiques + Inférence.

## 2. PARAMÈTRES UTILISATEUR (INPUTS)

L'interface utilisateur permet de définir les variables suivantes.

### 2.1 Contexte Général
| Variable | Description | Type | Valeur par défaut |
|---|---|---|---|
| `Project Name` | Identifiant du projet | Texte | "New AI Project" |
| `Project Type` | Archétype déterminant les sections visibles | Liste | "GenAI API (SaaS)" |
| `Duration` | Durée d'exploitation du projet (pour l'amortissement) | Float (Années) | 2.0 ans |

### 2.2 Phase Entraînement (Si applicable)
| Variable | Description | Unité | Valeur par défaut |
|---|---|---|---|
| `Training Region` | Lieu du datacenter d'entraînement | Liste (Pays) | "EU (avg)" |
| `Hardware Model` | Type de GPU/TPU utilisé | Liste (Ref) | "NVIDIA A100 (80GB)" |
| `GPU Count` | Nombre de cartes utilisées en parallèle | Entier | 8 |
| `Training Hours` | Durée d'un cycle d'entraînement complet | Heures | 100.0 |
| `Experimentation Factor` | Nombre d'essais (échecs, grid search) pour 1 succès | Entier | 1 (Pas d'erreur) |

### 2.3 Phase Inférence (Production)

**Configuration RAG (Optionnel)**
| Variable | Description | Unité | Valeur par défaut |
|---|---|---|---|
| `Enable RAG` | Active le surcoût de récupération de contexte | Booléen | False |
| `Chunks Retrieved` | Nombre de documents insérés dans le prompt | Entier | 3 |
| `Chunk Size` | Taille moyenne d'un document récupéré | Tokens | 512 |

**Mode A : SaaS / API**
| Variable | Description | Unité | Valeur par défaut |
|---|---|---|---|
| `GenAI Model` | Modèle utilisé (facteur d'émission spécifique) | Liste | "GPT-3.5 Turbo" |
| `Requests per Day` | Volume quotidien moyen | Entier | 1000 |
| `Avg Tokens per Req` | Somme (Prompt + Génération) par requête | Entier | 1000 |

**Mode B : Self-Hosted**
| Variable | Description | Unité | Valeur par défaut |
|---|---|---|---|
| `Inference Region` | Lieu d'hébergement (souvent proche utilisateur) | Liste | "EU (avg)" |
| `Hardware Model` | Type de GPU d'inférence | Liste | "NVIDIA T4" |
| `GPU Count` | Nombre de cartes dédiées | Entier | 1 |
| `Latency` | Temps de traitement moyen par requête | Secondes | 0.5 |

### 2.4 Stockage & Réseau (Optionnel)
| Variable | Description | Unité | Valeur par défaut |
|---|---|---|---|
| `Dataset Size` | Volume de données stockées (chaud) | GB | 50.0 |
| `Data Transfer` | Volume transféré (In + Out) quotidien | GB/jour | 1.0 |

## 3. DONNÉES DE RÉFÉRENCE (CONSTANTES)

Ces valeurs sont définies dans le système (`app/constants.py`) mais modifiables dans les paramètres avancés.

### 3.1 Hypothèses Globales
| Constante | Valeur | Description |
|---|---|---|
| `DEFAULT_PUE` | **1.2** | Power Usage Effectiveness (Standard Cloud Efficient) |
| `HARDWARE_LIFESPAN` | **4.0 ans** | Durée d'amortissement comptable/physique |
| `HOURS_PER_YEAR` | **8760** | 24h * 365j |
| `WATER_INTENSITY` | **0.5 m³/MWh** | Moyenne mondiale (Scope 2 Water) |

### 3.2 Facteurs d'Émission API (Estimations Recherche)
| Modèle | Facteur (gCO₂e / 1000 tokens) |
|---|---|
| GPT-3.5 Turbo / Haiku | 0.008 |
| Llama 3 70B (SaaS) | 0.04 |
| Mistral Large | 0.06 |
| GPT-4 / Opus / Ultra | 0.12 |
| Embedding (Ada v2) | 0.001 |

### 3.3 Matériel de Référence (Extraits)
| Modèle | TDP (Watts) | GWP Fabrication (kgCO₂e) |
|---|---|---|
| NVIDIA H100 | 700 | 2500 |
| NVIDIA A100 | 400 | 1500 |
| NVIDIA T4 | 70 | 200 |
| CPU Server | 200 | 800 |

## 4. LOGIQUE DE CALCUL

### 4.1 Phase Entraînement

L'impact prend en compte la répétition des entraînements (essais/erreurs).

1.  **Temps Total (h)** = `Training_Hours` × `Experimentation_Factor`
2.  **Énergie (kWh)** = (`TDP_kW` × `GPU_Count` × `Temps Total` × `PUE`)
3.  **CO₂ Usage (kg)** = `Énergie` × `Grid_Intensity_Train`
4.  **CO₂ Fabrication (kg)** = `GPU_Count` × `GWP_Unit` × (`Temps Total` / (`LIFESPAN` × 8760))
    *Note : On amortit la fabrication au prorata du temps d'utilisation réel des GPU.*

### 4.2 Phase Inférence

#### Cas A : Mode SaaS / API
Le calcul est basé sur une estimation par token (proxy de la complexité de calcul).

1.  **Tokens par Requête** = `Avg_Tokens` + (Si RAG: `Chunks` × `Chunk_Size`)
2.  **Volume Annuel** = `Requests_Day` × 365 × `Tokens par Requête`
3.  **CO₂ Annuel (kg)** = (`Volume Annuel` / 1000) × `API_Emission_Factor`
4.  **Total Projet** = `CO₂ Annuel` × `Duration_Years`

#### Cas B : Mode Self-Hosted
Le calcul est basé sur le temps d'occupation machine.

1.  **Temps Calcul Annuel (h)** = (`Requests_Day` × `Latency_Sec` / 3600) × 365
2.  **Énergie Annuelle (kWh)** = `TDP_kW` × `GPU_Count` × `Temps Calcul Annuel` × `PUE`
3.  **CO₂ Usage Total (kg)** = `Énergie Annuelle` × `Grid_Intensity_Inf` × `Duration_Years`
4.  **CO₂ Fabrication Total (kg)** = `GPU_Count` × `GWP_Unit` × (`Duration_Years` / `LIFESPAN`)
    *Note : Ici, on amortit sur la durée du projet (réservation de capacité), plafonné à 100% du matériel.*

### 4.3 Stockage & Réseau

1.  **Énergie Stockage (kWh)** = `Dataset_GB` × 0.0012 (kWh/GB/an) × `PUE` × `Duration_Years`
2.  **CO₂ Stockage** = `Énergie Stockage` × `Grid_Intensity_World` (Moyenne globale par défaut)
3.  **CO₂ Réseau** = `Transfer_GB_Day` × 365 × `Duration_Years` × 0.005 (kgCO₂/GB)

### 4.4 Eau (Water Footprint)

Calculé sur le Scope 2 (Eau nécessaire à la production électrique et au refroidissement).
**Total Eau (m³)** = `Total Énergie (MWh)` × `WATER_INTENSITY (m³/MWh)`

## 5. RÉSULTATS & KPIs

### 5.1 Indicateurs Principaux
- **Total CO₂ (kg)** : Somme de toutes les phases.
- **Total Énergie (kWh)** : Consommation électrique cumulée.
- **Total Eau (m³)** : Consommation d'eau cumulée.
- **Impact Annuel (kgCO₂/an)** : Total / Durée du projet.

### 5.2 Score Écologique
Note de A à G calculée par une formule logarithmique pondérée :
- **Score CO₂ (0-100)** : `100 - 20 * log10(Total_CO2)`
- **Score Eau (0-100)** : `100 - 20 * log10(Total_Water * 10)`
- **Score Final** : `0.7 * Score_CO2 + 0.3 * Score_Eau`

| Grade | Impact CO₂ (kg) | Référence |
|---|---|---|
| **A** | < 50 | Ampoule / an |
| **B** | < 250 | TGV Paris-Marseille |
| **C** | < 1,000 | Smartphone |
| **D** | < 5,000 | Vol Paris-NY |
| **E** | < 20,000 | Voiture thermique / an |
| **F** | < 100,000 | PME |
| **G** | > 100,000 | Industriel |

## 6. ARCHITECTURE TECHNIQUE
- **Langage :** Python 3.10+
- **Interface :** Streamlit
- **Données :** Fichiers JSON (pas de BDD SQL pour la portabilité)
- **Visualisation :** Plotly Express
