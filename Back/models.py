"""
Contrats JSON entre modules — CE FICHIER EST LE CONTRAT COMMUN DE L'EQUIPE.
Chaque module lit/produit ces structures. Ne pas modifier sans prévenir tout le monde.

Pipeline : Ticket -> Classification -> Diagnostic -> RAG -> Agent -> Decision
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import uuid4


# ---------------------------------------------------------------------------
# 0. Entrée brute
# ---------------------------------------------------------------------------

class TicketIn(BaseModel):
    # Optionnel : si un système externe fournit déjà un identifiant (ex. ticket
    # importé d'un outil de ticketing existant), on le garde. Sinon, le backend
    # génère un UUID unique — le client n'a plus à s'en soucier ni à risquer
    # une collision.
    ticket_id: str = Field(default_factory=lambda: str(uuid4()))
    texte: str                     # description brute fournie par l'utilisateur
    utilisateur_id: Optional[str] = None
    horodatage: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# 1. Sortie du module classification (classifier.py)
# ---------------------------------------------------------------------------

Categorie = Literal[
    "comptes_authentification",
    "reseau_connectivite",
    "materiel_informatique",
    "logiciels_applications",
    "imprimantes_peripheriques",
    "droits_acces",
    "cybersecurite",
    "autre_indetermine",
]

Priorite = Literal["basse", "moyenne", "haute", "critique"]


class Classification(BaseModel):
    categorie: Categorie
    priorite: Priorite
    equipe: str                    # ex: "infrastructure", "support-n1", "securite"
    confiance: float                # 0.0 - 1.0
    methode: str                    # ex: "llm_fewshot", "regles", "hybride" (pour justification/rapport)


# ---------------------------------------------------------------------------
# 2. Sortie du module diagnostic (diagnostic.py)
# ---------------------------------------------------------------------------

class InfosExtraites(BaseModel):
    utilisateur: Optional[str] = None
    equipement: Optional[str] = None
    application: Optional[str] = None
    symptomes: Optional[str] = None
    moment_apparition: Optional[str] = None
    impact_activite: Optional[str] = None
    manipulations_deja_effectuees: Optional[str] = None


class Diagnostic(BaseModel):
    infos: InfosExtraites
    informations_manquantes: list[str] = []      # noms des champs manquants jugés nécessaires
    questions_a_poser: list[str] = []             # questions ciblées si infos insuffisantes
    diagnostic_suffisant: bool                    # False -> on s'arrête ici, on demande des infos


# ---------------------------------------------------------------------------
# 3. Sortie du module RAG (rag.py)
# ---------------------------------------------------------------------------

class SourceDocument(BaseModel):
    doc_id: str                    # ex: "KB-NET-04"
    extrait: str                   # passage utilisé (court)
    score: float


class ResultatRAG(BaseModel):
    sources: list[SourceDocument] = []
    reponse_fondee: Optional[str] = None   # réponse générée à partir des sources
    reponse_incertaine: bool = True        # True si aucune source ne dépasse le seuil


# ---------------------------------------------------------------------------
# 4. Traces d'appels d'outils (agent.py / tools.py)
# ---------------------------------------------------------------------------

class ToolCall(BaseModel):
    nom_outil: str
    parametres: dict
    resultat: Optional[dict] = None
    statut: Literal["succes", "echec", "refuse", "en_attente_validation"]
    horodatage: datetime = Field(default_factory=datetime.now)
    latence_ms: Optional[float] = None


# ---------------------------------------------------------------------------
# 5. Sortie finale — DOIT respecter le schéma imposé par le sujet (section 5.3)
# ---------------------------------------------------------------------------

Action = Literal["resolution", "demande_information", "escalade", "refus"]


class DecisionFinale(BaseModel):
    ticket_id: str
    resume_probleme: str
    categorie: Categorie
    priorite: Priorite
    confiance: float
    diagnostic: str
    etapes_resolution: list[str] = []
    informations_manquantes: list[str] = []
    sources: list[str] = []                 # doc_ids uniquement, format attendu par le sujet
    outils_utilises: list[str] = []         # noms des outils appelés
    action: Action
    validation_humaine_requise: bool


# ---------------------------------------------------------------------------
# 6. Entrée de log pour l'observabilité (logger.py)
# ---------------------------------------------------------------------------

class LogEntry(BaseModel):
    ticket_id: str
    etape: str                     # "classification" | "diagnostic" | "rag" | "agent" | "decision"
    entree: dict
    sortie: dict
    latence_ms: float
    horodatage: datetime = Field(default_factory=datetime.now)
    erreur: Optional[str] = None