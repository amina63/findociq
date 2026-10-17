# Factures réelles utilisées pour l'évaluation (gold_real.json)

8 factures **réelles** émises par de vraies entreprises, au format PDF numérique (texte extractible),
publiées dans deux dépôts open source qui les utilisent eux-mêmes comme données de test.
Elles complètent les 12 factures synthétiques de `factures/` : mises en page imprévues, 4 langues,
1 à 2 pages, pièges réels.

| Fichier | Émetteur | Langue | Pages | Source | Licence |
|---|---|---|---|---|---|
| free_fiber.pdf | Free SAS (FAI, France) | FR | 2 | invoice2data | MIT |
| NetpresseInvoice.pdf | NETPRESSE (annonces légales, France) | FR | 1 | invoice2data | MIT |
| AmazonWebServices.pdf | Amazon Web Services, Inc. | EN | 1 | invoice2data | MIT |
| FlipkartInvoice.pdf | WS Retail Services (Flipkart, Inde) | EN | 1 | invoice2data | MIT |
| QualityHosting.pdf | QualityHosting AG (Allemagne) | DE | 2 | invoice2data | MIT |
| hetzner.pdf | Hetzner Online GmbH (Allemagne) | DE | 1 | ZUGFeRD corpus | Apache 2.0 |
| coolblue1.pdf | Coolblue B.V. (Pays-Bas) | NL | 1 | invoice2data | MIT |
| saeco.pdf | e-Luscious Nederland B.V. (Saeco) | NL | 1 | invoice2data | MIT |

Sources :
- invoice2data, dossier `tests/compare` : https://github.com/invoice-x/invoice2data
  (licence MIT, Copyright (c) 2015 Manuel Riel ; version consultée : commit 4feaeee, octobre 2026)
- ZUGFeRD corpus, dossier `unstructured` : https://github.com/ZUGFeRD/corpus
  (licence Apache 2.0 ; fichier d'origine RE-E-974-Hetzner_2016-01-19_R0005532486.pdf ; commit 82e886f)

## Comment la vérité terrain a été construite
- Valeurs relevées dans le texte de chaque PDF, et recoupées avec les annotations JSON
  fournies par invoice2data (numéro, date, montant) quand elles existent.
- Chaque valeur a été vérifiée automatiquement (elle apparaît bien dans le texte extrait du PDF)
  puis visuellement, page par page, sur le rendu image des 8 PDF.
- Les noms visibles seulement dans un logo sont acceptés comme variantes
  (ex. « Publication Annonce Légale » pour NETPRESSE, « Hetzner Online »).
- Quand une facture admet plusieurs réponses légitimes, le gold les liste toutes
  (ex. émetteur `["Free SAS", "Free"]`, client `["ALEXINUX", "de Lattre Alexis"]`).
- Les dates sont notées telles qu'écrites sur la facture ; l'évaluation compare les dates
  normalisées (jour, mois, année), quel que soit le format (« 02 Juillet 2015 » = « 02/07/2015 »).

## Pièges réels contenus dans ce jeu
- **saeco.pdf** : l'émetteur (e-Luscious Nederland B.V., pour Saeco) n'apparaît que dans une image, pas dans le texte → pour un système qui lit le texte, la bonne réponse est `null`. Facture réelle à laquelle les mainteneurs d'invoice2data ont ajouté un avertissement (texte rouge) pour en faire un cas de test. Teste le garde-fou : le modèle ne doit pas inventer.
- **FlipkartInvoice.pdf** : deux dates (commande 15-10-2015, facture 20-10-2015) ; vendeur légal (WS Retail) différent de la plateforme (Flipkart).
- **free_fiber.pdf** : date de facture et date limite de paiement proches ; montants HT et TTC.
- **hetzner.pdf** : Netto 87,39 € / Brutto 104,00 € → le total attendu est le TTC (Brutto).
- **QualityHosting.pdf** : le total n'apparaît qu'en page 2.
- **coolblue1.pdf** : texte mal extrait (« F actuurnummer », « K lantnummer ») comme souvent dans la réalité.

## Limites à mentionner dans le rapport
- 8 documents seulement : un F1 par champ calculé sur 8 valeurs varie de 0,125 par erreur → ordre de grandeur, pas mesure précise.
- Aucune facture marocaine (MAD) : aucune source publique trouvée ; les factures réelles contiennent des données personnelles et circulent rarement en ligne.
- Certaines factures ont été anonymisées par leurs contributeurs (ex. « Pino Bluebird », « Fakestreet »).
- Données personnelles : ces documents sont déjà publics, mais par prudence on ne les recopie pas
  dans le dépôt du projet (`factures_reelles/` dans .gitignore) ; ce fichier indique où les retrouver.
