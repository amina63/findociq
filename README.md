# FinDocIQ

Système d'extraction et de question-réponse sur documents financiers (factures, relevés, rapports), avec support des PDF numériques et scannés (OCR), le tout auto-hébergé localement via Ollama — aucune donnée envoyée à un service tiers.

## Fonctionnalités

- **Extraction structurée** : numéro, date, émetteur, client, total, devise, lignes de détail (JSON schema + LLM)
- **Question/réponse ancrée** : réponses avec citation exacte du passage source, garde-fou anti-hallucination
- **Calculs fiables** (`calcul.py`) : le LLM choisit l'opération et les valeurs, **Python fait le calcul**
- **RAG multi-documents** : recherche automatique dans une collection de documents (FAISS + embeddings multilingues)
- **OCR** : détection automatique document numérique/scanné, extraction via RapidOCR
- **Vérifications comptables** : cohérence total = somme des lignes, ratios
- **Interface Streamlit** : upload, tableau de champs extraits, chat Q&A, dashboard de métriques

## Installation

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Créer un fichier `.env` à la racine :
```
OLLAMA_URL=http://localhost:11434
```

Installer [Ollama](https://ollama.com) puis télécharger les modèles nécessaires :
```bash
ollama pull llama3.2
ollama pull bge-m3
```

## Utilisation

Lancer l'application :
```bash
streamlit run app.py
```

Lancer les évaluations :
```bash
python eval_extraction.py                  # F1 extraction, 12 factures de test
python eval_extraction.py gold_real.json   # F1 extraction, 8 factures réelles (voir ci-dessous)
python eval_qa.py                          # 60 questions : direct / direct+calcul / RAG (~1h30 sur CPU)
python eval_qa.py 2                        # test rapide sur 2 documents
python eval_rag.py                         # taux de retrieval (bon document retrouvé)
python eval_ocr.py                         # précision OCR (nécessite le dossier sroie/)
python test_calcul.py                      # tests du moteur de calcul (sans Ollama)
```

`eval_qa.py` sauvegarde chaque question dans `eval_qa_progress.json` et reprend là où il s'est arrêté ;
supprimer ce fichier pour une nouvelle mesure complète.

## Données de test

- `factures/` : 12 factures générées (templates variés, cas limites volontaires — champs manquants, formats différents), questions dans `qa_pairs.json`, vérité terrain dans `gold_set.json`
- `factures_reelles/` : 8 factures **réelles** (Free, Netpresse, AWS, Flipkart, QualityHosting, Hetzner, Coolblue, Saeco ; FR/EN/DE/NL) issues des dépôts open source invoice2data (MIT) et ZUGFeRD corpus (Apache 2.0). Non versionnées : voir `SOURCES_factures_reelles.md` pour les récupérer. Vérité terrain : `gold_real.json`
- `sroie/` : échantillon de 5 reçus scannés réels du dataset public [SROIE](https://github.com/zzzDavid/ICDAR-2019-SROIE) (images `.jpg` non versionnées, labels `.json` inclus)

## Résultats mesurés

Une exécution, llama3.2 3B local, temperature 0. Petits échantillons : ordres de grandeur.

**Extraction de champs — F1** (`eval_extraction.py`, comparaison normalisée : casse, accents, ponctuation et format de date ignorés)

| Champ | 12 factures de test | 8 factures réelles |
|---|---|---|
| numero_facture | 1.00 | 0.86 |
| date | 1.00 | 1.00 |
| emetteur | 0.91 | 0.86 |
| client | 1.00 | 0.86 |
| total | 1.00 | 1.00 |

**Question/réponse — 60 questions** (`eval_qa.py`, k=5)

| Type | Direct (bon document) | Direct + calcul Python | RAG (toutes) | RAG (questions identifiantes) |
|---|---|---|---|---|
| lookup (36) | 97% | 97% | 42% | 67% (8/12) |
| calcul (12) | 33% | **83%** | 17% | 22% (2/9) |
| sans_réponse (12) | 83% | 83% | 75% | 1/2 |

- Calcul Python : 0 faux déclenchement sur les 48 questions qui ne sont pas des calculs.
- Question **identifiante** : contient un mot qui n'apparaît que dans le document visé (ex. « gâteau d'anniversaire »). Les 24 autres questions lookup (« Quel est le fournisseur ? ») ne précisent pas de quelle facture il s'agit et n'ont pas de bonne réponse unique en mode RAG.
- Retrieval (`eval_rag.py`, bon document dans le top-5) : lookup 72%, calcul 92%, sans_réponse 67%.

**OCR** (5 reçus SROIE, `eval_ocr.py`) : total 100% (exact), date 60%, company 0% exact / 74% similarité textuelle.

## Limites connues

- **Factures réelles** : les erreurs viennent surtout des mises en page complexes (intitulés et valeurs sur des lignes séparées, émetteur seulement en pied de page ou dans un logo) dont la structure est perdue à l'extraction du texte. Le modèle ne laisse jamais un champ vide (rappel 1.00) : quand il se trompe, il remplit avec une mauvaise valeur.
- **Calculs** : le calcul Python n'est branché qu'en mode direct ; les erreurs restantes (2/12) sont des erreurs de planification du LLM (mauvaise opération choisie), jamais d'arithmétique. Le filtre de détection a été ajusté sur ces mêmes questions.
- **Garde-fou** : 83% en direct ; hallucinations observées (émetteur inventé, dont une copie d'un exemple du prompt : « SDN BHD »).
- **DeepSeek-OCR** (scans difficiles) : non testé, nécessite un GPU dédié non disponible en local.
- **Non-déterminisme** : les résultats du LLM peuvent varier légèrement d'une exécution à l'autre (temperature=0 limite cet effet). Les appels au modèle sont bornés en longueur (`num_predict`) et en temps (5 min) pour éviter les générations sans fin.
- Aucune facture marocaine réelle publique n'a pu être trouvée pour l'évaluation.

## Architecture

```
PDF/image → router.py (numérique vs scanné)
    ├─ numérique → text_extract.py (pdfplumber)
    └─ scanné    → ocr.py (RapidOCR)
         ↓
    fields.py (extraction structurée, LLM + schéma JSON)
         ↓
    Mode direct : calcul.py (si calcul : LLM planifie, Python calcule)
                  sinon answer_single_doc.py (1 document, tout le texte)
    Mode RAG    : chunk.py → embed.py → store.py (FAISS) → answer.py
         ↓
    app.py (interface Streamlit)
```
