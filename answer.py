from text_extract import extraire_texte_pdf
from chunk import decouper_en_chunks
from embed import obtenir_embedding
from store import construire_index, chercher_top_k
import json

def indexer_documents(liste_fichiers):
    """
    Prend une liste de fichiers PDF, les découpe en chunks,
    calcule leurs embeddings, et construit l'index FAISS.
    Retourne l'index ET la liste parallèle (position -> texte + source).
    """
    chunks_avec_source = []
    embeddings = []

    for fichier in liste_fichiers:
        texte = extraire_texte_pdf(fichier)
        chunks = decouper_en_chunks(texte)

        for chunk in chunks:
            embedding = obtenir_embedding(chunk)
            embeddings.append(embedding)
            chunks_avec_source.append({"texte": chunk, "fichier": fichier})

    index = construire_index(embeddings)
    return index, chunks_avec_source


def repondre_avec_rag(question, index, chunks_avec_source, k=5):
    """
    Cherche les k chunks les plus pertinents pour la question,
    puis demande au LLM de répondre en se basant uniquement sur eux.
    """
    embedding_question = obtenir_embedding(question)
    indices_trouves = chercher_top_k(index, embedding_question, k=k)

    chunks_pertinents = [chunks_avec_source[i] for i in indices_trouves]
    contexte = "\n\n".join(
        f"[Source: {c['fichier']}]\n{c['texte']}" for c in chunks_pertinents
    )

    from answer_single_doc import repondre_question
    return repondre_question(contexte, question)


if __name__ == "__main__":
    import glob
    fichiers = glob.glob("factures/*.pdf")

    print("Indexation en cours...")
    index, chunks_avec_source = indexer_documents(fichiers)
    print(f"{len(chunks_avec_source)} chunks indexés depuis {len(fichiers)} documents.\n")

    question = "Quel est le prix d'un câble HDMI ?"
    resultat = repondre_avec_rag(question, index, chunks_avec_source)
    print(json.dumps(resultat, indent=2, ensure_ascii=False))