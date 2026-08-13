"""
Module 1 — Compréhension et classification du ticket.
Contrat : TicketIn -> Classification (voir models.py)

Approche de départ : règles par mots-clés (rapide, mesurable, sert de baseline).
A remplacer/compléter par un appel LLM few-shot (cf. llm_classify) une fois le
squelette validé. Les deux peuvent cohabiter (approche hybride).
"""

from models import TicketIn, Classification
from logger import timed_step

# Mots-clés -> catégorie. A enrichir avec le corpus d'exemples fourni.
REGLES_CATEGORIE = {
    "comptes_authentification": ["mot de passe", "compte verrouillé", "connexion impossible", "login"],
    "reseau_connectivite": ["réseau", "wifi", "connexion internet", "lenteur réseau", "vpn"],
    "materiel_informatique": ["panne", "écran", "clavier", "ordinateur ne démarre", "matériel"],
    "logiciels_applications": ["application", "logiciel", "plante", "erreur", "ne démarre plus"],
    "imprimantes_peripheriques": ["imprimante", "impression", "scanner"],
    "droits_acces": ["accès", "partage", "permission", "droits"],
    "cybersecurite": ["phishing", "courriel suspect", "virus", "compromis", "suspect"],
}

MOTS_CLES_URGENCE = ["urgent", "bloqué", "impossible de travailler", "production", "tout le service"]

EQUIPE_PAR_CATEGORIE = {
    "comptes_authentification": "support-n1",
    "reseau_connectivite": "infrastructure",
    "materiel_informatique": "support-n1",
    "logiciels_applications": "support-n1",
    "imprimantes_peripheriques": "support-n1",
    "droits_acces": "infrastructure",
    "cybersecurite": "securite",
    "autre_indetermine": "support-n1",
}


def _classify_by_rules(texte: str) -> tuple[str, float]:
    texte_lower = texte.lower()
    scores = {}
    for categorie, mots_cles in REGLES_CATEGORIE.items():
        hits = sum(1 for mot in mots_cles if mot in texte_lower)
        if hits:
            scores[categorie] = hits
    if not scores:
        return "autre_indetermine", 0.3
    meilleure = max(scores, key=scores.get)
    confiance = min(0.5 + 0.15 * scores[meilleure], 0.9)  # heuristique simple
    return meilleure, confiance


def _estimate_priorite(texte: str, categorie: str) -> str:
    texte_lower = texte.lower()
    if categorie == "cybersecurite":
        return "critique"
    if any(mot in texte_lower for mot in MOTS_CLES_URGENCE):
        return "haute"
    return "moyenne"


def llm_classify(texte: str) -> tuple[str, float]:
    """
    TODO équipe LLM : appeler le modèle avec le schéma JSON imposé + few-shot
    examples tirés de l'historique de tickets. Retourner (categorie, confiance).
    Garder cette fonction séparée permet de comparer règles vs LLM (axe évaluation).
    """
    raise NotImplementedError


def classify(ticket: TicketIn) -> Classification:
    with timed_step(ticket.ticket_id, "classification", {"texte": ticket.texte}) as finish:
        categorie, confiance = _classify_by_rules(ticket.texte)
        priorite = _estimate_priorite(ticket.texte, categorie)
        equipe = EQUIPE_PAR_CATEGORIE[categorie]

        result = Classification(
            categorie=categorie,
            priorite=priorite,
            equipe=equipe,
            confiance=confiance,
            methode="regles",
        )
        finish(result.model_dump())
    return result
