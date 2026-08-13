"""
Point d'entrée. Lance : uvicorn main:app --reload
Endpoints d'authentification et de traitement sécurisé de tickets.
"""

from dotenv import load_dotenv
load_dotenv()  # doit être appelé avant les imports qui lisent os.environ (llm_client, auth)

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from models import TicketIn, DecisionFinale
from classifier import classify
from diagnostic import diagnose
from rag import retrieve_and_answer
from agent import run_agent
from decision import build_decision
import db
import Auth

app = FastAPI(title="mAIntenance & Assistance")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Modèles Pydantic pour l'authentification
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    nom: str
    email: EmailStr
    mot_de_passe: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Événements système
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    db.init_db()


# ---------------------------------------------------------------------------
# Endpoints d'authentification
# ---------------------------------------------------------------------------

@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister):
    """Inscrit un nouvel utilisateur."""
    return Auth.register(
        nom=user_data.nom,
        email=user_data.email,
        mot_de_passe=user_data.mot_de_passe
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Connecte un utilisateur et retourne un jeton JWT.
    Compatible avec Swagger UI (champs `username` qui contient l'email et `password`).
    """
    token = Auth.login(email=form_data.username, mot_de_passe=form_data.password)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me")
def get_me(current_user: dict = Depends(Auth.get_current_user)):
    """Retourne le profil de l'utilisateur actuellement connecté."""
    # Exclure le hash et le sel de la réponse
    return {
        "utilisateur_id": current_user["utilisateur_id"],
        "nom": current_user["nom"],
        "email": current_user["email"],
        "horodatage": current_user.get("horodatage")
    }


# ---------------------------------------------------------------------------
# Endpoints Métier (Tickets)
# ---------------------------------------------------------------------------

@app.post("/tickets", response_model=DecisionFinale)
def process_ticket(
    ticket: TicketIn,
    current_user: dict = Depends(Auth.get_current_user)
) -> DecisionFinale:
    """
    Traite un ticket soumis.
    L'utilisateur_id est extrait du jeton JWT pour garant de la sécurité.
    """
    utilisateur_id = current_user["utilisateur_id"]

    db.save_ticket(
        ticket.ticket_id,
        ticket.texte,
        utilisateur_id,
        ticket.horodatage.isoformat()
    )

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
def get_tickets(current_user: dict = Depends(Auth.get_current_user)):
    """Liste les tickets (nécessite d'être connecté)."""
    return db.list_tickets()


@app.get("/tickets/{ticket_id}")
def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(Auth.get_current_user)
):
    """Récupère les détails d'un ticket par son ID."""
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    ticket["outils"] = db.list_tool_calls(ticket_id)
    ticket["decisions"] = [d for d in db.list_decisions() if d["ticket_id"] == ticket_id]
    return ticket


@app.get("/tickets-en-attente")
def get_tickets_en_attente(current_user: dict = Depends(Auth.get_current_user)):
    """Tickets dont la décision nécessite une validation humaine — pour l'écran de validation."""
    return db.list_decisions(en_attente_seulement=True)