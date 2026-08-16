import streamlit as st
import glob
import json
from text_extract import extraire_texte_pdf
from answer_single_doc import repondre_question
from answer import indexer_documents, repondre_avec_rag
from fields import extraire_champs
import os

st.title("FinDocIQ — Extraction et Q&A sur documents financiers")

onglet_extraction, onglet_qa, onglet_metriques = st.tabs(
    ["📄 Extraction de champs", "💬 Question/Réponse", "📊 Métriques du système"]
)

# --- ONGLET 1 : Extraction de champs, avec upload ---
with onglet_extraction:
    st.subheader("Téléverse un document pour extraire ses champs")

    fichier_televerse = st.file_uploader("Choisis un PDF", type="pdf")

    if fichier_televerse is not None:
        chemin_temporaire = f"temp_{fichier_televerse.name}"
        with open(chemin_temporaire, "wb") as f:
            f.write(fichier_televerse.getbuffer())

        with st.spinner("Extraction en cours..."):
            texte = extraire_texte_pdf(chemin_temporaire)
            champs = extraire_champs(texte)

        st.success("Extraction terminée")

        # Tableau des champs simples (pas les lignes, affichées à part)
        champs_simples = {k: v for k, v in champs.items() if k != "lignes"}
        st.table(champs_simples)

        if champs.get("lignes"):
            st.write("**Lignes détaillées :**")
            st.table(champs["lignes"])
                
        os.remove(chemin_temporaire)    
with onglet_qa:
    st.subheader("Pose une question sur tes documents")

    fichiers_disponibles = glob.glob("factures/*.pdf")

    mode = st.radio(
        "Mode :",
        ["Document unique (direct)", "Plusieurs documents (RAG)"]
    )

    fichier_choisi = None
    if mode == "Document unique (direct)":
        fichier_choisi = st.selectbox("Choisis un document :", fichiers_disponibles)

    # Initialise l'historique de conversation, une seule fois
    if "historique_chat" not in st.session_state:
        st.session_state.historique_chat = []

    # Réaffiche tout l'historique déjà accumulé
    for message in st.session_state.historique_chat:
        with st.chat_message(message["role"]):
            st.write(message["contenu"])
            if message["role"] == "assistant":
                st.caption(f"Mode : {message['mode']} | Citation : {message['citation']}")

    # Zone de saisie en bas, façon chat
    question = st.chat_input("Pose ta question ici...")

    if question:
        # Affiche immédiatement la question de l'utilisateur
        with st.chat_message("user"):
            st.write(question)
        st.session_state.historique_chat.append({"role": "user", "contenu": question})

        # Calcule la réponse selon le mode choisi
        with st.spinner("Réflexion en cours..."):
            if mode == "Document unique (direct)":
                texte = extraire_texte_pdf(fichier_choisi)
                resultat = repondre_question(texte, question)
            else:
                index, chunks_avec_source = indexer_documents(fichiers_disponibles)
                resultat = repondre_avec_rag(question, index, chunks_avec_source)

        # Affiche la réponse de l'assistant
        with st.chat_message("assistant"):
            st.write(resultat["reponse"])
            st.caption(f"Mode : {mode} | Citation : {resultat['citation']}")

        st.session_state.historique_chat.append({
            "role": "assistant",
            "contenu": resultat["reponse"],
            "mode": mode,
            "citation": resultat["citation"]
        })
with onglet_metriques:
    st.subheader("Fiabilité mesurée du système")

    st.write("**Extraction de champs (eval_extraction.py, 12 documents)**")
    st.table({
        "Champ": ["numero_facture", "date", "emetteur", "client", "total"],
        "Precision": [0.92, 1.00, 1.00, 1.00, 1.00],
        "Recall": [1.00, 1.00, 0.82, 1.00, 1.00],
        "F1": [0.96, 1.00, 0.90, 1.00, 1.00],
    })

    st.write("**RAG — retrieval et réponses par type de question (eval_rag.py, 60 questions)**")
    st.table({
        "Type": ["lookup", "calcul", "sans_réponse"],
        "Retrieval hit-rate": ["72%", "92%", "67%"],
        "Answer accuracy": ["42%", "25%", "67%"],
    })

    st.warning("⚠️ Limite connue : les questions nécessitant un calcul multi-étapes restent peu fiables (25% de bonnes réponses), même quand le bon document est correctement trouvé (92%).")