"""
Outils (simulés) que l'agent peut appeler. Chaque fonction :
- valide ses paramètres,
- renvoie un dict "resultat",
- lève ValueError si les paramètres sont invalides (capté par agent.py).

Outils sensibles (nécessitent validation humaine) : creer_ticket, mettre_a_jour_ticket,
affecter_ticket, escalader_vers_technicien -> gérés dans agent.py, pas ici.
"""

import json
from pathlib import Path
import db

DATA_DIR = Path(__file__).parent / "data"


def _load(nom_fichier: str) -> list[dict]:
    path = DATA_DIR / nom_fichier
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


# --- Outils de consultation (jamais sensibles, exécution directe autorisée) ---

def rechercher_utilisateur(utilisateur_id: str) -> dict:
    utilisateurs = _load("utilisateurs.json")
    for u in utilisateurs:
        if u["utilisateur_id"] == utilisateur_id:
            return u
    return {"trouve": False}


def consulter_equipement(equipement_id: str) -> dict:
    equipements = _load("equipements.json")
    for e in equipements:
        if e["equipement_id"] == equipement_id:
            return e
    return {"trouve": False}


def verifier_etat_service(service: str) -> dict:
    services = _load("services.json")
    for s in services:
        if s["nom"].lower() == service.lower():
            return s
    return {"trouve": False, "statut": "inconnu"}


def rechercher_incidents_actifs(categorie: str | None = None) -> dict:
    incidents = _load("incidents_actifs.json")
    if categorie:
        incidents = [i for i in incidents if i.get("categorie") == categorie]
    return {"incidents": incidents, "nombre": len(incidents)}


# --- Outils d'action (sensibles — passent par la validation humaine dans agent.py) ---
# Le ticket lui-même est déjà créé dans la table `tickets` (db.save_ticket, appelé dans
# main.py à la réception). Ces outils modifient son statut en base.

def creer_ticket(payload: dict) -> dict:
    return {"cree": True, "ticket_id": payload.get("ticket_id")}


def mettre_a_jour_ticket(ticket_id: str, updates: dict) -> dict:
    statut = updates.get("statut", "mis_a_jour")
    db.update_ticket_statut(ticket_id, statut=statut, equipe=updates.get("equipe"))
    return {"mis_a_jour": True, "ticket_id": ticket_id, "updates": updates}


def affecter_ticket(ticket_id: str, equipe: str) -> dict:
    db.update_ticket_statut(ticket_id, statut="affecte", equipe=equipe)
    return {"affecte": True, "ticket_id": ticket_id, "equipe": equipe}


def escalader_vers_technicien(ticket_id: str, motif: str) -> dict:
    db.update_ticket_statut(ticket_id, statut="escalade")
    return {"escalade": True, "ticket_id": ticket_id, "motif": motif}


# Registre : nom -> (fonction, est_sensible)
OUTILS = {
    "rechercher_utilisateur": (rechercher_utilisateur, False),
    "consulter_equipement": (consulter_equipement, False),
    "verifier_etat_service": (verifier_etat_service, False),
    "rechercher_incidents_actifs": (rechercher_incidents_actifs, False),
    "creer_ticket": (creer_ticket, True),
    "mettre_a_jour_ticket": (mettre_a_jour_ticket, True),
    "affecter_ticket": (affecter_ticket, True),
    "escalader_vers_technicien": (escalader_vers_technicien, True),
}
