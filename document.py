"""Point d'entrée unique pour lire un document, quel que soit son type.

- PDF numérique  -> pdfplumber (rapide, exact)
- PDF scanné     -> chaque page est convertie en image, puis lue par OCR (RapidOCR)
- Image jpg/png  -> OCR directement
"""
import os
import tempfile

from router import est_document_scanne
from text_extract import extraire_texte_pdf

EXTENSIONS_IMAGES = (".jpg", ".jpeg", ".png")


def _ocr_image(chemin_image):
    from ocr import extraire_texte_image   # import tardif : le moteur OCR met du temps à charger
    return extraire_texte_image(chemin_image)


def _ocr_pdf_scanne(chemin_pdf, resolution=200):
    import pdfplumber
    morceaux = []
    with pdfplumber.open(chemin_pdf) as pdf:
        for numero, page in enumerate(pdf.pages, start=1):
            image = page.to_image(resolution=resolution).original
            with tempfile.TemporaryDirectory() as dossier:
                chemin_image = os.path.join(dossier, f"page_{numero}.png")
                image.save(chemin_image)
                morceaux.append(f"\n--- Page {numero} ---\n" + _ocr_image(chemin_image))
    return "".join(morceaux)


def lire_document(chemin):
    """Retourne (texte, methode) avec methode = 'pdfplumber' ou 'ocr'."""
    if chemin.lower().endswith(EXTENSIONS_IMAGES):
        return _ocr_image(chemin), "ocr"
    if est_document_scanne(chemin):
        return _ocr_pdf_scanne(chemin), "ocr"
    return extraire_texte_pdf(chemin), "pdfplumber"


if __name__ == "__main__":
    import sys
    texte, methode = lire_document(sys.argv[1])
    print(f"Méthode : {methode}\n{texte[:1500]}")
