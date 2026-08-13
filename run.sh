#!/bin/bash
# Crée l'environnement virtuel si besoin, installe les dépendances, lance l'API et le dashboard.
set -e

if [ ! -d "venv" ]; then
  echo "Création de l'environnement virtuel..."
  python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt --quiet

echo "Démarrage de l'API sur http://localhost:8000 ..."
uvicorn main:app --reload --port 8000 &
API_PID=$!

echo "Démarrage du dashboard sur http://localhost:8501 ..."
streamlit run dashboard.py --server.port 8501 &
DASH_PID=$!

trap "kill $API_PID $DASH_PID" EXIT
wait
