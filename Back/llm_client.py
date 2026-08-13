"""
Client LLM — Gemini Flash pour la synthèse de réponses RAG.

Isolé dans son propre module pour que :
- l'appel réseau/API soit à un seul endroit (facile à remplacer par un autre
  fournisseur si besoin — Claude, GPT... — sans toucher au reste du pipeline).
- un échec de l'appel LLM (clé absente, quota dépassé, timeout) ne fasse
  JAMAIS planter le pipeline : on retombe sur un fallback exploitable.

Variables d'environnement attendues (voir .env.example) :
- GEMINI_API_KEY  (obligatoire pour activer la génération)
- GEMINI_MODEL    (optionnel, défaut: gemini-2.0-flash)
"""

import os
import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

_client = None


def _get_client() -> genai.Client:
    """Initialise le client Google GenAI à la demande (lazy) — évite un crash au démarrage
    de l'API si la clé n'est pas encore configurée pendant le développement."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY non défini dans l'environnement")
        # Instanciation du nouveau SDK client avec la clé d'environnement
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def generate_grounded_answer(question: str, sources: list[dict]) -> str:
    """
    Génère une réponse à partir des `sources` retrouvées par le RAG, UNIQUEMENT.
    Le prompt interdit explicitement d'inventer une procédure absente des sources
    (exigence du sujet, section 3.3 : "Une réponse qui n'est pas suffisamment
    soutenue par les sources devra être signalée comme incertaine").

    `sources` : liste de dicts avec au moins doc_id et extrait
    (cf. SourceDocument.model_dump() dans rag.py).
    """
    if not sources:
        return "Aucune source pertinente trouvée dans la base de connaissances."

    contexte = "\n\n".join(f"[{s['doc_id']}] {s['extrait']}" for s in sources)

    prompt = f"""Tu es un assistant de support informatique interne.
Réponds à la demande ci-dessous UNIQUEMENT à partir des extraits de documentation fournis.
Si les extraits ne permettent pas de répondre avec certitude, dis-le clairement plutôt que d'inventer une procédure.
Cite l'identifiant du document utilisé entre crochets, ex: [KB-NET-04].
Réponse concise (3-5 phrases maximum), orientée action.

Demande de l'utilisateur :
{question}

Extraits de documentation disponibles :
{contexte}

Réponse :"""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=400,
            ),
        )
        texte = (response.text or "").strip()
        return texte or _fallback(sources)
    except Exception as e:
        # Le pipeline ne doit jamais s'arrêter à cause du LLM : on logue et on
        # retombe sur une réponse minimale mais toujours fondée sur les sources.
        logger.warning("Appel Gemini échoué (%s) — fallback sur concat des sources", e)
        return _fallback(sources)


def _fallback(sources: list[dict]) -> str:
    premiere = sources[0]
    return f"[Réponse générée sans LLM] Voir procédure {premiere['doc_id']} : {premiere['extrait']}"