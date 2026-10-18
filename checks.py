def _nombre(valeur):
    """350 / 350.0 / '350,00' -> 350.0 ; None ou illisible -> None."""
    if valeur is None or isinstance(valeur, bool):
        return None
    if isinstance(valeur, (int, float)):
        return float(valeur)
    try:
        return float(str(valeur).replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def verifier_total(lignes, total_annonce, tolerance=0.01):
    """
    Vérifie que le total annoncé correspond à la somme des montants des lignes.
    'lignes' est une liste de dictionnaires avec au moins une clé 'montant'.
    Retourne None si la vérification est impossible (total ou montants manquants).
    """
    total = _nombre(total_annonce)
    montants = [_nombre(l.get("montant")) for l in (lignes or []) if isinstance(l, dict)]
    if total is None or not montants or any(m is None for m in montants):
        return None

    somme_calculee = round(sum(montants), 2)
    return {
        "coherent": abs(somme_calculee - total) < tolerance,
        "somme_calculee": somme_calculee,
        "total_annonce": total,
        "difference": round(somme_calculee - total, 2)
    }


def calculer_part_de_chaque_ligne(lignes, total):
    """
    Calcule, pour chaque ligne, le pourcentage qu'elle représente du total.
    """
    total = _nombre(total)
    resultats = []
    for ligne in lignes or []:
        montant = _nombre(ligne.get("montant"))
        part = (montant / total * 100) if (total and montant is not None) else 0
        resultats.append({
            "description": ligne.get("description"),
            "montant": montant,
            "part_du_total": round(part, 1)
        })
    return resultats


if __name__ == "__main__":
    from text_extract import extraire_texte_pdf
    from fields import extraire_champs

    fichier = "factures/facture_test.pdf"
    texte = extraire_texte_pdf(fichier)
    champs = extraire_champs(texte)

    lignes = champs.get("lignes", [])
    total_annonce = champs.get("total")

    print(f"=== Document : {fichier} ===")
    print(f"Lignes extraites : {lignes}")
    print(f"Total annoncé : {total_annonce}\n")

    verification = verifier_total(lignes, total_annonce)
    if verification is not None:
        print("=== Vérification du total ===")
        print(verification)

        print("\n=== Part de chaque ligne dans le total ===")
        parts = calculer_part_de_chaque_ligne(lignes, total_annonce)
        for p in parts:
            print(p)
    else:
        print("Impossible de vérifier : lignes ou total manquants.")