import pdfplumber

def est_document_scanne(chemin_fichier, seuil_caracteres=20):
    """
    Détermine si un fichier est un PDF numérique (a du texte) ou un scan/image (pas de texte).
    Retourne True si scanné (ou si c'est directement une image), False si numérique.
    """
    extension = chemin_fichier.lower().split(".")[-1]

    # Une image (jpg, png...) est par définition un scan, pas besoin de vérifier
    if extension in ["jpg", "jpeg", "png"]:
        return True

    # Pour un PDF, on teste s'il contient du vrai texte exploitable
    with pdfplumber.open(chemin_fichier) as pdf:
        texte_total = ""
        for page in pdf.pages:
            texte_page = page.extract_text()
            if texte_page:
                texte_total += texte_page

    # Si très peu de texte trouvé, on considère que c'est un scan
    return len(texte_total.strip()) < seuil_caracteres


if __name__ == "__main__":
    fichiers_test = [
        "factures/facture_test.pdf",
        "sroie/000.jpg",
    ]

    for fichier in fichiers_test:
        scanne = est_document_scanne(fichier)
        type_detecte = "SCANNÉ (besoin d'OCR)" if scanne else "NUMÉRIQUE (pdfplumber suffit)"
        print(f"{fichier} → {type_detecte}")