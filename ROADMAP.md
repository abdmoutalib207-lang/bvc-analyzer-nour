# Qualité et évolutions de BVC Analyzer Nour

## Implémenté

- Dépôt isolé, 80 titres, historique disponible, graphiques SVG et périodes interactives, recherches et filtres.
- Score unique `nour-quant-v1` sans NLP ; états de qualité, technique, liquidité, fondamentaux documentés, briefing de séance et radar AMMC / presse.
- Import CDG indépendant avec vraie séance, mappage BVC vérifié, OHLC et montant MAD, copie atomique, état de collecte. Workflow autonome sans écriture dans l'ancien dépôt.

## Contrôles d'exploitation à achever sur de nouvelles séances

1. Observer plusieurs exécutions programmées : collecte → commit → Pages → fichier effectivement servi. Comparer les cours de clôture et le nombre de cotations au bulletin primaire.
2. Tester le fournisseur lorsque le flux CDG présente des titres sans OHLC, une suspension ou un changement de structure : journaliser les valeurs exclues sans corrompre la séance publiée.
3. Compléter les 2 historiques manquants et rattacher les rapports 2026 à l'ensemble des 80 émetteurs. Recouper les 31 rapports déjà référencés, vérifier la nature de chaque résultat et de chaque nombre d'actions.
4. Construire un backtest hors échantillon avec MASI, coûts, liquidité, glissement, turnover, drawdown et incertitudes avant toute interprétation prédictive du score.
5. Ajouter éventuellement fixing et carnet seulement après l'obtention de données licites et réellement horodatées ; ne jamais déduire les flux des seules clôtures.
6. Vérifier l'exactitude et les droits de réutilisation des sources de marché et presse, ainsi que l'accessibilité sur téléphone et clavier.

Tant que 1, 3 et 4 restent ouverts, Nour est un terminal analytique consultable et audit-able ; ce n'est ni du temps réel garanti ni une stratégie d'investissement validée.
