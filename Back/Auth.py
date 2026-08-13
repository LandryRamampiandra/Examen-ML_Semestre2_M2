"""
Authentification : inscription, connexion, hachage de mot de passe, JWT.

Approche volontairement simple pour un contexte hackathon :
- hachage du mot de passe avec PBKDF2-HMAC-SHA256 (stdlib, pas de dépendance
  supplémentaire pour ça) + sel aléatoire par utilisateur.
- JWT signé (HS256) pour l'authentification des requêtes suivantes, notamment
  la soumission de ticket : le ticket_id de l'utilisateur est extrait du
  token, jamais fait confiance à une valeur envoyée en clair par le client.

SECRET_KEY : à définir via variable d'environnement en production.
Ici valeur par défaut pour que ça tourne immédiatement en démo/hackathon.
"""

import hashlib
import secrets
import os
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

import db

SECRET_KEY = os.environ.get("SECRET_KEY", "changez-moi-en-production-ispm-hackathon")
ALGORITHM = "HS256"
EXPIRATION_MINUTES = 60 * 12  # 12h — largement suffisant pour une session de hackathon

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# Hachage de mot de passe
# ---------------------------------------------------------------------------

def hash_password(mot_de_passe: str, sel: str | None = None) -> tuple[str, str]:
    sel = sel or secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", mot_de_passe.encode("utf-8"), sel.encode("utf-8"), 100_000
    )
    return hash_bytes.hex(), sel


def verify_password(mot_de_passe: str, hash_stocke: str, sel: str) -> bool:
    hash_calcule, _ = hash_password(mot_de_passe, sel)
    return secrets.compare_digest(hash_calcule, hash_stocke)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(utilisateur_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRATION_MINUTES)
    payload = {"sub": utilisateur_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    """Retourne l'utilisateur_id contenu dans le token, ou lève une erreur HTTP 401."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        utilisateur_id = payload.get("sub")
        if utilisateur_id is None:
            raise HTTPException(status_code=401, detail="Token invalide")
        return utilisateur_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


# ---------------------------------------------------------------------------
# Dépendance FastAPI : utilisateur courant à partir du header Authorization
# ---------------------------------------------------------------------------

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    utilisateur_id = decode_access_token(token)
    user = db.get_user_by_id(utilisateur_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user


# ---------------------------------------------------------------------------
# Inscription / connexion
# ---------------------------------------------------------------------------

def register(nom: str, email: str, mot_de_passe: str) -> dict:
    if db.email_existe(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                             detail="Un compte existe déjà avec cet email")

    from uuid import uuid4
    utilisateur_id = str(uuid4())
    hash_mdp, sel = hash_password(mot_de_passe)

    db.create_user(
        utilisateur_id=utilisateur_id,
        nom=nom,
        email=email,
        mot_de_passe_hash=hash_mdp,
        sel=sel,
        horodatage=datetime.now().isoformat(),
    )
    return {"utilisateur_id": utilisateur_id, "nom": nom, "email": email}


def login(email: str, mot_de_passe: str) -> str:
    user = db.get_user_by_email(email)
    if user is None or not verify_password(mot_de_passe, user["mot_de_passe_hash"], user["sel"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                             detail="Email ou mot de passe incorrect")
    return create_access_token(user["utilisateur_id"])