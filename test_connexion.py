import os
import requests
from dotenv import load_dotenv

# Charge les variables du fichier .env dans le programme
load_dotenv()

# Récupère la valeur de OLLAMA_URL écrite dans le .env
url = os.getenv("OLLAMA_URL")

print(f"J'essaie de contacter : {url}")

try:
    reponse = requests.get(url, timeout=5)
    print("Connexion réussie !")
    print("Réponse du serveur :", reponse.text)
except requests.exceptions.ConnectionError:
    print("Échec de connexion : aucun serveur ne répond à cette adresse.")
except requests.exceptions.Timeout:
    print("Le serveur a mis trop de temps à répondre.")