import faiss
import numpy as np

def construire_index(embeddings):
    """
    Construit un index FAISS à partir d'une liste d'embeddings.
    Cet index permet ensuite de chercher rapidement les embeddings les plus proches.
    """
    dimension = len(embeddings[0])  # 1024 pour bge-m3
    index = faiss.IndexFlatL2(dimension)

    # FAISS attend un tableau numpy de type float32, pas une simple liste Python
    embeddings_array = np.array(embeddings).astype("float32")
    index.add(embeddings_array)

    return index


def chercher_top_k(index, embedding_question, k=3):
    """
    Cherche les k chunks dont l'embedding est le plus proche de la question.
    Retourne les indices (positions) des meilleurs chunks trouvés.
    """
    embedding_question_array = np.array([embedding_question]).astype("float32")
    distances, indices = index.search(embedding_question_array, k)

    return indices[0]  # on ne garde que la 1ère (et unique) ligne de résultats