import json
from answer_single_doc import repondre_question
from text_extract import extraire_texte_pdf

MESSAGE_ATTENDU = "Cette information n'est pas présente dans ce document."

def charger_qa_pairs(chemin="qa_pairs.json"):
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)

def tester_guardrail():
    qa_pairs = charger_qa_pairs()

    reussites = 0
    echecs = []

    for entree in qa_pairs:
        chemin_pdf = entree["fichier"]
        texte = extraire_texte_pdf(chemin_pdf)

        # On ne garde que la question de type "sans_reponse" pour ce document
        question_sans_reponse = next(
            (q for q in entree["questions"] if q["type"] == "sans_reponse"),
            None
        )

        if question_sans_reponse is None:
            continue

        resultat = repondre_question(texte, question_sans_reponse["question"])

        if resultat and resultat.get("reponse", "").strip() == MESSAGE_ATTENDU:
            reussites += 1
        else:
            echecs.append({
                "fichier": chemin_pdf,
                "question": question_sans_reponse["question"],
                "reponse_obtenue": resultat.get("reponse") if resultat else None
            })

    total = reussites + len(echecs)
    print(f"\nGuardrail : {reussites}/{total} réponses correctement refusées ({reussites/total*100:.0f}%)")

    if echecs:
        print("\n=== ECHECS DU GARDE-FOU ===")
        for e in echecs:
            print(f"{e['fichier']} | Q: {e['question']}")
            print(f"  Réponse obtenue au lieu du refus : {e['reponse_obtenue']}")


if __name__ == "__main__":
    tester_guardrail()