"""
Petite base SQLite pour persister l'état des tickets, les décisions prises
et l'historique des appels d'outils. Complémente logger.py (qui trace en JSONL
pour l'observabilité fine, prompt-par-prompt) — ici on stocke l'état "métier"
interrogeable (ex: "quels tickets en attente de validation ?").

Un seul fichier : data/app.db. Zéro config, suffisant pour la démo.
"""

import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "data" / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    utilisateur_id      TEXT PRIMARY KEY,
    nom                 TEXT NOT NULL,
    email               TEXT NOT NULL UNIQUE,
    mot_de_passe_hash   TEXT NOT NULL,
    sel                 TEXT NOT NULL,
    horodatage          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id       TEXT PRIMARY KEY,
    texte           TEXT NOT NULL,
    utilisateur_id  TEXT NOT NULL,
    horodatage      TEXT NOT NULL,
    statut          TEXT NOT NULL DEFAULT 'nouveau',
    equipe_affectee TEXT,
    FOREIGN KEY (utilisateur_id) REFERENCES users(utilisateur_id)
);

CREATE TABLE IF NOT EXISTS decisions (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id                   TEXT NOT NULL,
    categorie                   TEXT,
    priorite                    TEXT,
    confiance                   REAL,
    action                      TEXT,
    validation_humaine_requise  INTEGER,
    payload_json                TEXT NOT NULL,
    horodatage                  TEXT NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id     TEXT NOT NULL,
    nom_outil     TEXT NOT NULL,
    parametres    TEXT,
    resultat      TEXT,
    statut        TEXT NOT NULL,
    latence_ms    REAL,
    horodatage    TEXT NOT NULL
);
"""


@contextmanager
def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Comptes utilisateurs (authentification)
# ---------------------------------------------------------------------------

def create_user(utilisateur_id: str, nom: str, email: str,
                 mot_de_passe_hash: str, sel: str, horodatage: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO users (utilisateur_id, nom, email, mot_de_passe_hash, sel, horodatage)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (utilisateur_id, nom, email, mot_de_passe_hash, sel, horodatage),
        )


def get_user_by_email(email: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(utilisateur_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE utilisateur_id = ?", (utilisateur_id,)
        ).fetchone()
        return dict(row) if row else None


def email_existe(email: str) -> bool:
    return get_user_by_email(email) is not None


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------

def save_ticket(ticket_id: str, texte: str, utilisateur_id: str | None, horodatage: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO tickets (ticket_id, texte, utilisateur_id, horodatage)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(ticket_id) DO NOTHING""",
            (ticket_id, texte, utilisateur_id, horodatage),
        )


def update_ticket_statut(ticket_id: str, statut: str, equipe: str | None = None):
    with get_connection() as conn:
        if equipe:
            conn.execute(
                "UPDATE tickets SET statut = ?, equipe_affectee = ? WHERE ticket_id = ?",
                (statut, equipe, ticket_id),
            )
        else:
            conn.execute(
                "UPDATE tickets SET statut = ? WHERE ticket_id = ?",
                (statut, ticket_id),
            )


def get_ticket(ticket_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None


def list_tickets() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY horodatage DESC").fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Décisions
# ---------------------------------------------------------------------------

def save_decision(ticket_id: str, categorie: str, priorite: str, confiance: float,
                   action: str, validation_humaine_requise: bool, payload: dict, horodatage: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO decisions
               (ticket_id, categorie, priorite, confiance, action,
                validation_humaine_requise, payload_json, horodatage)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticket_id, categorie, priorite, confiance, action,
             int(validation_humaine_requise), json.dumps(payload, ensure_ascii=False), horodatage),
        )


def list_decisions(en_attente_seulement: bool = False) -> list[dict]:
    with get_connection() as conn:
        query = "SELECT * FROM decisions"
        if en_attente_seulement:
            query += " WHERE validation_humaine_requise = 1"
        query += " ORDER BY horodatage DESC"
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Appels d'outils
# ---------------------------------------------------------------------------

def save_tool_call(ticket_id: str, nom_outil: str, parametres: dict, resultat: dict | None,
                    statut: str, latence_ms: float | None, horodatage: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO tool_calls
               (ticket_id, nom_outil, parametres, resultat, statut, latence_ms, horodatage)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ticket_id, nom_outil, json.dumps(parametres, ensure_ascii=False),
             json.dumps(resultat, ensure_ascii=False) if resultat is not None else None,
             statut, latence_ms, horodatage),
        )


def list_tool_calls(ticket_id: str | None = None) -> list[dict]:
    with get_connection() as conn:
        if ticket_id:
            rows = conn.execute(
                "SELECT * FROM tool_calls WHERE ticket_id = ? ORDER BY horodatage",
                (ticket_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tool_calls ORDER BY horodatage DESC").fetchall()
        return [dict(r) for r in rows]