"""Diagnostic (pas d'ajustement) : pour chaque question de calcul, affiche ce que voit le
planificateur (les champs extraits), le plan qu'il choisit et le résultat de Python.
Sert à EXPLIQUER les erreurs dans le rapport, pas à modifier le système.

python diagnostic_calcul.py qa_real.json
"""
import sys
import json
from text_extract import extraire_texte_pdf
from fields import extraire_champs
from calcul import ressemble_a_un_calcul, planifier, executer_plan, decrire_champs, formater

chemin_qa = sys.argv[1] if len(sys.argv) > 1 else "qa_real.json"
resultats = []
for entree in json.load(open(chemin_qa, encoding="utf-8")):
    calculs = [q for q in entree["questions"] if q["type"] == "calcul"]
    if not calculs:
        continue
    champs = extraire_champs(extraire_texte_pdf(entree["fichier"])) or {}
    for q in calculs:
        filtre = ressemble_a_un_calcul(q["question"])
        plan = planifier(q["question"], champs) if filtre else None
        res = executer_plan(plan, champs) if plan else None
        obtenu = f"{res[1]} = {formater(res[0])}" if res else None
        print(f"\n=== {entree['fichier']}\nQuestion : {q['question']}\nAttendu  : {q['reponse']}")
        print("Champs vus par le planificateur :\n  " + decrire_champs(champs).replace("\n", "\n  "))
        print(f"Filtre : {'déclenché' if filtre else 'non déclenché'} | Plan : {plan} | Python : {obtenu}")
        resultats.append({"fichier": entree["fichier"], "question": q["question"], "attendu": q["reponse"],
                          "champs": champs, "filtre": filtre, "plan": plan, "resultat_python": obtenu})

sortie = f"diagnostic_calcul_{chemin_qa.replace('.json', '')}.json"
with open(sortie, "w", encoding="utf-8") as f:
    json.dump(resultats, f, indent=2, ensure_ascii=False)
print(f"\nDétail sauvegardé : {sortie}")
