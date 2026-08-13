"""
Module 5 — Sortie structurée finale.
Contrat : tout ce qui précède -> DecisionFinale (respecte le schéma imposé, section 5.3 du sujet)

Règle d'or : les garde-fous de validation humaine sont calculés ici en dur,
jamais laissés à la seule appréciation du LLM.
"""

from models import (
    TicketIn, Classification, Diagnostic, ResultatRAG, ToolCall, DecisionFinale, Action
)
from logger import timed_step

CATEGORIES_SENSIBLES = {"cybersecurite", "droits_acces"}


def _determine_action(classification: Classification, diagnostic: Diagnostic,
                       rag_result: ResultatRAG) -> Action:
    if not diagnostic.diagnostic_suffisant:
        return "demande_information"
    if classification.categorie in CATEGORIES_SENSIBLES:
        return "escalade"
    if rag_result.reponse_incertaine:
        return "escalade"
    return "resolution"


def _validation_requise(classification: Classification, action: Action,
                         outils: list[ToolCall]) -> bool:
    if classification.categorie in CATEGORIES_SENSIBLES:
        return True
    if action == "escalade":
        return True
    if any(tc.statut == "en_attente_validation" for tc in outils):
        return True
    return False


def build_decision(ticket: TicketIn, classification: Classification,
                    diagnostic: Diagnostic, rag_result: ResultatRAG,
                    outils: list[ToolCall]) -> DecisionFinale:
    entree = {"ticket_id": ticket.ticket_id}
    with timed_step(ticket.ticket_id, "decision", entree) as finish:
        action = _determine_action(classification, diagnostic, rag_result)
        validation_requise = _validation_requise(classification, action, outils)

        etapes = []
        if rag_result.reponse_fondee:
            etapes.append(rag_result.reponse_fondee)
        if diagnostic.questions_a_poser:
            etapes.extend(diagnostic.questions_a_poser)

        result = DecisionFinale(
            ticket_id=ticket.ticket_id,
            resume_probleme=ticket.texte[:200],
            categorie=classification.categorie,
            priorite=classification.priorite,
            confiance=classification.confiance,
            diagnostic=(
                "Diagnostic suffisant" if diagnostic.diagnostic_suffisant
                else "Informations manquantes : " + ", ".join(diagnostic.informations_manquantes)
            ),
            etapes_resolution=etapes,
            informations_manquantes=diagnostic.informations_manquantes,
            sources=[s.doc_id for s in rag_result.sources],
            outils_utilises=[tc.nom_outil for tc in outils],
            action=action,
            validation_humaine_requise=validation_requise,
        )
        finish(result.model_dump())
    return result
