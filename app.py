import streamlit as st
import glob
import json
from text_extract import extraire_texte_pdf
from answer_single_doc import repondre_question
from answer import indexer_documents, repondre_avec_rag

st.title("FinDocIQ — Q&A sur documents financiers")

fichiers_disponibles = glob.glob("factures/*.pdf")

mode = st.radio(
    "Choisis un mode :",
    ["Document unique (direct)", "Plusieurs documents (RAG)"]
)

if mode == "Document unique (direct)":
    fichier_choisi = st.selectbox("Choisis un document :", fichiers_disponibles)
    question = st.text_input("Ta question :")

    if st.button("Répondre") and question:
        with st.spinner("Extraction et lecture du document..."):
            texte = extraire_texte_pdf(fichier_choisi)
            resultat = repondre_question(texte, question)

        st.write("**Réponse :**", resultat["reponse"])
        st.write("**Citation source :**", resultat["citation"])

else:
    question = st.text_input("Ta question (recherchée dans tous les documents) :")

    if st.button("Répondre") and question:
        with st.spinner("Indexation de tous les documents et recherche..."):
            index, chunks_avec_source = indexer_documents(fichiers_disponibles)
            resultat = repondre_avec_rag(question, index, chunks_avec_source)

        st.write("**Réponse :**", resultat["reponse"])
        st.write("**Citation source :**", resultat["citation"])