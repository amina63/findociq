import os
import json
import requests
from dotenv import load_dotenv
from text_extract import extraire_texte_pdf

load_dotenv()
url_base = os.getenv("OLLAMA_URL")

# Le "formulaire à remplir" qu'on impose au modèle
SCHEMA = """
{
  "numero_facture": string ou null,
  "date": string ou null,
  "emetteur": string ou null,
  "client": string ou null,
  "total": number ou null
}
"""

def extraire_champs(texte_document):
    """
    Envoie le texte du document au LLM avec des instructions strictes,
    et retourne les champs extraits sous forme de dictionnaire Python.
    """

    prompt = f"""Voici le texte d'un document financier :

{texte_document}

Extrais les champs suivants et réponds UNIQUEMENT avec un objet JSON valide, rien d'autre (pas de phrase avant ou après) :
{SCHEMA}

Règles strictes :
- Utilise null si une information est absente du document.
- N'invente jamais une valeur qui n'est pas explicitement dans le texte.
- Le champ "total" doit être un nombre, sans le symbole monétaire.
"""

    reponse = requests.post(
        f"{url_base}/api/generate",
        json={
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False,
            "format": "json",
                    "options": {
            "temperature": 0
        }
        }
    )

    resultat_brut = reponse.json()["response"]

    try:
        champs = json.loads(resultat_brut)
        return champs
    except json.JSONDecodeError:
        print("Erreur : le modèle n'a pas renvoyé du JSON valide.")
        print("Réponse brute reçue :", resultat_brut)
        return None


CHAMPS_ATTENDUS = ["numero_facture", "date", "emetteur", "client", "total"]

def valider_champs(champs):
    """S'assure que toutes les clés attendues existent, même si le modèle en a oublié."""
    if champs is None:
        return None
    for champ in CHAMPS_ATTENDUS:
        if champ not in champs:
            champs[champ] = None
    return champs


if __name__ == "__main__":
    fichiers = ["factures/facture_test.pdf", "factures/facture_test_2.pdf", "factures/facture_test_3.pdf"]

    for fichier in fichiers:
        print(f"\n=== {fichier} ===")
        texte = extraire_texte_pdf(fichier)
        champs = extraire_champs(texte)
        champs = valider_champs(champs)
        print(json.dumps(champs, indent=2, ensure_ascii=False))