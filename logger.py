"""
Observabilité : chaque étape du pipeline écrit une LogEntry en JSONL.
Utilisé pour : dashboard.py, le "journal d'observabilité" livrable, et le calcul de latence/coût.
"""

import json
import time
from pathlib import Path
from contextlib import contextmanager
from models import LogEntry

LOG_FILE = Path(__file__).parent / "logs" / "traces.jsonl"
LOG_FILE.parent.mkdir(exist_ok=True)


def log_step(ticket_id: str, etape: str, entree: dict, sortie: dict,
             latence_ms: float, erreur: str | None = None):
    entry = LogEntry(
        ticket_id=ticket_id,
        etape=etape,
        entree=entree,
        sortie=sortie,
        latence_ms=latence_ms,
        erreur=erreur,
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")


@contextmanager
def timed_step(ticket_id: str, etape: str, entree: dict):
    """Usage:
    with timed_step(ticket_id, "classification", {"texte": texte}) as finish:
        resultat = ...
        finish(resultat.model_dump())
    """
    start = time.perf_counter()
    sortie_holder = {}
    erreur_holder = {"erreur": None}

    def finish(sortie: dict):
        sortie_holder["sortie"] = sortie

    try:
        yield finish
    except Exception as e:
        erreur_holder["erreur"] = str(e)
        raise
    finally:
        latence_ms = (time.perf_counter() - start) * 1000
        log_step(
            ticket_id, etape, entree,
            sortie_holder.get("sortie", {}),
            latence_ms,
            erreur_holder["erreur"],
        )


def read_all_logs() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
