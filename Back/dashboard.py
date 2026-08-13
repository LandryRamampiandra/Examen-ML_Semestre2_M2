"""
Dashboard d'observabilité. Lance : streamlit run dashboard.py
Lit logs/traces.jsonl (écrit par logger.py) et les affiche.
"""

import streamlit as st
import pandas as pd
from logger import read_all_logs
import db

st.set_page_config(page_title="Observabilité — mAIntenance & Assistance", layout="wide")
st.title("mAIntenance & Assistance — Observabilité")

onglet_tickets, onglet_traces = st.tabs(["Tickets (SQLite)", "Traces (JSONL)"])

with onglet_tickets:
    tickets = db.list_tickets()
    if not tickets:
        st.info("Aucun ticket en base. Traitez un ticket via l'API pour le voir apparaître ici.")
    else:
        df_tickets = pd.DataFrame(tickets)

        col1, col2, col3 = st.columns(3)
        col1.metric("Tickets en base", len(df_tickets))
        en_attente = len(db.list_decisions(en_attente_seulement=True))
        col2.metric("En attente de validation humaine", en_attente)
        col3.metric("Statuts distincts", df_tickets["statut"].nunique())

        st.subheader("Tous les tickets")
        st.dataframe(df_tickets, use_container_width=True)

        st.subheader("En attente de validation humaine")
        decisions_attente = db.list_decisions(en_attente_seulement=True)
        if decisions_attente:
            st.dataframe(pd.DataFrame(decisions_attente)[
                ["ticket_id", "categorie", "priorite", "action", "horodatage"]
            ], use_container_width=True)
        else:
            st.write("Aucun ticket en attente.")

        st.subheader("Détail d'un ticket (avec ses appels d'outils)")
        choix_ticket = st.selectbox("Choisir un ticket", df_tickets["ticket_id"].tolist())
        if choix_ticket:
            appels = db.list_tool_calls(choix_ticket)
            st.write(f"**{len(appels)} appel(s) d'outil** pour ce ticket :")
            if appels:
                st.dataframe(pd.DataFrame(appels)[
                    ["nom_outil", "statut", "latence_ms", "horodatage"]
                ], use_container_width=True)

with onglet_traces:
    logs = read_all_logs()

    if not logs:
        st.info("Aucune trace pour le moment. Traitez un ticket via l'API pour voir apparaître des logs ici.")
    else:
        df = pd.DataFrame(logs)

        col1, col2, col3 = st.columns(3)
        col1.metric("Tickets tracés", df["ticket_id"].nunique())
        col2.metric("Étapes exécutées", len(df))
        col3.metric("Latence moyenne (ms)", round(df["latence_ms"].mean(), 1))

        ticket_ids = sorted(df["ticket_id"].unique())
        choix = st.selectbox("Filtrer par ticket", ["Tous"] + list(ticket_ids))
        df_filtre = df if choix == "Tous" else df[df["ticket_id"] == choix]

        st.subheader("Traces")
        st.dataframe(
            df_filtre[["horodatage", "ticket_id", "etape", "latence_ms", "erreur"]],
            use_container_width=True,
        )

        st.subheader("Détail d'une trace")
        idx = st.number_input("Index de ligne", min_value=0, max_value=max(len(df_filtre) - 1, 0), value=0)
        if len(df_filtre) > 0:
            ligne = df_filtre.iloc[idx]
            st.json({"entree": ligne["entree"], "sortie": ligne["sortie"]})

        erreurs = df[df["erreur"].notna()]
        if not erreurs.empty:
            st.subheader("Erreurs")
            st.dataframe(erreurs[["ticket_id", "etape", "erreur"]], use_container_width=True)
