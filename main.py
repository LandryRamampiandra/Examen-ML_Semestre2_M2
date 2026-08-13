"""
Point d'entrée. Lance : uvicorn main:app --reload
Endpoint principal : POST /tickets -> DecisionFinale
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import TicketIn, DecisionFinale
from classifier import classify
from diagnostic import diagnose
from rag import retrieve_and_answer
from agent import run_agent
from decision import build_decision
import db

app = FastAPI(title="mAIntenance & Assistance")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    db.init_db()


@app.post("/tickets", response_model=DecisionFinale)
def process_ticket(ticket: TicketIn) -> DecisionFinale:
    db.save_ticket(ticket.ticket_id, ticket.texte, ticket.utilisateur_id,
                    ticket.horodatage.isoformat())

    classification = classify(ticket)
    diagnostic = diagnose(ticket, classification)
    rag_result = retrieve_and_answer(ticket)
    outils = run_agent(ticket, classification, diagnostic, rag_result)
    decision = build_decision(ticket, classification, diagnostic, rag_result, outils)

    db.save_decision(
        ticket_id=decision.ticket_id,
        categorie=decision.categorie,
        priorite=decision.priorite,
        confiance=decision.confiance,
        action=decision.action,
        validation_humaine_requise=decision.validation_humaine_requise,
        payload=decision.model_dump(),
        horodatage=ticket.horodatage.isoformat(),
    )
    db.update_ticket_statut(
        ticket.ticket_id,
        statut="en_attente_validation" if decision.validation_humaine_requise else decision.action,
        equipe=classification.equipe,
    )

    return decision


@app.get("/health")
def health():
    return {"statut": "ok"}


@app.get("/tickets")
def get_tickets():
    return db.list_tickets()


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        return {"erreur": "ticket introuvable"}
    ticket["outils"] = db.list_tool_calls(ticket_id)
    ticket["decisions"] = [d for d in db.list_decisions() if d["ticket_id"] == ticket_id]
    return ticket


@app.get("/tickets-en-attente")
def get_tickets_en_attente():
    """Tickets dont la décision nécessite une validation humaine — pour l'écran de validation."""
    return db.list_decisions(en_attente_seulement=True)
