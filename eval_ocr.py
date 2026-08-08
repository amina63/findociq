import json
import glob
from difflib import SequenceMatcher
from ocr import extraire_texte_image
from fields import extraire_champs

CHAMPS_A_EVALUER = ["company", "date", "total"]

SCHEMA_RECU = """
{
  "company": string ou null,
  "date": string ou null,
  "total": number ou null
}
"""

def charger_gold_sroie(dossier="sroie"):
    """Charge les paires (image, gold) pour chaque reçu SROIE téléchargé."""
    paires = []
    for chemin_json in glob.glob(f"{dossier}/*.json"):
        chemin_image = chemin_json.replace(".json", ".jpg")
        with open(chemin_json, "r", encoding="utf-8") as f:
            gold = json.load(f)
        paires.append({"image": chemin_image, "gold": gold})
    return paires


def comparer_texte(valeur_predite, valeur_gold, champ=None):
    if valeur_predite is None or valeur_gold is None:
        return False

    if champ == "total":
        try:
            return abs(float(valeur_predite) - float(valeur_gold)) < 0.01
        except (ValueError, TypeError):
            return False

    return str(valeur_predite).strip().lower() == str(valeur_gold).strip().lower()


def similarite(a, b):
    """Calcule un pourcentage de ressemblance textuelle entre 2 valeurs (0 à 1)."""
    if a is None or b is None:
        return 0.0
    return SequenceMatcher(None, str(a).strip().lower(), str(b).strip().lower()).ratio()


def evaluer_ocr():
    paires = charger_gold_sroie()
    stats = {champ: {"corrects": 0, "total": 0, "similarites": []} for champ in CHAMPS_A_EVALUER}

    for paire in paires:
        print(f"Traitement de {paire['image']}...")

        texte_ocr = extraire_texte_image(paire["image"])
        predictions = extraire_champs(texte_ocr, schema=SCHEMA_RECU)

        if predictions is None:
            continue

        for champ in CHAMPS_A_EVALUER:
            valeur_gold = paire["gold"].get(champ)
            valeur_predite = predictions.get(champ)

            stats[champ]["total"] += 1
            correct = comparer_texte(valeur_predite, valeur_gold, champ=champ)
            if correct:
                stats[champ]["corrects"] += 1

            if champ != "total":
                sim = similarite(valeur_predite, valeur_gold)
                stats[champ]["similarites"].append(sim)
                sim_affichage = f"{sim*100:.0f}%"
            else:
                sim_affichage = "N/A (numérique)"

            statut = "✓" if correct else "✗"
            print(f"  {statut} {champ} | attendu={valeur_gold!r} | obtenu={valeur_predite!r} | similarité={sim_affichage}")

    print("\n=== PRÉCISION OCR (RapidOCR) PAR CHAMP ===")
    print(f"{'Champ':<10} {'Exact':<15} {'Similarité moy.':<15}")
    for champ in CHAMPS_A_EVALUER:
        c = stats[champ]["corrects"]
        t = stats[champ]["total"]
        pourcentage_exact = (c / t * 100) if t > 0 else 0

        if stats[champ]["similarites"]:
            sim_moyenne = sum(stats[champ]["similarites"]) / len(stats[champ]["similarites"]) * 100
            sim_affichage = f"{sim_moyenne:.0f}%"
        else:
            sim_affichage = "N/A"

        print(f"{champ:<10} {f'{c}/{t} ({pourcentage_exact:.0f}%)':<15} {sim_affichage:<15}")


if __name__ == "__main__":
    evaluer_ocr()