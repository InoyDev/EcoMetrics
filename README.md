# EcoMetrics

Simulateur d'impact écologique pour projets IA (Outil d'aide à la décision GO / NO-GO).

## Installation

Suivez ces étapes pour mettre en place l'environnement de développement.

### 1. Cloner le dépôt

```bash
git clone <URL_DU_DEPOT>
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
flask run
```

L'application sera accessible à l'adresse `http://127.0.0.1:5000`.