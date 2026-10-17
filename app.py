import streamlit as st
import glob
import json
from text_extract import extraire_texte_pdf
from answer_single_doc import repondre_question
from answer import indexer_documents, repondre_avec_rag
from fields import extraire_champs
import os
from calcul import repondre_calcul


st.title("FinDocIQ — Extraction et Q&A sur documents financiers")

@st.cache_data
def champs_du_document(chemin):
    return extraire_champs(extraire_texte_pdf(chemin)) or {}


@st.cache_resource
def index_de_la_collection(fichiers):
    """Indexe la collection UNE seule fois (et non à chaque question)."""
    return indexer_documents(list(fichiers))

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

        os.remove(chemin_temporaire)

        if not champs:
            st.error("L'extraction a échoué (voir le terminal). Vérifie qu'Ollama est lancé.")
        else:
            st.success("Extraction terminée")

            # Tableau des champs simples (pas les lignes, affichées à part)
            champs_simples = {k: v for k, v in champs.items() if k != "lignes"}
            st.table(champs_simples)

            if champs.get("lignes"):
                st.write("**Lignes détaillées :**")
                st.table(champs["lignes"])

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
                resultat = repondre_calcul(question, champs_du_document(fichier_choisi)) or repondre_question(texte, question)

            else:
                index, chunks_avec_source = index_de_la_collection(tuple(fichiers_disponibles))
                resultat = repondre_avec_rag(question, index, chunks_avec_source)

        if not resultat:
            resultat = {"reponse": "Erreur : le modèle n'a pas répondu (voir le terminal).", "citation": None}

        # Affiche la réponse de l'assistant
        with st.chat_message("assistant"):
            st.write(resultat.get("reponse"))
            st.caption(f"Mode : {mode} | Citation : {resultat.get('citation')}")

        st.session_state.historique_chat.append({
            "role": "assistant",
            "contenu": resultat.get("reponse"),
            "mode": mode,
            "citation": resultat.get("citation")
        })
with onglet_metriques:
    st.subheader("Fiabilité mesurée du système")
    st.caption("Chiffres mesurés lors d'une exécution (llama3.2 3B local, temperature 0). "
               "Les petits échantillons donnent des ordres de grandeur, pas des mesures précises.")

    st.write("**1. Extraction de champs — F1 par champ (eval_extraction.py)**")
    st.table({
        "Champ": ["numero_facture", "date", "emetteur", "client", "total"],
        "12 factures de test": [1.00, 1.00, 0.91, 1.00, 1.00],
        "8 factures réelles": [0.86, 1.00, 0.86, 0.86, 1.00],
    })
    st.caption("Factures réelles : Free, Netpresse, AWS, Flipkart, QualityHosting, Hetzner, Coolblue, Saeco "
               "(FR/EN/DE/NL). La plupart des erreurs viennent de mises en page complexes "
               "dont la structure est perdue à l'extraction du texte.")

    st.write("**2. Question/Réponse — 60 questions (eval_qa.py, k=5)**")
    st.table({
        "Type": ["lookup (36)", "calcul (12)", "sans réponse (12)"],
        "Direct (bon document)": ["97%", "33%", "83%"],
        "Direct + calcul Python": ["97%", "83%", "83%"],
        "RAG (toutes)": ["42%", "17%", "75%"],
        "RAG (questions identifiantes)": ["67% (8/12)", "22% (2/9)", "1/2"],
    })
    st.caption("Calcul Python : le LLM choisit l'opération, Python calcule. "
               "0 faux déclenchement sur les 48 questions qui ne sont pas des calculs.")

    st.info("ℹ️ Le modèle lit correctement un document donné (97%). La baisse en RAG vient surtout "
            "des questions qui ne précisent pas de quelle facture il s'agit (24 sur 36) : "
            "le mode RAG a besoin de questions précises.")
    st.warning("⚠️ Limites connues : calcul Python branché seulement en mode direct ; "
               "garde-fou anti-hallucination à 83% (ex. émetteur inventé quand il est absent du texte) ; "
               "OCR des reçus scannés : nom du commerce 0% exact (74% de similarité).")
