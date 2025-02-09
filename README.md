# Radio Monitor

Application de surveillance des radios pour la SODAV (Société sénégalaise du droit d'auteur et des droits voisins).

## Fonctionnalités

- Surveillance en temps réel des flux radio
- Détection automatique des morceaux joués
- Interface de visualisation des données
- Génération de rapports
- Analyse des tendances

## Structure du projet

- `frontend/` : Application React/TypeScript avec Chakra UI
- `backend/` : API FastAPI avec détection audio

## Installation

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm start
```

## Configuration

1. Créez un fichier `.env` dans le dossier `backend/` :
```env
AUDD_API_KEY=votre_clé_api
DATABASE_URL=sqlite:///./sodav_monitor.db
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

2. Assurez-vous que les URLs des stations radio sont correctement configurées dans `frontend/src/services/radioBrowser.ts`

## Utilisation

1. Lancez le backend : `python main.py`
2. Lancez le frontend : `npm start`
3. Accédez à l'application via `http://localhost:3000`

## Développement

- Backend : Python 3.8+, FastAPI, SQLAlchemy
- Frontend : React 18, TypeScript, Chakra UI
- Base de données : SQLite

## Licence

Copyright © 2025 LordThiouk. Tous droits réservés.
