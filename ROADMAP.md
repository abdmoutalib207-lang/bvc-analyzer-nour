# Qualité et évolutions de BVC Analyzer Nour

## Implémenté

- Dépôt isolé, 80 titres, historique disponible, graphiques SVG et périodes interactives, recherches et filtres.
- Score unique `nour-quant-v1` sans NLP ; états de qualité, technique, liquidité, fondamentaux documentés, briefing de séance et radar AMMC / presse.
- Import CDG indépendant avec vraie séance, mappage BVC vérifié, OHLC et montant MAD, copie atomique, état de collecte. Workflow autonome sans écriture dans l'ancien dépôt.
- Lot du 04/10 : 63 références annuelles, 68 semestrielles, compteur public des métriques réellement disponibles ; semestre séparé, devise et capital protégés. Statistiques historiques non chevauchantes, sans prédiction ; vue MASI unifiée et rattachement prudent des actualités.
- Complément documentaire direct AMMC : 66 références annuelles après AGMA, Salafin, Eqdom. Pages contrôlées visuellement, hashes conservés, PNB affiché séparément du CA ; pas de dette/EBE industriel pour ces établissements de crédit. Anomalie Eqdom de 0,018 MMAD entre tableaux de fonds propres conservée : pas de P/B ni ROE tant que non rapprochée. AGMA social distinct du semestre consolidé, dénominateur par action encore manquant.

- Complément MGL/MRL/MDP/CASH publié après contrôles : 70 références annuelles, 68 semestrielles. [Pages, unités, dénominateurs et anomalies](docs/batches/2026-10-04-MGL-MRL-MDP-CASH.md). Fonds propres CASH et opérations de capital à rapprocher ; ratios concernés indisponibles.

- Complément CIH/CDM : 72 références annuelles, 69 semestrielles après ajout du S1 2026 CIH. [Preuves et changements de capital](docs/batches/2026-10-04-CIH-CDM.md). Capital juillet 2026 recoupé pour les deux banques ; ajustements comparatifs et moyenne pondérée encore à vérifier, ratios par action bloqués.

## Contrôles d'exploitation à achever sur de nouvelles séances

1. Observer plusieurs exécutions programmées : collecte → commit → Pages → fichier effectivement servi. Comparer les cours de clôture et le nombre de cotations au bulletin primaire.
2. Tester le fournisseur lorsque le flux CDG présente des titres sans OHLC, une suspension ou un changement de structure : journaliser les valeurs exclues sans corrompre la séance publiée.
3. Compléter les 2 historiques manquants sans fabriquer de séances. Achever les 8 références annuelles et 11 semestrielles absentes ; recouper les PDF importés et les nombres d'actions, rapprocher les fonds propres Eqdom et le nombre de titres AGMA. Faire les imports suivants dans Nour uniquement, sans dépendance d'exécution au dépôt principal.
4. Valider la stabilité des statistiques hors échantillon et par régime, avec MASI, coûts, dividendes, liquidité et incertitudes. Construire une base point-in-time avant tout test de facteurs fondamentaux. Le but est l'aide à l'analyse statistique, pas la prédiction du marché.
5. Ajouter éventuellement fixing et carnet seulement après l'obtention de données licites et réellement horodatées ; ne jamais déduire les flux des seules clôtures.
6. Vérifier l'exactitude et les droits de réutilisation des sources de marché et presse, ainsi que l'accessibilité sur téléphone et clavier.

Tant que 1, 3 et 4 restent ouverts, Nour est un terminal analytique consultable et audit-able ; ce n'est ni du temps réel garanti ni une stratégie d'investissement validée.

- Complément disponible terminé : 77/80 annuels et 76/80 semestriels. [Preuves et références restantes](docs/batches/2026-10-04-remaining.md). Annuel manquant : DIS/Diac Salaf, DLM, IBM ; semestre : mêmes titres et CAR à clôture décalée. [Rapprochement principal/Nour](docs/comparisons/2026-10-04-principal.md) : cinq BPA annuels concordent, divergences de période/capital/fonds propres documentées. Ratios sans dénominateur vérifié toujours bloqués.
