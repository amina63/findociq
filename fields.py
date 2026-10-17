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
  "total": number ou null,
  "devise": string ou null,
  "lignes": [{"description": "string", "quantite": "number ou null",
              "prix_unitaire": "number ou null", "montant": "number"}]
}
"""

def extraire_champs(texte_document, schema=None):
    """
    Envoie le texte du document au LLM avec des instructions strictes,
    et retourne les champs extraits sous forme de dictionnaire Python.
    Si aucun schema n'est précisé, utilise le schéma facture par défaut (SCHEMA).
    """

    if schema is None:
        schema = SCHEMA

    prompt = f"""Voici le texte d'un document financier :

{texte_document}

Extrais les champs suivants et réponds UNIQUEMENT avec un objet JSON valide, rien d'autre (pas de phrase avant ou après) :
{schema}

Règles strictes :
- Utilise null si une information est absente du document.
- N'invente jamais une valeur qui n'est pas explicitement dans le texte.
- Le champ "total" doit être un nombre, sans le symbole monétaire.
- Pour un champ "company" ou "emetteur" : c'est le nom du COMMERCE/MAGASIN qui émet le document, généralement en gros caractères, souvent accompagné de mentions comme "SDN BHD", "SARL", ou une adresse juste en dessous. Ce n'est PAS un nom de personne isolé en première ligne (comme un caissier).
"""

    try:
        reponse = requests.post(
            f"{url_base}/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                    "num_predict": 1024   # limite de longueur : évite une génération sans fin
                }
            },
            timeout=300                   # limite de temps : 5 min maximum par appel
        )
        donnees = reponse.json()
    except (requests.RequestException, ValueError) as e:
        print("Erreur Ollama (extraction des champs) :", e)
        return None

    if "response" not in donnees:
        print("Erreur Ollama :", donnees.get("error", donnees))
        return None
    resultat_brut = donnees["response"]

    try:
        champs = json.loads(resultat_brut)
        return champs
    except json.JSONDecodeError:
        print("Erreur : le modèle n'a pas renvoyé du JSON valide.")
        print("Réponse brute reçue :", resultat_brut)
        return None


CHAMPS_ATTENDUS = ["numero_facture", "date", "emetteur", "client", "total"]

VALEURS_VIDES = {"", "null", "none", "n/a", "na", "-"}


def valider_champs(champs):
    """S'assure que toutes les clés attendues existent, même si le modèle en a oublié.
    Convertit aussi le TEXTE "null" (ou "None", "") en vraie valeur vide None :
    le modèle écrit parfois "null" entre guillemets au lieu de null."""
    if champs is None:
        return None
    for champ in CHAMPS_ATTENDUS:
        valeur = champs.get(champ)
        if isinstance(valeur, str) and valeur.strip().lower() in VALEURS_VIDES:
            valeur = None
        champs[champ] = valeur
    return champs


if __name__ == "__main__":
    fichiers = ["factures/facture_test.pdf", "factures/facture_test_2.pdf", "factures/facture_test_3.pdf"]

    for fichier in fichiers:
        print(f"\n=== {fichier} ===")
        texte = extraire_texte_pdf(fichier)
        champs = extraire_champs(texte)
        champs = valider_champs(champs)
        print(json.dumps(champs, indent=2, ensure_ascii=False))