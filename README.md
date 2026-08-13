# mAIntenance & Assistance — squelette

## Architecture

Pipeline linéaire, un module par responsabilité, contrat JSON commun défini dans `models.py`.

```
TicketIn
   │
   ▼
classifier.py   → Classification (catégorie, priorité, équipe, confiance)
   │
   ▼
diagnostic.py   → Diagnostic (infos extraites, infos manquantes, questions)
   │
   ▼
rag.py          → ResultatRAG (sources citées, réponse fondée ou incertaine)
   │
   ▼
agent.py        → list[ToolCall] (appels d'outils via tools.py, tous loggés)
   │
   ▼
decision.py     → DecisionFinale (schéma imposé par le sujet, garde-fous appliqués)
```

Chaque étape écrit sa trace dans `logs/traces.jsonl` via `logger.py` (module transverse) →
consultable dans `dashboard.py`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `models.py` | Contrats Pydantic entre modules — à figer en premier |
| `classifier.py` | Classification (règles + point d'extension LLM) |
| `diagnostic.py` | Extraction d'infos et détection de champs manquants |
| `rag.py` | Indexation + recherche documentaire (TF-IDF de départ) |
| `tools.py` | Outils simulés (consultation + action) |
| `agent.py` | Sélection/appel des outils, garde-fous, logging des appels |
| `decision.py` | Agrégation en sortie structurée finale |
| `logger.py` | Écriture des traces JSONL (observabilité fine, prompt par prompt) |
| `db.py` | Base SQLite (`data/app.db`) — état métier : tickets, décisions, appels d'outils |
| `main.py` | API FastAPI — `POST /tickets` |
| `dashboard.py` | Dashboard Streamlit de consultation des traces |
| `data/` | Données simulées (KB, utilisateurs, équipements, services, incidents) |

## Lancer le projet

```bash
./run.sh
```

- API : http://localhost:8000/docs (Swagger auto-généré par FastAPI)
- Dashboard : http://localhost:8501

Test rapide :
```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "t1", "texte": "Mon mot de passe ne fonctionne plus depuis ce matin, urgent"}'
```

## Base de données

SQLite, un seul fichier `data/app.db`, créé automatiquement au démarrage de l'API
(`db.init_db()` dans le hook `startup` de `main.py`). Trois tables :

- **`tickets`** — un ticket par ligne, avec son statut courant (`nouveau`, `traite`,
  `affecte`, `escalade`, `en_attente_validation`...) et l'équipe affectée.
- **`decisions`** — une ligne par décision produite (`DecisionFinale` complète en JSON
  dans `payload_json`, plus les champs clés en colonnes pour filtrer facilement).
- **`tool_calls`** — historique de tous les appels d'outils, avec paramètres, résultat,
  statut et latence.

Fonctions utiles côté code (`db.py`) : `list_tickets()`, `get_ticket(id)`,
`list_decisions(en_attente_seulement=True)` (pour l'écran de validation humaine),
`list_tool_calls(ticket_id)`.

Endpoints API associés : `GET /tickets`, `GET /tickets/{id}`, `GET /tickets-en-attente`.

Le dashboard (`dashboard.py`) a un onglet "Tickets (SQLite)" qui interroge cette base
directement, en plus de l'onglet "Traces (JSONL)" pour l'observabilité fine.

Pour repartir de zéro pendant les tests : `rm data/app.db` (recréée au prochain démarrage).

## Choix effectués

- **Classification** : règles par mots-clés en baseline mesurable (`methode: "regles"`),
  point d'extension `llm_classify()` prévu pour comparer à une approche few-shot.
- **RAG** : TF-IDF + similarité cosinus pour un pipeline fonctionnel immédiatement ;
  seuil de confiance (`SEUIL_CONFIANCE`) déclenche `reponse_incertaine` si aucune
  source ne convient.
- **Garde-fous** : codés en dur dans `agent.py` et `decision.py`, jamais laissés au LLM.
  Catégories `cybersecurite` et `droits_acces` → validation humaine systématique.
  Tout outil marqué sensible dans `tools.OUTILS` passe par un statut
  `en_attente_validation` avant exécution réelle.
- **Observabilité** : chaque étape logue automatiquement entrée/sortie/latence/erreur
  via `timed_step()`, sans effort supplémentaire dans chaque module.

## Limites connues (à compléter par l'équipe)

- Extraction d'infos (`diagnostic.py`) est un placeholder — à raffiner avec un LLM structuré.
- RAG en TF-IDF : pas de compréhension sémantique fine, à améliorer avec des embeddings si le temps le permet.
- Validation humaine simulée par un statut, pas d'interface de confirmation dédiée.
- Pas de persistance des tickets créés/modifiés (à ajouter dans `tools.py` si besoin, ex. SQLite).

## Prochaines étapes (par ordre de priorité)

1. Brancher un LLM sur `classifier.llm_classify` et `diagnostic._extract_infos`
   (few-shot avec exemples de l'historique de tickets fourni).
2. Brancher un LLM sur `rag.retrieve_and_answer` pour synthétiser la réponse
   à partir des sources retrouvées (au lieu du concat brut actuel).
3. Ajouter la sélection d'outils pilotée par LLM (function calling) dans `agent.py`.
4. Tester les 4 scénarios obligatoires du sujet de bout en bout.
5. Écrire les jeux de tests et les résultats d'évaluation (livrables 5 et 6).
