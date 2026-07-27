import os
import requests
from dotenv import load_dotenv

load_dotenv()
url_base = os.getenv("OLLAMA_URL")

def obtenir_embedding(texte):
    """
    Envoie un texte au modèle d'embeddings multilingue (bge-m3),
    et retourne sa représentation numérique (une liste de nombres).
    """
    reponse = requests.post(
        f"{url_base}/api/embeddings",
        json={
            "model": "bge-m3",
            "prompt": texte
        }
    )

    resultat = reponse.json()
    return resultat["embedding"]


if __name__ == "__main__":
    from text_extract import extraire_texte_pdf
    from chunk import decouper_en_chunks

    texte = extraire_texte_pdf("factures/facture_test.pdf")
    chunks = decouper_en_chunks(texte)

    for i, chunk in enumerate(chunks):
        embedding = obtenir_embedding(chunk)
        print(f"Chunk {i+1} : embedding de {len(embedding)} nombres")
        print(f"Premiers 5 nombres : {embedding[:5]}")