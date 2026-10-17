import re
import sys
import json
import unicodedata
from fields import extraire_champs, valider_champs
from text_extract import extraire_texte_pdf

CHAMPS_A_EVALUER = ["numero_facture", "date", "emetteur", "client", "total"]

MOIS = {  # français, anglais, allemand, néerlandais
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
    "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "januar": 1, "februar": 2, "marz": 3, "juni": 6, "juli": 7, "oktober": 10, "dezember": 12,
    "januari": 1, "februari": 2, "maart": 3, "mei": 5, "augustus": 8,
}


def charger_gold_set(chemin="gold_set.json"):
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


def normaliser_texte(valeur):
    """'Amazon Web Services, Inc.' -> 'amazon web services inc' (casse, accents, ponctuation ignorés)."""
    t = unicodedata.normalize("NFD", str(valeur).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def normaliser_date(valeur):
    """Ramène une date écrite de façon quelconque à (année, mois, jour), ou None si illisible.
    '02 Juillet 2015', '02/07/2015', '2015-07-02', '7. Mai 2014', 'August 3, 2014' -> même résultat.
    Convention européenne : 05/03/2026 = 5 mars (jour d'abord)."""
    t = normaliser_texte(valeur)
    m = re.fullmatch(r"(\d{4}) (\d{1,2}) (\d{1,2})", t)                 # 2015 07 02 (ISO)
    if m:
        a, mo, j = map(int, m.groups())
        return (a, mo, j) if 1 <= mo <= 12 and 1 <= j <= 31 else None
    m = re.fullmatch(r"(\d{1,2}) (\d{1,2}) (\d{2,4})", t)              # 02 07 2015
    if m:
        j, mo, a = map(int, m.groups())
        a = a + 2000 if a < 100 else a
        return (a, mo, j) if 1 <= mo <= 12 and 1 <= j <= 31 else None
    m = re.fullmatch(r"(\d{1,2}) ([a-z]+) (\d{4})", t)                 # 02 juillet 2015
    if m and m.group(2) in MOIS:
        return (int(m.group(3)), MOIS[m.group(2)], int(m.group(1)))
    m = re.fullmatch(r"([a-z]+) (\d{1,2}) (\d{4})", t)                 # august 3 2014
    if m and m.group(1) in MOIS:
        return (int(m.group(3)), MOIS[m.group(1)], int(m.group(2)))
    return None


def vers_nombre(valeur):
    """29.99 / '29,99' / '1 234,56 €' / '$4.11' -> float, sinon None."""
    if isinstance(valeur, (int, float)) and not isinstance(valeur, bool):
        return float(valeur)
    s = re.sub(r"[^\d,.\-]", "", str(valeur))
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def comparer_valeur(valeur_predite, valeur_gold, champ=None):
    # Le gold peut lister plusieurs formulations acceptées : ["Free SAS", "Free"]
    if isinstance(valeur_gold, list):
        return any(comparer_valeur(valeur_predite, g, champ) for g in valeur_gold)

    if valeur_predite is None and valeur_gold is None:
        return True
    if valeur_predite is None or valeur_gold is None:
        return False

    if champ == "total":
        p, g = vers_nombre(valeur_predite), vers_nombre(valeur_gold)
        return p is not None and g is not None and abs(p - g) < 0.01

    if champ == "date":
        p, g = normaliser_date(valeur_predite), normaliser_date(valeur_gold)
        if p is not None and g is not None:
            return p == g

    return normaliser_texte(valeur_predite) == normaliser_texte(valeur_gold)


def evaluer(chemin_gold="gold_set.json"):
    gold_set = charger_gold_set(chemin_gold)
    print(f"Gold set utilisé : {chemin_gold} ({len(gold_set)} documents)\n")

    # Un compteur separe pour chaque champ
    stats = {champ: {"vrais_positifs": 0, "faux_positifs": 0, "faux_negatifs": 0} for champ in CHAMPS_A_EVALUER}
    erreurs = []

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

            if not correct:
                erreurs.append((chemin_pdf, champ, valeur_gold, valeur_predite))

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

    print(f"\n=== ERREURS ({len(erreurs)}) : attendu -> obtenu ===")
    for fichier, champ, gold, predit in erreurs:
        print(f"  {fichier} | {champ} : {gold} -> {predit}")


if __name__ == "__main__":
    # python eval_extraction.py                  -> 12 factures de test (gold_set.json)
    # python eval_extraction.py gold_real.json   -> 8 factures réelles (factures_reelles/)
    evaluer(sys.argv[1] if len(sys.argv) > 1 else "gold_set.json")
