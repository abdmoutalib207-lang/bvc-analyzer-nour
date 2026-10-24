# Collecte métier automatisée — lot TGCC, Marsa Maroc, SMI

Premier lot de nouvelles données primaires : 18 observations, distinctes des relevés comptables déjà présents.

- TGCC : carnet S1 2026 de 28 360 MDH, comparatif S1 2025 de 19 100 MDH ; tableau page PDF 2. Le texte arrondi à 28,4 milliards n'écrase pas le tableau.
- Marsa Maroc : trafic S1 2026 de 34,5 millions de tonnes ; conteneurs 1 520 260 EVP, dont 822 666 transbordement et 697 594 import-export ; vracs liquides 5,9 et solides/divers 11,7 millions de tonnes. Page PDF 2. Tonnes et EVP ne sont pas additionnés. Les unités véhicules/TIR ambiguës restent hors extraction.
- SMI : production d'argent 126 544 kg en 2025 et 127 675 kg en 2024 ; minerai traité, teneur et rendement métal avec comparatifs (page PDF 40, imprimée 79). AISC **approximatif** ~22 USD/oz et CAPEX des chiffres clés 214 MDH (page PDF 6, imprimée 10), distinct d'un décaissement TFT. Aucun coût groupe Managem n'en est déduit.

Les trois PDF ont été téléchargés, hachés, les pages retenues rendues et lues visuellement. Les empreintes approuvées sont figées dans les profils ; une nouvelle version ne bénéficie pas de cette revue par simple héritage. `data/sector_disclosures.json` conserve valeurs, source, page, extrait probant, unité, période, approximation et première disponibilité.

## Automatisation active dans le workflow

La collecte s'exécute à l'édition de clôture, sur publication de code et sur lancement manuel complet. Elle examine les pages officielles propres aux trois sociétés, plus les documents déjà repérés par la veille. Le téléchargement natif TGCC `jet_download` est reconnu. Chaque profil décrit une identité, des hôtes autorisés, un type de période et des tableaux/unité/colonnes précis. Au maximum deux PDF par société et trois sociétés en parallèle ; HTTPS, taille, temps et extraction sont bornés. Cache PDF avec ETag restauré entre runs.

Une table reconnue dans une nouvelle version produit une **lecture automatique identifiée**, jamais un statut de revue visuelle. Les schémas non reconnus et valeurs contradictoires restent des candidats à vérifier dans l'état de collecte. Les champs compatibles s'intègrent dans les tableaux métier ; aucun nouveau chiffre de ce flux ne modifie un score ni n'alimente un ratio financier par défaut.

Une panne locale conserve les valeurs précédentes, leurs dates et leurs preuves ; elle est signalée sans empêcher les autres sociétés. Les incidents de collecte sont conservés dans un journal cumulatif, sans résolution inventée. Une modification de valeur pour la même période devient une divergence avec ancienne et nouvelle valeur. Les premières disponibilités ne sont pas réécrites lors d'une nouvelle lecture identique. Une date future est refusée.

`web/collecte-metiers.json` expose le résultat de collecte. La vue locale de l'assistant couvre carnet TGCC, trafic Marsa Maroc et AISC SMI. Le backend IA privé n'est pas modifié. Les contrôles navigateur ajoutent ces trois fiches aux trois largeurs.

## Limites

L'automatisation numérique porte sur **ces trois profils**, pas encore les 80 sociétés. Les profils semestriels reconnaissent S1 ; S2, trimestres, nouvelles unités ou nouvelles mises en page demandent une extension explicite. Un PDF image exigeant OCR reste à vérifier. Les colonnes, dates, unités ou périmètres ambigus ne sont pas devinés. Le moteur principal reste strictement en lecture seule.
