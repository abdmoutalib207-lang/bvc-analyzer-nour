# BVC Analyzer Nour · avancement et prochaines étapes

## Livré dans le dépôt isolé

- 80 fiches issues du snapshot du 25 septembre ; 78 séries historiques, DIS et DLM marqués absents.
- Courbes de clôture et histogrammes de volumes SVG visibles sans JavaScript, navigation ticker par ticker, choix de période avec JavaScript, 40 dernières séances par fiche, CSV complet pour chaque série.
- Une décision canonique de qualité des données, vérification OHLC/fraîcheur/reprise, métriques descriptives et estimation de liquidité signalée comme telle.
- Tests du moteur et de visibilité de l'interface ; dépôt Git local sans liaison à la production.

## Lot 1 — Dépôt distant et publication de test

Créer **un nouveau dépôt GitHub distinct** `bvc-analyzer-nour`, de préférence privé. Y pousser exclusivement ce dossier, sans secrets ni workflows qui écrivent dans `-bvc-analyzer`. Prévoir une URL de prévisualisation différente de celle du projet principal si la publication est voulue. Vérifier sur téléphone que le tableau de 80 titres, ADI et le CSV s'ouvrent effectivement depuis cette URL.

## Lot 2 — nouvelles séances et qualité (3 à 5 jours sous réserve des droits d'accès)

Ajouter un import manuel puis automatisé en lecture seule : séance effective BVC, arrêt/reprise, symbole officiel et opération sur capital. Contrôler les extrêmes vrais, la valeur échangée réelle et la date avant publication. **Critère :** CMT ne mélange jamais l'avant/après suspension ; aucune série DIS/DLM n'est inventée ; tous les échecs ont un motif visible.

## Lot 3 — liquidité, risque et validation (1 à 3 semaines)

Remplacer les MAD historiques approximés par les valeurs réelles lorsque disponibles. Ajouter concentration des volumes, flottant documenté, scénarios de sortie et indicateurs de risque dont les entrées sont vérifiées. Tester les cas ADI, RDS, TGCC, SGTM, T2S, SMI et CMT sur plusieurs séances et régimes. Un flux ou une « absorption » exige des données de carnet/fixing horodatées ; le volume seul ne suffit pas.

## Lot 4 — comparaison prospective

Faire tourner Nour et le moteur public aux mêmes dates sans transfert de signal. Mesurer la couverture, l'âge des données, les divergences et les erreurs de détection. Toute nouvelle décision directionnelle devra être validée hors échantillon avec coûts et liquidité ; le retrait du NLP du score reste maintenu durant la recherche.
