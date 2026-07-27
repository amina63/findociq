import os
import json
import requests
from dotenv import load_dotenv
from text_extract import extraire_texte_pdf

load_dotenv()
url_base = os.getenv("OLLAMA_URL")

def repondre_question(texte_document, question):
    """
    Envoie le texte complet d'un document + une question au LLM,
    et exige une réponse ancrée avec citation exacte du passage source.
    """

    prompt = f"""Voici le texte complet d'un document :

{texte_document}

Question : {question}

Réponds UNIQUEMENT à partir de ce qui est explicitement écrit dans le texte ci-dessus.

Règles strictes :
- Si la réponse est présente dans le texte, donne-la, puis cite EXACTEMENT le passage du texte qui la justifie (mot pour mot, sans le reformuler).
- Si la réponse n'est PAS présente dans le texte, réponds exactement : "Cette information n'est pas présente dans ce document."
- N'invente jamais une information qui n'est pas explicitement écrite.

Réponds UNIQUEMENT avec un objet JSON de cette forme :
{{
  "reponse": "ta réponse ici, ou le message d'absence",
  "citation": "le passage exact du texte qui justifie la réponse, ou null si absente"
}}
"""

    reponse = requests.post(
        f"{url_base}/api/generate",
        json={
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0}
        }
    )

    resultat_brut = reponse.json()["response"]

    try:
        resultat = json.loads(resultat_brut)
        return resultat
    except json.JSONDecodeError:
        print("Erreur : réponse non valide.")
        print("Réponse brute :", resultat_brut)
        return None


if __name__ == "__main__":
    texte = extraire_texte_pdf("factures/facture_test.pdf")

    questions_test = [
        "Quel est le numéro de la facture ?",
        "Quel est le numéro de téléphone de l'émetteur ?"
    ]

    for question in questions_test:
        print(f"\n--- Question : {question} ---")
        resultat = repondre_question(texte, question)
        print(json.dumps(resultat, indent=2, ensure_ascii=False))