"""Évaluation Q/R détaillée : sépare les causes d'erreur.

Pour chaque type de question, on mesure :
  - Direct   : on donne le BON document au LLM (aucune recherche en jeu)
  - Direct+calcul : idem, mais les calculs passent par calcul.py (Python)
  - RAG (toutes) : recherche dans la collection
  - RAG (identifiantes) : seulement les questions qui désignent un document précis

Une question est "identifiante" si elle contient au moins un mot (hors mots génériques
de facture comme numéro, date, émetteur, total...) qui n'apparaît QUE dans le document visé.
Ex. "Quel est le prix du gâteau d'anniversaire ?" -> identifiante (gâteau n'est que dans f12).
Ex. "Quelle est la date de la facture ?" -> non identifiante : en mode RAG, sur 12 factures,
la question ne dit pas DE QUELLE facture on parle, aucune réponse ne peut être "la bonne".
"""
import os
import time
import argparse
import json
import glob
from collections import Counter

import re
import unicodedata

from answer import indexer_documents, repondre_avec_rag
from answer_single_doc import repondre_question
from text_extract import extraire_texte_pdf
from fields import extraire_champs
from calcul import repondre_calcul

TYPES = ["lookup", "calcul", "sans_reponse"]
PHRASES_REFUS = ["pas presente", "pas present", "not present", "not in this document", "pas mentionne"]
MOTIF_NOMBRE = re.compile(r"\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


def charger_qa_pairs(chemin="qa_pairs.json"):
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


def normaliser_chemin(chemin):
    return chemin.replace("\\", "/")


def normaliser_texte(texte):
    t = unicodedata.normalize("NFD", str(texte).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def vers_float(chaine):
    s = chaine.replace(" ", "").replace("\u00a0", "").replace("\u202f", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if len(s.split(",")[-1]) == 3 else s.replace(",", ".")
    return float(s)


def extraire_nombres(texte):
    return [vers_float(m) for m in MOTIF_NOMBRE.findall(str(texte))]


def est_numerique(valeur):
    return re.fullmatch(r"\s*[\d\s.,]+\s*(MAD|DH|EUR|€|\$)?\s*", str(valeur), flags=re.I) is not None


def comparer_reponse(obtenue, attendue, type_question):
    obtenue = "" if obtenue is None else str(obtenue)
    if type_question == "sans_reponse":
        o = normaliser_texte(obtenue)
        return any(p in o for p in PHRASES_REFUS)
    if attendue is None:
        return False
    if est_numerique(attendue):
        cible = extraire_nombres(attendue)[0]
        return any(abs(n - cible) < 0.01 for n in extraire_nombres(obtenue))
    return normaliser_texte(attendue) in normaliser_texte(obtenue)


def reponse_texte(resultat):
    return str(resultat.get("reponse", "")) if resultat else ""


MOTS_VIDES = set("""quel quelle quels quelles est sont les des une pour par sur dans avec qui que quoi
cette ces son ses leur ete ont the what who is of this that was were are for and with how much would which
numero facture invoice number date emission emis emise emetteur issued fournisseur vendeur reference ref
document montant total prix price unit nom cabinet dossier client mad""".split())


def mots_significatifs(texte):
    """Mots normalisés (sans accents, pluriel simple retiré), hors mots vides et génériques."""
    mots = set()
    for m in normaliser_texte(texte).split():
        if len(m) < 3 or m in MOTS_VIDES:
            continue
        if len(m) > 4 and m.endswith("s"):
            m = m[:-1]
        mots.add(m)
    return mots


def mots_discriminants(question, fichier, mots_par_doc):
    """Mots de la question présents dans le document visé ET dans aucun autre document."""
    return sorted(m for m in mots_significatifs(question)
                  if m in mots_par_doc[fichier]
                  and all(m not in mots for f, mots in mots_par_doc.items() if f != fichier))


def pct(n, t):
    return f"{n}/{t} ({n / t * 100:.0f}%)" if t else "-"


def noms_fichiers(chemin_qa):
    """qa_pairs.json -> eval_qa_progress.json / eval_qa_details.json (noms historiques)
    qa_real.json  -> eval_qa_progress_qa_real.json / eval_qa_details_qa_real.json"""
    nom = os.path.splitext(os.path.basename(chemin_qa))[0]
    suffixe = "" if nom == "qa_pairs" else f"_{nom}"
    return f"eval_qa_progress{suffixe}.json", f"eval_qa_details{suffixe}.json"


def charger_progres(fichier_progres):
    """Questions déjà terminées lors d'une exécution précédente (reprise après arrêt)."""
    try:
        with open(fichier_progres, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def sauver_progres(details, fichier_progres):
    with open(fichier_progres, "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2, ensure_ascii=False)


def etape(nom):
    print(f"   {nom}...", end="", flush=True)


def evaluer(k=5, max_docs=None, chemin_qa="qa_pairs.json", dossier="factures"):
    fichier_progres, fichier_details = noms_fichiers(chemin_qa)
    qa_pairs = charger_qa_pairs(chemin_qa)
    print(f"Questions : {chemin_qa} | Collection RAG : {dossier}/*.pdf")
    if max_docs:
        qa_pairs = qa_pairs[:max_docs]   # mode test rapide
    debut = time.time()

    details = charger_progres(fichier_progres)
    deja_faites = {(d["fichier"], d["question"]) for d in details}
    if details:
        print(f"Reprise : {len(details)} questions déjà faites (dans {fichier_progres}), on les saute.")

    # Vocabulaire de CHAQUE document du jeu de questions (toujours les 12, même en mode rapide)
    mots_par_doc = {e["fichier"]: mots_significatifs(extraire_texte_pdf(e["fichier"]))
                    for e in charger_qa_pairs(chemin_qa)}
    index, chunks = indexer_documents(glob.glob(f"{dossier}/*.pdf"))

    nb_total = sum(len(e["questions"]) for e in qa_pairs)
    fait = 0
    for entree in qa_pairs:
        fichier = normaliser_chemin(entree["fichier"])
        restantes = [q for q in entree["questions"] if (fichier, q["question"]) not in deja_faites]
        fait += len(entree["questions"]) - len(restantes)
        if not restantes:
            continue

        print(f"\n=== {fichier} : extraction des champs... ({(time.time() - debut) / 60:.1f} min)", flush=True)
        texte = extraire_texte_pdf(entree["fichier"])
        champs = extraire_champs(texte) or {}

        for q in restantes:
            fait += 1
            t, attendue = q["type"], q["reponse"]
            print(f"[{fait}/{nb_total}] ({(time.time() - debut) / 60:.1f} min) {t} | {q['question']}", flush=True)
            discriminants = mots_discriminants(q["question"], entree["fichier"], mots_par_doc)

            etape("direct")
            direct = reponse_texte(repondre_question(texte, q["question"]))
            etape("calcul")
            rc = repondre_calcul(q["question"], champs)           # None => pas un calcul
            rep_c = rc["reponse"] if rc else direct
            etape("RAG")
            rep_rag = reponse_texte(repondre_avec_rag(q["question"], index, chunks, k=k))
            print(" ok", flush=True)

            details.append({"fichier": fichier, "type": t, "question": q["question"], "attendue": attendue,
                            "identifiante": len(discriminants) > 0, "mots_discriminants": discriminants,
                            "direct": direct, "direct_calcul": rep_c, "calcul_declenche": rc is not None,
                            "rag": rep_rag,
                            "ok_direct": comparer_reponse(direct, attendue, t),
                            "ok_direct_calcul": comparer_reponse(rep_c, attendue, t),
                            "ok_rag": comparer_reponse(rep_rag, attendue, t)})
            sauver_progres(details, fichier_progres)     # sauvegarde après CHAQUE question

    afficher_resultats(details, qa_pairs, fichier_details, fichier_progres)


def afficher_resultats(details, qa_pairs, fichier_details, fichier_progres):
    # On ne garde que les questions du jeu évalué (utile en mode rapide)
    voulues = {(normaliser_chemin(e["fichier"]), q["question"]) for e in qa_pairs for q in e["questions"]}
    details = [d for d in details if (d["fichier"], d["question"]) in voulues]

    with open(fichier_details, "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2, ensure_ascii=False)

    print(f"\n{'Type':<14}{'Direct':<14}{'Direct+calcul':<16}{'RAG (toutes)':<15}{'RAG (identifiantes)':<20}")
    for t in TYPES:
        d_t = [d for d in details if d["type"] == t]
        ident = [d for d in d_t if d["identifiante"]]
        n_ok = lambda liste, cle: sum(d[cle] for d in liste)
        print(f"{t:<14}{pct(n_ok(d_t, 'ok_direct'), len(d_t)):<14}"
              f"{pct(n_ok(d_t, 'ok_direct_calcul'), len(d_t)):<16}"
              f"{pct(n_ok(d_t, 'ok_rag'), len(d_t)):<15}"
              f"{pct(n_ok(ident, 'ok_rag'), len(ident)):<20}")
    faux = [d for d in details if d["type"] != "calcul" and d["calcul_declenche"]]
    print(f"\nFaux déclenchements du calcul (hors questions calcul) : {len(faux)}")
    for d in faux:
        print("  -", d["question"], "->", d["direct_calcul"])
    print(f"Détail : {fichier_details}")
    print(f"Pour repartir de zéro (nouvelle mesure complète) : supprimer {fichier_progres}")


if __name__ == "__main__":
    # python eval_qa.py                                            -> 60 questions, factures de test
    # python eval_qa.py 2                                          -> test rapide (2 premiers documents)
    # python eval_qa.py --qa qa_real.json --dossier factures_reelles  -> 24 questions, factures réelles
    parser = argparse.ArgumentParser(description="Évaluation question/réponse : direct, direct+calcul, RAG")
    parser.add_argument("max_docs", nargs="?", type=int, default=None, help="nombre de documents (test rapide)")
    parser.add_argument("--qa", default="qa_pairs.json", help="fichier de questions")
    parser.add_argument("--dossier", default="factures", help="dossier des PDF indexés pour le RAG")
    args = parser.parse_args()
    evaluer(max_docs=args.max_docs, chemin_qa=args.qa, dossier=args.dossier)
