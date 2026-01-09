# EcoMetrics

Ecological impact simulator for AI projects (GO / NO-GO decision tool).

## Installation

Follow these steps to set up the development environment.

### 1. Clone the repository

```bash
git clone <REPO_URL>
cd EcoMetrics
```

### 2. Créer et activer l'environnement virtuel

- **macOS / Linux**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- **Windows**
  ```bash
  python -m venv .venv
  .\.venv\Scripts\activate
  ```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Créez un fichier `.env` en copiant l'exemple.

```bash
cp .env.example .env
```

### 5. Lancer l'application

```bash
streamlit run app.py
```

L'application sera accessible à l'adresse `http://127.0.0.1:5000`.