"""Calculs financiers : le LLM PLANIFIE, Python CALCULE.

Le LLM (llama3.2 3B) se trompe souvent sur l'arithmétique. Ici on ne lui demande
jamais de calculer : il choisit seulement une opération et ses opérandes
(des références vers les champs extraits par fields.py). Python fait le calcul exact.
"""
import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODELE = "llama3.2"

# Filtre rapide : on n'appelle le planificateur que si la question ressemble à un calcul.
# "Combien de livres ont été achetés ?" est une LECTURE (pas un calcul) : volontairement exclu.
MOTS_CALCUL = re.compile(
    r"diff[ée]rence|somme|total des|combin[ée]|serait|si une|une seule|chacun|"
    r"par unit[ée]|moyenne|pourcentage|%|remise|plus cher|moins cher|combien co[uû]t|"
    r"additionn|multipli|divis|soustrai|"
    r"would|difference|sum of|in total|each|average", re.I)


def ressemble_a_un_calcul(question):
    return MOTS_CALCUL.search(question) is not None


def _lignes(champs):
    lignes = champs.get("lignes") or []
    return [l for l in lignes if isinstance(l, dict)]


def _nombre(x):
    """Convertit 350 / 350.0 / '350,00' / '1 200.50' en float, sinon None."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = re.sub(r"[^\d,.\-]", "", str(x)).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def resoudre_operande(op, champs):
    """'total' | 'lignes[2]' | 'lignes[2].quantite' | 12.5 | '12.5' -> float ou None."""
    if isinstance(op, (int, float)) and not isinstance(op, bool):
        return float(op)
    if not isinstance(op, str):
        return None
    op = op.strip()
    if op == "total":
        return _nombre(champs.get("total"))
    m = re.fullmatch(r"lignes\[(\d+)\](?:\.(montant|quantite|prix_unitaire))?", op)
    if m:
        i, cle = int(m.group(1)), m.group(2) or "montant"
        lignes = _lignes(champs)
        return _nombre(lignes[i].get(cle)) if i < len(lignes) else None
    return _nombre(op)


def executer_plan(plan, champs):
    """Exécute {'operation': ..., 'operandes': [...]}. Retourne (valeur, expression) ou None."""
    if not isinstance(plan, dict):
        return None
    operation = plan.get("operation")

    if operation == "somme_lignes":
        vals = [_nombre(l.get("montant")) for l in _lignes(champs)]
        if not vals or any(v is None for v in vals):
            return None
        return sum(vals), " + ".join(f"{v:g}" for v in vals)

    ops = plan.get("operandes") or []
    if not isinstance(ops, list):
        return None
    vals = [resoudre_operande(o, champs) for o in ops]
    if not vals or any(v is None for v in vals):
        return None

    if operation == "somme":
        return sum(vals), " + ".join(f"{v:g}" for v in vals)
    if len(vals) != 2:
        return None
    a, b = vals
    if operation == "difference":                     # écart toujours positif
        return abs(a - b), f"|{a:g} - {b:g}|"
    if operation == "soustraction":
        return a - b, f"{a:g} - {b:g}"
    if operation == "multiplication":
        return a * b, f"{a:g} × {b:g}"
    if operation == "division":
        return (a / b, f"{a:g} / {b:g}") if b != 0 else None
    if operation == "part_en_pourcentage":            # a représente quel % de b
        return (a / b * 100, f"{a:g} / {b:g} × 100") if b != 0 else None
    if operation == "pourcentage_de":                 # b % de a
        return a * b / 100, f"{a:g} × {b:g} / 100"
    if operation == "ajout_pourcentage":              # a augmenté de b % (ex. TVA)
        return a * (1 + b / 100), f"{a:g} × (1 + {b:g}/100)"
    return None


def decrire_champs(champs):
    """Présente les champs avec des références explicites, pour que le LLM n'ait pas à compter."""
    lignes_txt = [f"total = {champs.get('total')}"]
    for i, l in enumerate(_lignes(champs)):
        lignes_txt.append(
            f"lignes[{i}] = {l.get('description')} | quantite = {l.get('quantite')} | "
            f"prix_unitaire = {l.get('prix_unitaire')} | montant = {l.get('montant')}")
    return "\n".join(lignes_txt)


CONSIGNE = """Tu es un planificateur de calcul. Tu NE CALCULES PAS toi-même.

Valeurs disponibles dans le document :
{champs}

Question : {question}

Choisis UNE opération et ses deux opérandes. Réponds UNIQUEMENT en JSON :
{{"operation": "...", "operandes": [..., ...]}}

Opérations possibles :
- "difference" : écart entre deux montants (a et b)
- "somme" : addition de plusieurs valeurs
- "somme_lignes" : somme de tous les montants des lignes (operandes = [])
- "multiplication" : a × b (ex. prix unitaire × quantité)
- "division" : a / b (ex. prix d'un lot / nombre d'unités)
- "pourcentage_de" : b % de a (ex. 10% du total -> ["total", 10])
- "ajout_pourcentage" : a augmenté de b % (ex. total TTC avec TVA 20% -> ["total", 20])
- "part_en_pourcentage" : a représente quel pourcentage de b
- "aucune" : la question n'est pas un calcul, ou les valeurs nécessaires manquent

Opérandes possibles : "total", "lignes[i]" (montant de la ligne i),
"lignes[i].quantite", "lignes[i].prix_unitaire", ou un nombre écrit dans la question.
"""


def planifier(question, champs):
    prompt = CONSIGNE.format(champs=decrire_champs(champs), question=question)
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", timeout=300, json={
            "model": MODELE, "prompt": prompt, "stream": False, "format": "json",
            # un plan fait ~30 mots : 200 tokens suffisent largement et empêchent une génération sans fin
            "options": {"temperature": 0, "num_predict": 200}})
        return json.loads(r.json()["response"])
    except (requests.RequestException, ValueError, KeyError):
        return None


def formater(valeur):
    return f"{valeur:.2f}".rstrip("0").rstrip(".")


def repondre_calcul(question, champs):
    """Retourne {reponse, citation, calcul} si la question est un calcul faisable,
    sinon None (=> l'appelant retombe sur repondre_question, le LLM classique)."""
    if not champs or not ressemble_a_un_calcul(question):
        return None
    plan = planifier(question, champs)
    if not plan or plan.get("operation") in (None, "aucune"):
        return None
    res = executer_plan(plan, champs)
    if res is None:
        return None
    valeur, expression = res
    devise = champs.get("devise") or ""
    return {"reponse": f"{formater(valeur)} {devise}".strip(),
            "citation": f"Calcul fait par Python sur les champs extraits : {expression}",
            "calcul": f"{expression} = {formater(valeur)}"}
