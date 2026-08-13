"""
Module 2 — Complétion du diagnostic.
Contrat : TicketIn, Classification -> Diagnostic (voir models.py)

Objectif : extraire ce qui est déjà présent dans le texte, repérer ce qui manque,
et générer des questions ciblées plutôt que de deviner.
"""

from models import TicketIn, Classification, Diagnostic, InfosExtraites
from logger import timed_step

# Champs jugés nécessaires selon la catégorie, pour juger si le diagnostic est exploitable.
CHAMPS_REQUIS = {
    "comptes_authentification": ["utilisateur", "application"],
    "reseau_connectivite": ["equipement", "moment_apparition"],
    "materiel_informatique": ["equipement", "symptomes"],
    "logiciels_applications": ["application", "symptomes"],
    "imprimantes_peripheriques": ["equipement"],
    "droits_acces": ["utilisateur", "application"],
    "cybersecurite": ["utilisateur", "moment_apparition"],
    "autre_indetermine": [],
}

QUESTIONS_PAR_CHAMP = {
    "utilisateur": "Pouvez-vous confirmer votre identifiant utilisateur ?",
    "equipement": "Quel équipement (poste, modèle) est concerné ?",
    "application": "Quelle application ou quel service est concerné ?",
    "symptomes": "Pouvez-vous décrire précisément ce qui se passe (message d'erreur, comportement) ?",
    "moment_apparition": "Depuis quand rencontrez-vous ce problème ?",
    "impact_activite": "Ce problème vous empêche-t-il de travailler complètement ou partiellement ?",
}


def _extract_infos(texte: str) -> InfosExtraites:
    """
    TODO : extraction plus fine (regex / NER / LLM). Version de départ : on renvoie
    une extraction vide et on laisse le calcul de champs manquants faire son travail,
    OU on branche un appel LLM structuré ici (recommandé).
    """
    return InfosExtraites(symptomes=texte[:200])  # placeholder minimal


def diagnose(ticket: TicketIn, classification: Classification) -> Diagnostic:
    entree = {"texte": ticket.texte, "categorie": classification.categorie}
    with timed_step(ticket.ticket_id, "diagnostic", entree) as finish:
        infos = _extract_infos(ticket.texte)
        requis = CHAMPS_REQUIS.get(classification.categorie, [])

        manquants = [
            champ for champ in requis
            if getattr(infos, champ, None) in (None, "")
        ]
        questions = [QUESTIONS_PAR_CHAMP[c] for c in manquants if c in QUESTIONS_PAR_CHAMP]

        result = Diagnostic(
            infos=infos,
            informations_manquantes=manquants,
            questions_a_poser=questions,
            diagnostic_suffisant=len(manquants) == 0,
        )
        finish(result.model_dump())
    return result
