"""Tests de calcul.py SANS Ollama : on vérifie la partie Python (exécution des plans).
Lancer : python test_calcul.py"""
from calcul import executer_plan, ressemble_a_un_calcul, formater, decrire_champs


def L(desc, qte, pu, montant):
    return {"description": desc, "quantite": qte, "prix_unitaire": pu, "montant": montant}


# Champs tels qu'ils sont écrits dans les 12 factures (valeurs relevées dans les PDF)
CAS = [
    # (champs, plan qu'un bon planificateur doit produire, réponse attendue dans qa_pairs.json)
    ({"total": 1900, "lignes": [L("Table en chene", 1, 1200, 1200), L("Chaises (lot de 4)", 2, 350, 700)]},
     {"operation": "division", "operandes": [350, 4]}, 87.5),
    ({"total": 1230, "lignes": [L("Ramettes papier A4", 10, 45, 450), L("Cartouches encre", 3, 180, 540),
                                L("Classeurs", 20, 12, 240)]},
     {"operation": "somme", "operandes": ["lignes[1]", "lignes[2]"]}, 780),
    ({"total": 3300, "lignes": [L("Tenue de comptabilite", None, None, 2500), L("Declaration fiscale", None, None, 800)]},
     {"operation": "difference", "operandes": ["lignes[0]", "lignes[1]"]}, 1700),
    ({"total": 415, "lignes": [L("Cable HDMI 2m", 5, 35, 175), L("Souris sans fil", 2, 120, 240)]},
     {"operation": "difference", "operandes": ["lignes[1]", "lignes[0]"]}, 65),
    ({"total": 175, "lignes": [L("Medicament A", 1, 85, 85), L("Medicament B", 2, 45, 90)]},
     {"operation": "difference", "operandes": ["lignes[0]", "lignes[1]"]}, 5),   # ordre inversé -> toujours 5
    ({"total": 450, "lignes": [L("Livre - Analyse Mathematique", 3, 150, 450)]},
     {"operation": "multiplication", "operandes": ["lignes[0].prix_unitaire", 5]}, 750),
    ({"total": 3090, "lignes": [L("Bureau bois massif", 1, 2200, 2200), L("Chaise ergonomique", 1, 890, 890)]},
     {"operation": "difference", "operandes": ["lignes[0]", "lignes[1]"]}, 1310),
    ({"total": 620, "lignes": [L("Laptop stand", 1, 320, 320), L("USB-C hub", 2, 150, 300)]},
     {"operation": "multiplication", "operandes": ["lignes[1].prix_unitaire", 3]}, 450),
    ({"total": 980, "lignes": []},
     {"operation": "pourcentage_de", "operandes": ["total", 10]}, 98),
    ({"total": 3700, "lignes": [L("Consultation juridique", None, None, "1500,00"), L("Redaction contrat", None, None, "2200,00")]},
     {"operation": "difference", "operandes": ["lignes[1]", "lignes[0]"]}, 700),  # montants en texte avec virgule
    ({"total": 600, "lignes": [L("Service de maintenance", 1, 600, 600)]},
     {"operation": "ajout_pourcentage", "operandes": ["total", 20]}, 720),
    ({"total": 530, "lignes": [L("Gateau anniversaire", 1, 350, 350), L("Viennoiseries (lot)", 3, 60, 180)]},
     {"operation": "difference", "operandes": ["lignes[0]", "lignes[1]"]}, 170),
]

for i, (champs, plan, attendu) in enumerate(CAS, start=1):
    valeur, expression = executer_plan(plan, champs)
    assert abs(valeur - attendu) < 0.01, (i, valeur, attendu)
    print(f"Calcul {i:>2} : {expression} = {formater(valeur)}  (attendu {attendu})  OK")

# Cas qui doivent échouer proprement (None) au lieu de planter
ch = CAS[0][0]
assert executer_plan({"operation": "division", "operandes": ["total", 0]}, ch) is None      # division par 0
assert executer_plan({"operation": "somme", "operandes": ["lignes[9]"]}, ch) is None        # ligne inexistante
assert executer_plan({"operation": "somme", "operandes": ["lignes[0].quantite", "x"]}, ch) is None  # opérande illisible
assert executer_plan({"operation": "difference", "operandes": ["lignes[0]"]}, ch) is None   # 1 seul opérande
assert executer_plan({"operation": "inconnue", "operandes": [1, 2]}, ch) is None
assert executer_plan("pas un dict", ch) is None
assert executer_plan({"operation": "somme", "operandes": "total"}, ch) is None              # mauvais format
assert executer_plan({"operation": "somme_lignes"}, CAS[8][0]) is None                      # aucune ligne

# Formatage et filtre
assert formater(87.5) == "87.5" and formater(780.0) == "780" and formater(7.142857) == "7.14"
assert ressemble_a_un_calcul("Quelle est la différence entre A et B ?")
assert not ressemble_a_un_calcul("Combien de livres ont été achetés ?")   # lecture, pas calcul
assert not ressemble_a_un_calcul("Quelle est la date de la facture ?")
assert "lignes[1] = Chaises (lot de 4)" in decrire_champs(CAS[0][0])

print("\ncalcul.py : tous les tests OK")
