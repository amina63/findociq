import json
import glob
from answer import indexer_documents, repondre_avec_rag

def charger_qa_pairs(chemin="qa_pairs.json"):
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


def normaliser_chemin(chemin):
    """Uniformise les séparateurs de chemin (\\ -> /) pour comparer correctement, peu importe l'OS."""
    return chemin.replace("\\", "/")


def comparer_reponse(reponse_obtenue, reponse_attendue, type_question):
    """Compare selon le type de question, avec des règles adaptées."""
    if type_question == "sans_reponse":
        return "n'est pas présente" in reponse_obtenue.lower() or "pas présente" in reponse_obtenue.lower()

    if reponse_attendue is None:
        return False

    # Pour lookup et calcul, on vérifie si la valeur attendue apparaît dans la réponse
    return str(reponse_attendue).strip().lower() in str(reponse_obtenue).strip().lower()


def evaluer_rag(k=3):
    qa_pairs = charger_qa_pairs()
    fichiers = glob.glob("factures/*.pdf")

    print("Indexation de tous les documents...")
    index, chunks_avec_source = indexer_documents(fichiers)
    print(f"{len(chunks_avec_source)} chunks indexés.\n")

    stats_par_type = {
        "lookup": {"hits_retrieval": 0, "reponses_correctes": 0, "total": 0},
        "calcul": {"hits_retrieval": 0, "reponses_correctes": 0, "total": 0},
        "sans_reponse": {"hits_retrieval": 0, "reponses_correctes": 0, "total": 0},
    }

    for entree in qa_pairs:
        fichier_attendu = normaliser_chemin(entree["fichier"])

        for q in entree["questions"]:
            question = q["question"]
            reponse_attendue = q["reponse"]
            type_q = q["type"]

            print(f"[{type_q}] {fichier_attendu} | {question}")

            resultat = repondre_avec_rag(question, index, chunks_avec_source, k=k)

            # Pour vérifier le retrieval, on doit voir quels chunks ont été récupérés
            from embed import obtenir_embedding
            from store import chercher_top_k
            embedding_q = obtenir_embedding(question)
            indices = chercher_top_k(index, embedding_q, k=k)
            fichiers_retrouves = [normaliser_chemin(chunks_avec_source[i]["fichier"]) for i in indices]

            hit_retrieval = fichier_attendu in fichiers_retrouves

            reponse_correcte = comparer_reponse(resultat["reponse"], reponse_attendue, type_q)

            stats_par_type[type_q]["total"] += 1
            if hit_retrieval:
                stats_par_type[type_q]["hits_retrieval"] += 1
            if reponse_correcte:
                stats_par_type[type_q]["reponses_correctes"] += 1

    print("\n=== RÉSULTATS RAG PAR TYPE DE QUESTION ===")
    print(f"{'Type':<15} {'Retrieval hit-rate':<20} {'Answer accuracy':<20}")
    for type_q, s in stats_par_type.items():
        hit_rate = s["hits_retrieval"] / s["total"] * 100 if s["total"] else 0
        accuracy = s["reponses_correctes"] / s["total"] * 100 if s["total"] else 0

        texte_retrieval = f"{s['hits_retrieval']}/{s['total']} ({hit_rate:.0f}%)"
        texte_accuracy = f"{s['reponses_correctes']}/{s['total']} ({accuracy:.0f}%)"

        print(f"{type_q:<15} {texte_retrieval:<20} {texte_accuracy:<20}")


if __name__ == "__main__":
    evaluer_rag(k=5)