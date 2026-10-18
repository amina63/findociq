"""FinDocIQ — interface Streamlit.

Lancer : streamlit run app.py
Trois onglets : Extraction de champs | Question/Réponse | Métriques mesurées.
"""
import os
import glob
import json

import requests
import pandas as pd
import streamlit as st

from document import lire_document
from fields import extraire_champs, valider_champs
from answer_single_doc import repondre_question
from answer import indexer_documents, repondre_avec_rag
from calcul import repondre_calcul

st.set_page_config(page_title="FinDocIQ", page_icon="📑", layout="wide")

# Pleine largeur : le paramètre a changé de nom selon la version de Streamlit
_version = tuple(int(x) for x in st.__version__.split(".")[:2])
LARGE = {"width": "stretch"} if _version >= (1, 46) else {"use_container_width": True}

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DOSSIER_TELEVERSEMENTS = "televersements"      # documents téléversés dans l'app (non versionnés)
EXTENSIONS = ("pdf", "jpg", "jpeg", "png")
LIBELLES = {"numero_facture": "N° de facture", "date": "Date", "emetteur": "Émetteur",
            "client": "Client", "total": "Total"}


# ----------------------------------------------------------------------------------------------
# Fonctions utilitaires (mises en cache : un document n'est lu et analysé qu'une seule fois)
# ----------------------------------------------------------------------------------------------
def empreinte(chemin):
    """Taille + date de modification : change si le fichier change (sert de clé de cache)."""
    return (os.path.getsize(chemin), os.path.getmtime(chemin))


@st.cache_data(show_spinner=False)
def texte_du_document(chemin, cle):
    return lire_document(chemin)                 # -> (texte, "pdfplumber" ou "ocr")


@st.cache_data(show_spinner=False)
def champs_du_document(chemin, cle):
    texte, _ = texte_du_document(chemin, cle)
    return valider_champs(extraire_champs(texte)) or {}


@st.cache_data(show_spinner=False)
def apercu_du_document(chemin, cle):
    """Image de la première page, pour l'afficher à côté des champs extraits."""
    try:
        if chemin.lower().endswith(".pdf"):
            import pdfplumber
            with pdfplumber.open(chemin) as pdf:
                return pdf.pages[0].to_image(resolution=110).original
        from PIL import Image
        return Image.open(chemin)
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def index_de_la_collection(fichiers):
    """Indexe la collection UNE seule fois (et non à chaque question)."""
    return indexer_documents(list(fichiers))


@st.cache_data(ttl=30, show_spinner=False)
def etat_ollama():
    """Vérifie que le serveur Ollama répond et que les deux modèles sont installés."""
    try:
        modeles = [m["name"] for m in requests.get(f"{OLLAMA_URL}/api/tags", timeout=3).json().get("models", [])]
        return True, {nom: any(m.startswith(nom) for m in modeles) for nom in ("llama3.2", "bge-m3")}
    except (requests.RequestException, ValueError):
        return False, {}


def enregistrer_televersement(fichier_televerse):
    """Copie le fichier téléversé dans televersements/ (seulement s'il est nouveau ou modifié)."""
    os.makedirs(DOSSIER_TELEVERSEMENTS, exist_ok=True)
    chemin = os.path.join(DOSSIER_TELEVERSEMENTS, os.path.basename(fichier_televerse.name))
    contenu = fichier_televerse.getbuffer()
    if not os.path.exists(chemin) or os.path.getsize(chemin) != len(contenu):
        with open(chemin, "wb") as f:
            f.write(contenu)
    return chemin.replace("\\", "/")


def lister(dossier, extensions):
    fichiers = []
    for ext in extensions:
        fichiers += glob.glob(f"{dossier}/*.{ext}")
    return sorted(f.replace("\\", "/") for f in fichiers)


def nom_affiche(chemin):
    nom = os.path.basename(chemin)
    return f"📎 {nom} (téléversé)" if chemin.startswith(DOSSIER_TELEVERSEMENTS) else nom


def formater_montant(valeur, devise):
    try:
        texte = f"{float(valeur):,.2f}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"
    return f"{texte} {devise or ''}".strip()


# ----------------------------------------------------------------------------------------------
# Barre latérale : état du système
# ----------------------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📑 FinDocIQ")
    st.caption("Extraction et questions-réponses sur documents financiers.")

    connecte, modeles = etat_ollama()
    if not connecte:      # rien n'est affiché quand tout fonctionne
        st.error(f"Ollama ne répond pas ({OLLAMA_URL}). Lance l'application Ollama, puis recharge la page.", icon="🛑")
    elif not all(modeles.values()):
        manquants = ", ".join(nom for nom, present in modeles.items() if not present)
        st.warning(f"Modèle manquant : {manquants} (ollama pull {manquants.split(',')[0]})", icon="⚠️")

    st.divider()
    st.markdown("**Confidentialité**")
    st.caption("🔒 Tout est traité sur cette machine (Ollama local). Aucun document n'est envoyé "
               "à un service externe.")
    st.divider()
    st.caption("Modèles : llama3.2 (3B) · bge-m3 · RapidOCR")


# ----------------------------------------------------------------------------------------------
# En-tête
# ----------------------------------------------------------------------------------------------
st.title("📑 FinDocIQ")
st.caption("Téléverse une facture, récupère ses champs en JSON, puis pose tes questions : "
           "chaque réponse est justifiée par une citation du document.")

onglet_extraction, onglet_qa, onglet_metriques = st.tabs(
    ["📄 Extraction de champs", "💬 Question / Réponse", "📊 Fiabilité mesurée"])


# ----------------------------------------------------------------------------------------------
# ONGLET 1 : extraction de champs
# ----------------------------------------------------------------------------------------------
with onglet_extraction:
    fichier_televerse = st.file_uploader(
        "Téléverse une facture (PDF numérique, PDF scanné ou image)", type=list(EXTENSIONS))

    if fichier_televerse is not None:
        chemin = enregistrer_televersement(fichier_televerse)
        st.session_state.dernier_televerse = chemin
        cle = empreinte(chemin)

        with st.spinner("Lecture du document et extraction des champs…"):
            texte, methode = texte_du_document(chemin, cle)
            champs = champs_du_document(chemin, cle)

        col_doc, col_champs = st.columns([2, 3], gap="large")

        with col_doc:
            st.markdown("**Document**")
            apercu = apercu_du_document(chemin, cle)
            if apercu is not None:
                st.image(apercu)
            st.caption("📄 PDF numérique — texte lu par pdfplumber" if methode == "pdfplumber"
                       else "🔍 Document scanné — texte lu par OCR (RapidOCR)")

        with col_champs:
            if not champs:
                st.error("L'extraction a échoué. Vérifie qu'Ollama est lancé (barre latérale).")
            else:
                st.markdown("**Champs extraits**")
                cartes = st.columns(2)
                for i, (cle_champ, libelle) in enumerate(LIBELLES.items()):
                    valeur = champs.get(cle_champ)
                    if cle_champ == "total" and valeur is not None:
                        valeur = formater_montant(valeur, champs.get("devise"))
                    with cartes[i % 2].container(border=True):
                        st.caption(libelle)
                        st.markdown(f"**{valeur}**" if valeur not in (None, "") else "— *non trouvé*")

                lignes = [l for l in (champs.get("lignes") or []) if isinstance(l, dict)]
                if lignes:
                    st.markdown("**Lignes de la facture**")
                    def nombre(v, decimales=2):
                        try:
                            v = float(str(v).replace(",", "."))
                        except (TypeError, ValueError):
                            return "—"                       # valeur absente ou illisible
                        return f"{v:g}" if decimales == 0 else f"{v:,.{decimales}f}".replace(",", " ")
                    tableau = pd.DataFrame([{
                        "Description": l.get("description") or "—",
                        "Qté": nombre(l.get("quantite"), 0),
                        "Prix unitaire": nombre(l.get("prix_unitaire")),
                        "Montant": nombre(l.get("montant")),
                    } for l in lignes])
                    st.dataframe(tableau, hide_index=True, **LARGE)

                st.download_button("⬇️ Télécharger le JSON", file_name=f"{os.path.splitext(os.path.basename(chemin))[0]}.json",
                                   data=json.dumps(champs, indent=2, ensure_ascii=False), mime="application/json")

        with st.expander("Voir le texte lu dans le document"):
            st.text(texte if texte.strip() else "(aucun texte trouvé)")


# ----------------------------------------------------------------------------------------------
# ONGLET 2 : question / réponse
# ----------------------------------------------------------------------------------------------
with onglet_qa:
    if "historique_chat" not in st.session_state:
        st.session_state.historique_chat = []

    documents = lister(DOSSIER_TELEVERSEMENTS, EXTENSIONS) + lister("factures", ["pdf"]) \
        + lister("factures_reelles", ["pdf"])
    documents_pdf = [d for d in documents if d.lower().endswith(".pdf")]

    col_reglages, col_chat = st.columns([1, 2], gap="large")

    with col_reglages:
        mode = st.radio("Où chercher la réponse ?",
                        ["Dans un document précis", "Dans toute la collection (RAG)"],
                        help="Document précis : le modèle lit tout le document choisi (le plus fiable). "
                             "Collection : il cherche d'abord les passages utiles parmi tous les PDF.")
        fichier_choisi = None
        if mode == "Dans un document précis":
            dernier = st.session_state.get("dernier_televerse")
            position = documents.index(dernier) if dernier in documents else 0
            fichier_choisi = st.selectbox("Document", documents, index=position, format_func=nom_affiche)
        else:
            st.caption(f"{len(documents_pdf)} documents indexés. Précise le fournisseur dans ta question "
                       "(ex. « sur la facture Hetzner… ») : sinon la réponse peut venir d'un autre document.")

        st.markdown("**Exemples**")
        st.caption("• Quel est le numéro de facture ?\n\n• Quelle est la différence entre les deux "
                   "premières lignes ?\n\n• Quel est le numéro de téléphone du client ?")
        if st.button("🗑️ Effacer la conversation", **LARGE):
            st.session_state.historique_chat = []
            st.rerun()

    with col_chat:
        for message in st.session_state.historique_chat:
            with st.chat_message(message["role"]):
                st.markdown(message["contenu"])
                if message["role"] == "assistant":
                    st.caption(message["source"])
                    if message.get("calcul"):
                        st.caption(f"🧮 {message['calcul']}")
                    if message.get("citation"):
                        with st.expander("Justification (citation du document)"):
                            st.write(message["citation"])

        question = st.chat_input("Pose ta question…")

    if question:
        if mode == "Dans un document précis" and fichier_choisi is None:
            st.warning("Aucun document disponible.")
        else:
            with st.spinner("Recherche de la réponse…"):
                if mode == "Dans un document précis":
                    cle = empreinte(fichier_choisi)
                    texte, _ = texte_du_document(fichier_choisi, cle)
                    resultat_calcul = repondre_calcul(question, champs_du_document(fichier_choisi, cle))
                    resultat = resultat_calcul or repondre_question(texte, question)
                    source = (f"🧮 Calcul fait par Python · {nom_affiche(fichier_choisi)}" if resultat_calcul
                              else f"📄 Lecture du document · {nom_affiche(fichier_choisi)}")
                else:
                    index, chunks = index_de_la_collection(tuple(documents_pdf))
                    resultat = repondre_avec_rag(question, index, chunks)
                    source = "🔎 Recherche dans la collection (RAG)"

            resultat = resultat or {"reponse": "⚠️ Le modèle n'a pas répondu (voir le terminal).", "citation": None}
            st.session_state.historique_chat += [
                {"role": "user", "contenu": question},
                {"role": "assistant", "contenu": str(resultat.get("reponse")), "source": source,
                 "citation": resultat.get("citation"), "calcul": resultat.get("calcul")},
            ]
            st.rerun()      # réaffiche l'historique au-dessus de la zone de saisie


# ----------------------------------------------------------------------------------------------
# ONGLET 3 : fiabilité mesurée
# ----------------------------------------------------------------------------------------------
with onglet_metriques:
    pct = st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")

    st.markdown("#### 1. Extraction de champs — F1 par champ")
    st.dataframe(pd.DataFrame({
        "Champ": ["N° de facture", "Date", "Émetteur", "Client", "Total"],
        "12 factures de test": [1.00, 1.00, 0.91, 1.00, 1.00],
        "8 factures réelles": [0.86, 1.00, 0.86, 0.86, 1.00],
    }), hide_index=True, **LARGE,
        column_config={"12 factures de test": pct, "8 factures réelles": pct})
    st.caption("Factures réelles : Free, Netpresse, AWS, Flipkart, QualityHosting, Hetzner, Coolblue, Saeco. "
               "Les erreurs viennent surtout de mises en page dont la structure est perdue à l'extraction du texte.")

    st.markdown("#### 2. Question / réponse — taux de bonnes réponses")
    colonnes_qa = {c: pct for c in ["Bon document", "+ calcul Python", "RAG"]}
    st.markdown("**12 factures de test — 60 questions**")
    st.dataframe(pd.DataFrame({
        "Type": ["Lecture", "Calcul", "Sans réponse"],
        "Bon document": [0.97, 0.33, 0.83],
        "+ calcul Python": [0.97, 0.83, 0.83],
        "RAG": [0.42, 0.17, 0.75],
    }), hide_index=True, **LARGE, column_config=colonnes_qa)
    st.markdown("**8 factures réelles — 24 questions jamais vues**")
    st.dataframe(pd.DataFrame({
        "Type": ["Lecture", "Calcul", "Sans réponse"],
        "Bon document": [0.88, 0.50, 0.75],
        "+ calcul Python": [0.88, 0.50, 0.75],
        "RAG": [0.62, 0.25, 0.50],
    }), hide_index=True, **LARGE, column_config=colonnes_qa)
