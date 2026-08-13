"""
Module 4 — Agent avec outils.
Contrat : TicketIn, Classification, Diagnostic, ResultatRAG -> list[ToolCall]

Garde-fous appliqués ICI (en dur, pas laissés au LLM) :
- catégorie cybersecurite -> aucune action automatique, escalade + validation humaine
- tout outil marqué "sensible" -> statut "en_attente_validation" tant que non confirmé
- nombre d'appels limité (anti-boucle / anti-abus)
- paramètres non conformes -> statut "refuse"
"""

import time
from datetime import datetime
from models import TicketIn, Classification, Diagnostic, ResultatRAG, ToolCall
from tools import OUTILS
from logger import log_step
import db

MAX_APPELS_OUTILS = 5
CATEGORIES_TOUJOURS_VALIDATION = {"cybersecurite", "droits_acces"}


def call_tool(ticket_id: str, nom_outil: str, parametres: dict, forcer_sensible: bool = False) -> ToolCall:
    start = time.perf_counter()

    if nom_outil not in OUTILS:
        tc = ToolCall(nom_outil=nom_outil, parametres=parametres, statut="refuse",
                      resultat={"erreur": "outil inconnu"})
        _log(ticket_id, tc, start)
        return tc

    fonction, est_sensible = OUTILS[nom_outil]

    if est_sensible or forcer_sensible:
        tc = ToolCall(nom_outil=nom_outil, parametres=parametres,
                       statut="en_attente_validation", resultat=None)
        _log(ticket_id, tc, start)
        return tc

    try:
        resultat = fonction(**parametres)
        tc = ToolCall(nom_outil=nom_outil, parametres=parametres, statut="succes", resultat=resultat)
    except Exception as e:
        tc = ToolCall(nom_outil=nom_outil, parametres=parametres, statut="echec",
                       resultat={"erreur": str(e)})

    _log(ticket_id, tc, start)
    return tc


def _log(ticket_id: str, tc: ToolCall, start: float):
    latence_ms = (time.perf_counter() - start) * 1000
    tc.latence_ms = latence_ms
    log_step(ticket_id, "agent_tool_call", {"nom_outil": tc.nom_outil, "parametres": tc.parametres},
              {"statut": tc.statut, "resultat": tc.resultat}, latence_ms)
    db.save_tool_call(
        ticket_id=ticket_id,
        nom_outil=tc.nom_outil,
        parametres=tc.parametres,
        resultat=tc.resultat,
        statut=tc.statut,
        latence_ms=latence_ms,
        horodatage=datetime.now().isoformat(),
    )


def run_agent(ticket: TicketIn, classification: Classification,
              diagnostic: Diagnostic, rag_result: ResultatRAG) -> list[ToolCall]:
    """
    Enchaîne un nombre borné d'appels d'outils selon des règles simples.
    TODO équipe agent : remplacer par une sélection pilotée par LLM (function calling)
    si le temps le permet — le wrapper call_tool() reste le point de passage obligé
    pour garder le logging et les garde-fous.
    """
    appels: list[ToolCall] = []

    if len(appels) >= MAX_APPELS_OUTILS:
        return appels

    # Exemple de logique minimale de départ
    if diagnostic.infos.utilisateur:
        appels.append(call_tool(ticket.ticket_id, "rechercher_utilisateur",
                                 {"utilisateur_id": diagnostic.infos.utilisateur}))

    if classification.categorie in CATEGORIES_TOUJOURS_VALIDATION:
        appels.append(call_tool(ticket.ticket_id, "escalader_vers_technicien",
                                 {"ticket_id": ticket.ticket_id, "motif": classification.categorie},
                                 forcer_sensible=True))
    elif classification.priorite in ("haute", "critique"):
        appels.append(call_tool(ticket.ticket_id, "rechercher_incidents_actifs",
                                 {"categorie": classification.categorie}))
        appels.append(call_tool(ticket.ticket_id, "affecter_ticket",
                                 {"ticket_id": ticket.ticket_id, "equipe": classification.equipe},
                                 forcer_sensible=True))

    return appels
