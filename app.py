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

DOSSIER_TELEVERSEMENTS = "televersements"   # factures téléversées dans l'app (non versionnées)


def empreinte(chemin):
    """Taille + date de modification : change si le fichier change (sert de clé de cache)."""
    return (os.path.getsize(chemin), os.path.getmtime(chemin))


@st.cache_data
def champs_du_document(chemin, cle):
    return extraire_champs(extraire_texte_pdf(chemin)) or {}


def champs_en_cache(chemin):
    # cle = empreinte : si le fichier est remplacé, l'extraction est refaite ; sinon elle vient du cache
    return champs_du_document(chemin, cle=empreinte(chemin))


@st.cache_resource
def index_de_la_collection(fichiers):
    """Indexe la collection UNE seule fois (et non à chaque question)."""
    return indexer_documents(list(fichiers))


def enregistrer_televersement(fichier_televerse):
    """Copie le PDF téléversé dans televersements/ (seulement s'il est nouveau ou modifié)."""
    os.makedirs(DOSSIER_TELEVERSEMENTS, exist_ok=True)
    chemin = os.path.join(DOSSIER_TELEVERSEMENTS, os.path.basename(fichier_televerse.name))
    contenu = fichier_televerse.getbuffer()
    if not os.path.exists(chemin) or os.path.getsize(chemin) != len(contenu):
        with open(chemin, "wb") as f:
            f.write(contenu)
    return chemin.replace("\\", "/")


def nom_affiche(chemin):
    nom = os.path.basename(chemin)
    return f"📎 {nom} (téléversé)" if chemin.startswith(DOSSIER_TELEVERSEMENTS) else nom


onglet_extraction, onglet_qa, onglet_metriques = st.tabs(
    ["📄 Extraction de champs", "💬 Question/Réponse", "📊 Métriques du système"]
)

# --- ONGLET 1 : Extraction de champs, avec upload ---
with onglet_extraction:
    st.subheader("Téléverse un document pour extraire ses champs")

    fichier_televerse = st.file_uploader("Choisis un PDF", type="pdf")

    if fichier_televerse is not None:
        chemin_televerse = enregistrer_televersement(fichier_televerse)
        st.session_state.dernier_televerse = chemin_televerse

        with st.spinner("Extraction en cours..."):
            champs = champs_en_cache(chemin_televerse)

        if not champs:
            st.error("L'extraction a échoué (voir le terminal). Vérifie qu'Ollama est lancé.")
        else:
            st.success("Extraction terminée — ce document est aussi disponible dans l'onglet Question/Réponse.")

            # Tableau des champs simples (pas les lignes, affichées à part)
            champs_simples = {k: v for k, v in champs.items() if k != "lignes"}
            st.table(champs_simples)

            if champs.get("lignes"):
                st.write("**Lignes détaillées :**")
                st.table(champs["lignes"])

with onglet_qa:
    st.subheader("Pose une question sur tes documents")

    # Factures de démonstration + factures téléversées dans l'onglet 1
    fichiers_disponibles = [f.replace("\\", "/") for f in
                            sorted(glob.glob(f"{DOSSIER_TELEVERSEMENTS}/*.pdf")) + sorted(glob.glob("factures/*.pdf"))]

    mode = st.radio(
        "Mode :",
        ["Document unique (direct)", "Plusieurs documents (RAG)"]
    )

    fichier_choisi = None
    if mode == "Document unique (direct)":
        dernier = st.session_state.get("dernier_televerse")
        position = fichiers_disponibles.index(dernier) if dernier in fichiers_disponibles else 0
        fichier_choisi = st.selectbox("Choisis un document :", fichiers_disponibles,
                                      index=position, format_func=nom_affiche)

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
                resultat = repondre_calcul(question, champs_en_cache(fichier_choisi)) or repondre_question(texte, question)

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

    st.write("**3. Question/Réponse — 24 questions sur les 8 factures réelles (jamais vues)**")
    st.table({
        "Type": ["lookup (8)", "calcul (8)", "sans réponse (8)"],
        "Direct (bon document)": ["88%", "50%", "75%"],
        "Direct + calcul Python": ["88%", "50%", "75%"],
        "RAG": ["62%", "25%", "50%"],
    })
    st.caption("Sur les factures réelles, le calcul Python n'apporte pas de gain : le calcul est toujours exact, "
               "mais le plan (opération, lignes choisies) ou les lignes extraites sont souvent faux.")

    st.info("ℹ️ Le modèle lit correctement un document donné (97%). La baisse en RAG vient surtout "
            "des questions qui ne précisent pas de quelle facture il s'agit (24 sur 36) : "
            "le mode RAG a besoin de questions précises.")
    st.warning("⚠️ Limites connues : en RAG, risque de réponse tirée d'une autre facture ; "
               "calcul Python branché seulement en mode direct et peu efficace sur les factures réelles ; "
               "garde-fou anti-hallucination à 83% (ex. émetteur inventé quand il est absent du texte) ; "
               "OCR des reçus scannés : nom du commerce 0% exact (74% de similarité).")
