"""
Module 3 — Recherche documentaire (RAG).
Contrat : requête texte -> ResultatRAG (voir models.py)

Version de départ : similarité lexicale simple (TF-IDF) pour avoir un pipeline
qui tourne immédiatement. A remplacer par des embeddings (sentence-transformers,
ChromaDB...) si le temps le permet — l'interface ne change pas.
"""

import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models import TicketIn, ResultatRAG, SourceDocument
from logger import timed_step
import llm_client          # ← ligne ajoutée

KB_FILE = Path(__file__).parent / "data" / "knowledge_base.json"
SEUIL_CONFIANCE = 0.15  # en dessous -> reponse_incertaine = True


class KnowledgeBase:
    def __init__(self, path: Path = KB_FILE):
        self.documents = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        self.vectorizer = None
        self.matrix = None
        if self.documents:
            self._build_index()

    def _build_index(self):
        textes = [doc["contenu"] for doc in self.documents]
        self.vectorizer = TfidfVectorizer()
        self.matrix = self.vectorizer.fit_transform(textes)

    def search(self, query: str, k: int = 3) -> list[SourceDocument]:
        if not self.documents or self.vectorizer is None:
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]
        top_idx = scores.argsort()[::-1][:k]
        return [
            SourceDocument(
                doc_id=self.documents[i]["doc_id"],
                extrait=self.documents[i]["contenu"][:300],
                score=float(scores[i]),
            )
            for i in top_idx if scores[i] > 0
        ]


_kb = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def retrieve_and_answer(ticket: TicketIn) -> ResultatRAG:
    with timed_step(ticket.ticket_id, "rag", {"query": ticket.texte}) as finish:
        sources = get_kb().search(ticket.texte, k=3)
        incertaine = not sources or sources[0].score < SEUIL_CONFIANCE

        reponse = None
        if not incertaine:
            reponse = llm_client.generate_grounded_answer(
                question=ticket.texte,
                sources=[s.model_dump() for s in sources],
            )

        result = ResultatRAG(
            sources=sources,
            reponse_fondee=reponse,
            reponse_incertaine=incertaine,
        )
        finish(result.model_dump())
    return result
