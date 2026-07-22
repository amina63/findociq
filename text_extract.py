import pdfplumber

def extraire_texte_pdf(chemin_pdf):

    texte_complet = ""

    with pdfplumber.open(chemin_pdf) as pdf:
        print(f"Nombre de pages détectées : {len(pdf.pages)}")

        for numero_page, page in enumerate(pdf.pages, start=1):
            texte_page = page.extract_text()

            if texte_page:
                texte_complet += f"\n--- Page {numero_page} ---\n"
                texte_complet += texte_page
            else:
                print(f"Attention : aucune texte trouvé sur la page {numero_page}")

    return texte_complet


if __name__ == "__main__":
    resultat = extraire_texte_pdf("Rapport Financier Annuel 2024.pdf")

    with open("texte_extrait.txt", "w", encoding="utf-8") as f:
        f.write(resultat)

    print("Texte sauvegardé dans texte_extrait.txt")
    