import json
from fields import extraire_champs, valider_champs
from text_extract import extraire_texte_pdf

CHAMPS_A_EVALUER = ["numero_facture", "date", "emetteur", "client", "total"]

def charger_gold_set(chemin="gold_set.json"):
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)

def comparer_valeur(valeur_predite, valeur_gold, champ=None):
    if valeur_predite is None and valeur_gold is None:
        return True
    if valeur_predite is None or valeur_gold is None:
        return False

    if champ == "total":
        try:
            return abs(float(valeur_predite) - float(valeur_gold)) < 0.01
        except (ValueError, TypeError):
            return False

    return str(valeur_predite).strip().lower() == str(valeur_gold).strip().lower()

def evaluer():
    gold_set = charger_gold_set()

    # Un compteur separe pour chaque champ
    stats = {champ: {"vrais_positifs": 0, "faux_positifs": 0, "faux_negatifs": 0} for champ in CHAMPS_A_EVALUER}

    for entree in gold_set:
        chemin_pdf = entree["fichier"]
        print(f"Traitement de {chemin_pdf}...")

        texte = extraire_texte_pdf(chemin_pdf)
        predictions = extraire_champs(texte)
        predictions = valider_champs(predictions)

        if predictions is None:
            print(f"  Echec d'extraction pour {chemin_pdf}, ignore.")
            continue

        for champ in CHAMPS_A_EVALUER:
            valeur_gold = entree.get(champ)
            valeur_predite = predictions.get(champ)
            correct = comparer_valeur(valeur_predite, valeur_gold, champ=champ)

            if valeur_predite is not None and correct:
                stats[champ]["vrais_positifs"] += 1
            elif valeur_predite is not None and not correct:
                stats[champ]["faux_positifs"] += 1
            elif valeur_predite is None and valeur_gold is not None:
                stats[champ]["faux_negatifs"] += 1
            # Cas restant : predit=null ET gold=null -> correct, on ne compte rien (pas d'erreur)

    # Calcul et affichage des scores, champ par champ
    print("\n=== RESULTATS ===")
    print(f"{'Champ':<20} {'Precision':<12} {'Recall':<12} {'F1':<8}")

    for champ in CHAMPS_A_EVALUER:
        vp = stats[champ]["vrais_positifs"]
        fp = stats[champ]["faux_positifs"]
        fn = stats[champ]["faux_negatifs"]

        precision = vp / (vp + fp) if (vp + fp) > 0 else 0
        recall = vp / (vp + fn) if (vp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        print(f"{champ:<20} {precision:<12.2f} {recall:<12.2f} {f1:<8.2f}")


if __name__ == "__main__":
    evaluer()