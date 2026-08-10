def verifier_total(lignes, total_annonce, tolerance=0.01):
    """
    Vérifie que le total annoncé correspond à la somme des montants des lignes.
    'lignes' est une liste de dictionnaires avec au moins une clé 'montant'.
    """
    somme_calculee = sum(ligne["montant"] for ligne in lignes)
    coherent = abs(somme_calculee - total_annonce) < tolerance

    return {
        "coherent": coherent,
        "somme_calculee": somme_calculee,
        "total_annonce": total_annonce,
        "difference": round(somme_calculee - total_annonce, 2)
    }


def calculer_part_de_chaque_ligne(lignes, total):
    """
    Calcule, pour chaque ligne, le pourcentage qu'elle représente du total.
    """
    resultats = []
    for ligne in lignes:
        part = (ligne["montant"] / total * 100) if total else 0
        resultats.append({
            "description": ligne["description"],
            "montant": ligne["montant"],
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

    if lignes and total_annonce is not None:
        verification = verifier_total(lignes, total_annonce)
        print("=== Vérification du total ===")
        print(verification)

        print("\n=== Part de chaque ligne dans le total ===")
        parts = calculer_part_de_chaque_ligne(lignes, total_annonce)
        for p in parts:
            print(p)
    else:
        print("Impossible de vérifier : lignes ou total manquants.")