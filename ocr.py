from rapidocr_onnxruntime import RapidOCR

# On charge le moteur OCR une seule fois (pas à chaque appel, ce serait lent)
moteur_ocr = RapidOCR()

def extraire_texte_image(chemin_image):
    """
    Utilise RapidOCR pour lire le texte visible dans une image scannée.
    Retourne le texte complet reconnu.
    """
    resultats, _ = moteur_ocr(chemin_image)

    if resultats is None:
        return ""

    # Chaque élément de resultats contient [position, texte_reconnu, score_confiance]
    lignes_texte = [ligne[1] for ligne in resultats]
    texte_complet = "\n".join(lignes_texte)

    return texte_complet


if __name__ == "__main__":
    texte = extraire_texte_image("sroie/000.jpg")
    print("=== Texte reconnu par OCR ===")
    print(texte)