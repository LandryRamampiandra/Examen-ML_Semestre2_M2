# Intégration Front / Back

Courte documentation pour lancer le frontend et le backend en développement.

Prérequis
- Python 3.9+ (ou 3.10+ recommandé)
- Node 18+ et npm

Backend (Windows PowerShell)

```powershell
cd Back
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Backend (Linux / macOS)

```bash
cd Back
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend

```bash
cd Front
npm install
npm run dev
```

Notes
- Le frontend utilise l'env `VITE_API_URL` (défini dans `Front/.env.development`) qui pointe par défaut sur `http://localhost:8000`.
- L'API FastAPI expose la doc Swagger à `http://localhost:8000/docs`.

Script pratique (Windows PowerShell)

Un petit script `start-dev.ps1` est fourni à la racine pour démarrer backend et frontend dans de nouvelles fenêtres PowerShell :

```powershell
.\start-dev.ps1
```

Test rapide (curl)

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"t1","texte":"Mot de passe oublié","utilisateur_id":"u1","horodatage":"2026-01-01T12:00:00"}'
```

Si vous voulez, je peux :
- ajouter un `docker-compose` pour lancer les deux services ensemble
- ajouter un script npm racine utilisant `concurrently` pour Windows/macOS
- configurer un proxy Vite (si vous préférez appels relatifs au lieu de `VITE_API_URL`)
