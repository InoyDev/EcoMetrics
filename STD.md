
# SPÉCIFICATIONS TECHNIQUES : SOLUTION ECO-SCORE IA

- **Projet :** Simulateur d'impact écologique pour projets IA (Outil d'aide à la décision GO / NO-GO)
- **Version :** 1.0
- **Date :** Janvier 2026

## 1. VISION & OBJECTIFS

Développer une application web interactive permettant d'estimer l'empreinte carbone (kgCO₂e) d'un projet d'IA sur l'ensemble de son cycle de vie.

### Objectifs principaux :

- **Notation intuitive :** Fournir un classement de A à G (type Nutri-Score) pour une lecture immédiate par les décideurs.
- **Précision scientifique :** Fournir un calcul détaillé (Fabrication vs Usage) basé sur l'Analyse de Cycle de Vie (ACV).
- **Simulation agile :** Permettre, via un tableau de bord, de modifier des paramètres (région, matériel, durée) afin de visualiser l'amélioration du score en temps réel.

## 2. MODÈLE DE DONNÉES (CONSTANTES & RÉFÉRENCES)

Ces données constituent la base du moteur de calcul. Elles doivent être stockées dans un fichier JSON ou une base de données.

### 2.1 Hypothèses et valeurs par défaut

| Constante | Valeur | Description |
|---|---|---|
| `DEFAULT_PUE_CLOUD` | 1.2 | Efficacité énergétique moyenne des hyperscalers |
| `DEFAULT_PUE_ONPREM` | 1.6 | Efficacité énergétique moyenne datacenter entreprise |
| `DEFAULT_CI_WORLD` | 475 gCO₂/kWh | Intensité carbone moyenne mondiale |
| `DEFAULT_LIFESPAN_HARDWARE` | 4 ans | Durée de vie moyenne d'un serveur |
| `DEFAULT_PROJECT_YEARS` | 2 ans | Durée de vie moyenne d'un projet IA |
| `HOURS_PER_YEAR` | 8760 | Nombre d'heures dans une année |

### 2.2 Base de données matériel (GPU / CPU)

```json
{
  "hardware_list": [
    { "id": "h100", "name": "NVIDIA H100", "tdp_watts": 700, "gwp_fabrication_kg": 2500 },
    { "id": "a100", "name": "NVIDIA A100", "tdp_watts": 400, "gwp_fabrication_kg": 1500 },
    { "id": "t4", "name": "NVIDIA T4", "tdp_watts": 70, "gwp_fabrication_kg": 200 },
    { "id": "rtx4090", "name": "Consumer RTX 4090", "tdp_watts": 450, "gwp_fabrication_kg": 250 },
    { "id": "cpu_server", "name": "CPU Server Standard", "tdp_watts": 200, "gwp_fabrication_kg": 800 }
  ]
}
```

### 2.3 Base de données géographique (intensité carbone)

```json
{
  "regions": [
    { "id": "fr", "name": "France", "ci_factor": 52 },
    { "id": "us", "name": "USA (Moyenne)", "ci_factor": 367 },
    { "id": "de", "name": "Allemagne", "ci_factor": 350 },
    { "id": "se", "name": "Suède", "ci_factor": 45 },
    { "id": "cn", "name": "Chine", "ci_factor": 550 },
    { "id": "world", "name": "Moyenne mondiale", "ci_factor": 475 }
  ]
}
```

## 3. SCÉNARIO UTILISATEUR & QUESTIONNAIRE

Le formulaire est conditionnel et n'affiche que les questions nécessaires.

### Phase 1 — Profil du projet

**Q1. Nature du projet**

- A — Utilisation d'une API (OpenAI, Claude…) → Entraînement masqué
- B — Inférence pure (modèle pré‑entraîné) → Entraînement masqué
- C — Fine‑tuning / ré‑entraînement → Entraînement activé
- D — Entraînement complet (from scratch) → Entraînement activé

**Q2. Durée de vie estimée du projet**
- Nombre d'années (défaut : 2)

### Phase 2 — Entraînement (si C ou D)

**Q3. Région d'entraînement**
- Liste déroulante (pays)

**Q4. Matériel utilisé**
- Liste ou Autre / Je ne sais pas
- Consommation (W) — défaut : 400 W
- Nombre de puces

**Q5. Durée de l'entraînement**
- Heures totales de calcul

### Phase 3 — Inférence & production (obligatoire)

**Q6. Région d'hébergement (production)**

**Q7. Matériel en production**

**Q8. Trafic estimé**
- Requêtes / jour
- Temps par requête (s)
  - Texte : 0.2 s
  - LLM chat : 2 s
  - Image : 4 s

## 4. ALGORITHME DE CALCUL

### 4.1 Variables normalisées

- **PUE :** efficacité datacenter
- **CI :** intensité carbone (gCO₂/kWh)
- **W_gpu :** puissance GPU (W)
- **N_gpu :** nombre de GPU
- **GWP_unit :** empreinte fabrication unitaire (kgCO₂e)

### 4.2 Formules

#### Impact entraînement

```
# Énergie consommée (kWh)
E_training_kWh = (W_gpu * N_gpu * T_training_hours * PUE) / 1000

# Impact usage (kgCO₂e)
Usage_training_kgCO2e = E_training_kWh * (CI / 1000)

# Impact fabrication (kgCO₂e)
Fab_training_kgCO2e = N_gpu * GWP_unit * (T_training_hours / (DEFAULT_LIFESPAN_HARDWARE * HOURS_PER_YEAR))

# Total
Impact_training_kgCO2e = Usage_training_kgCO2e + Fab_training_kgCO2e
```

#### Impact inférence

```
# Temps de calcul total sur la durée du projet (heures)
T_inference_hours = (Requests_per_day * Time_per_request_s / 3600) * 365 * DEFAULT_PROJECT_YEARS

# Énergie consommée (kWh)
E_inference_kWh = (W_gpu * N_gpu * T_inference_hours * PUE) / 1000

# Impact usage (kgCO₂e)
Usage_inference_kgCO2e = E_inference_kWh * (CI / 1000)

# Impact fabrication (kgCO₂e)
Fab_inference_kgCO2e = N_gpu * GWP_unit * ( (DEFAULT_PROJECT_YEARS * HOURS_PER_YEAR) / (DEFAULT_LIFESPAN_HARDWARE * HOURS_PER_YEAR) )

# Total
Impact_inference_kgCO2e = Usage_inference_kgCO2e + Fab_inference_kgCO2e
```

## 5. SYSTÈME DE NOTATION

| Grade | Couleur | Impact total | Référence |
|---|---|---|---|
| A | Vert foncé | 0 – 50 kg | Ampoule / an |
| B | Vert clair | 50 – 250 kg | Paris–Marseille (TGV) |
| C | Jaune | 250 kg – 1 t | Smartphone |
| D | Orange | 1 – 5 t | Paris–New York |
| E | Orange foncé | 5 – 20 t | Voiture |
| F | Rouge | 20 – 100 t | 20 Français / an |
| G | Bordeaux | > 100 t | Industriel |

## 6. DASHBOARD & SIMULATION

- **Visualisation**
  - Jauge de score
  - Donut de répartition
- **Simulation What‑If**
  - Région serveur
  - Durée de vie du projet
  - Mode optimisé (−30 % GPU, −20 % latence)

## 7. MOTEUR DE RECOMMANDATIONS

- **Électricité carbonée :** CI > 200 → changer de région
- **Matériel surdimensionné :** Fabrication > usage → réduire le hardware
- **Explosion de l'inférence :** Inférence > 10× entraînement → optimisation, cache, distillation
