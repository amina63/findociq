import os
import sys
import json
import glob
import argparse

from document import lire_document
from fields import extraire_champs, valider_champs


def traiter_un_document(chemin_fichier):
    """
    Traite un seul document : détecte son type, extrait le texte
    (pdfplumber ou OCR selon le cas), puis extrait les champs structurés.
    Retourne un dictionnaire prêt à être sauvegardé en JSON.
    """
    # PDF numérique -> pdfplumber ; PDF scanné ou image -> OCR (voir document.py)
    texte, methode = lire_document(chemin_fichier)
    champs = valider_champs(extraire_champs(texte))

    return {
        "fichier_source": chemin_fichier,
        "methode_extraction": methode,
        "champs": champs,
    }


def traiter_dossier(dossier_entree, dossier_sortie):
    """
    Parcourt tous les PDF (et images) d'un dossier, les traite un par un,
    et sauvegarde un JSON de résultat pour chacun dans le dossier de sortie.
    """
    os.makedirs(dossier_sortie, exist_ok=True)

    fichiers = []
    for extension in ("pdf", "jpg", "jpeg", "png"):
        fichiers += glob.glob(f"{dossier_entree}/*.{extension}")

    if not fichiers:
        print(f"Aucun fichier trouvé dans {dossier_entree}")
        return

    reussites = 0
    echecs = []

    for chemin_fichier in fichiers:
        nom_base = os.path.splitext(os.path.basename(chemin_fichier))[0]
        chemin_sortie = os.path.join(dossier_sortie, f"{nom_base}.json")

        print(f"Traitement : {chemin_fichier} ...")

        try:
            resultat = traiter_un_document(chemin_fichier)
            with open(chemin_sortie, "w", encoding="utf-8") as f:
                json.dump(resultat, f, indent=2, ensure_ascii=False)
            reussites += 1
        except Exception as e:
            print(f"  Échec sur {chemin_fichier} : {e}")
            echecs.append(chemin_fichier)

    print(f"\nTerminé : {reussites}/{len(fichiers)} documents traités avec succès.")
    if echecs:
        print(f"Échecs ({len(echecs)}) : {echecs}")
    print(f"Résultats sauvegardés dans : {dossier_sortie}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Traite un dossier de PDF/images en lot : extraction + structuration, sauvegardées en JSON."
    )
    parser.add_argument(
        "--input", "-i", default="factures",
        help="Dossier contenant les PDF/images à traiter (défaut : factures)"
    )
    parser.add_argument(
        "--output", "-o", default="output",
        help="Dossier où sauvegarder les JSON résultats (défaut : output)"
    )
    args = parser.parse_args()

    traiter_dossier(args.input, args.output)