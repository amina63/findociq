# FinDocIQ

Système d'extraction et de question-réponse sur documents financiers (factures, relevés, rapports), avec support des PDF numériques et scannés (OCR), le tout auto-hébergé localement via Ollama — aucune donnée envoyée à un service tiers.

## Fonctionnalités

- **Extraction structurée** : numéro, date, émetteur, client, total, lignes de détail (JSON schema + LLM)
- **Question/réponse ancrée** : réponses avec citation exacte du passage source, garde-fou anti-hallucination
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
python eval_extraction.py   # précision/recall/F1 extraction de champs
python eval_rag.py          # retrieval + précision des réponses
python eval_ocr.py          # précision OCR (nécessite le dossier sroie/, voir ci-dessous)
python test_guardrail.py    # taux de refus sur questions sans réponse
```

## Données de test

- `factures/` : 12 factures générées (templates variés, cas limites volontaires — champs manquants, formats différents)
- `sroie/` : échantillon de 5 reçus scannés réels du dataset public [SROIE](https://github.com/zzzDavid/ICDAR-2019-SROIE) (images `.jpg` non versionnées, à retélécharger si besoin — labels `.json` inclus)

## Résultats mesurés

**Extraction de champs** (12 documents, `eval_extraction.py`) :

| Champ | Precision | Recall | F1 |
|---|---|---|---|
| numero_facture | 0.92 | 1.00 | 0.96 |
| date | 1.00 | 1.00 | 1.00 |
| emetteur | 1.00 | 0.82 | 0.90 |
| client | 1.00 | 1.00 | 1.00 |
| total | 1.00 | 1.00 | 1.00 |

**RAG — 60 questions** (`eval_rag.py`, k=5) :

| Type | Retrieval hit-rate | Answer accuracy |
|---|---|---|
| lookup | 72% | 42% |
| calcul | 92% | 25% |
| sans_réponse (garde-fou) | 67% | 67% |

**OCR** (5 reçus SROIE, `eval_ocr.py`) : total 100% (exact), date 60%, company 0% exact / 74% similarité textuelle.

## Limites connues

- **Calculs multi-étapes** : le LLM local (llama3.2:3B) répond correctement à seulement ~25% des questions nécessitant un calcul, même quand le bon document est retrouvé (92%) — limite de raisonnement du modèle, pas du retrieval.
- **DeepSeek-OCR** (scans difficiles) : non testé, nécessite un GPU dédié (16Go+ VRAM) non disponible en local ; en attente d'accès au serveur de l'équipe.
- **Extraction de noms de commerce sur reçus scannés** : sensible aux erreurs OCR (espaces/caractères mal lus).
- **Non-déterminisme** : les résultats du LLM peuvent varier légèrement d'une exécution à l'autre (temperature=0 utilisé pour limiter cet effet).

## Architecture

```
PDF/image → router.py (numérique vs scanné)
    ├─ numérique → text_extract.py (pdfplumber)
    └─ scanné    → ocr.py (RapidOCR)
         ↓
    fields.py (extraction structurée, LLM + schéma JSON)
         ↓
    Mode direct : answer_single_doc.py (1 document, tout le texte)
    Mode RAG    : chunk.py → embed.py → store.py (FAISS) → answer.py
         ↓
    app.py (interface Streamlit)
```
