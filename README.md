# 🌱 EcoMetrics — AI Project Lifecycle Assessment

EcoMetrics est un outil d'aide à la décision permettant d'estimer l'empreinte carbone et hydrique des projets d'IA sur l'ensemble de leur cycle de vie (Fabrication + Usage).

## 🚀 Installation

1. **Cloner le projet** et naviguer dans le dossier :
   ```bash
   cd EcoMetrics
   ```

2. **Créer un environnement virtuel** (recommandé) :
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Sur Mac/Linux
   # .venv\Scripts\activate   # Sur Windows
   ```

3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

## ▶️ Lancement

Lancer l'application Streamlit :
```bash
streamlit run app/main.py
```

## 📂 Structure

- `app/`: Code source de l'application.
- `data/`: Stockage local des projets et hypothèses.
- `old/`: Archives de l'ancien POC (référence).
- `STD.md`: Documentation technique et méthodologie de calcul.