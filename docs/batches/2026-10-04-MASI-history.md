# Restauration de la profondeur MASI dans Nour

Le graphique Nour utilisait une copie de l'historique datant d'avant l'import des exports MASI 2023–2025 dans le moteur principal. L'historique complet existe bien ; il n'avait pas encore été transféré dans Nour.

## Source et recoupements

Source consultée en lecture seule : `abdmoutalib207-lang/-bvc-analyzer`, commit `eed7e2d9ce475de459cae29d08008f46926fc043`, fichier `pipeline/masi_history.json`, blob `eeece0b3ebf646b6c8d43d9ec5e752b143a86a43`.

- Avant : 197 clôtures, du 01/12/2025 au 02/10/2026.
- Ajout : 719 clôtures, du 02/01/2023 au 28/11/2025.
- Après : 916 clôtures, du 02/01/2023 au 02/10/2026.
- Les 197 séances communes correspondent exactement, sans écart de valeur. Toutes les clôtures préexistantes de Nour sont conservées.
- Les 742 lignes du fichier source `datasets/masi_investing_ohlc.json` respectent leurs bornes OHLC et leurs clôtures concordent avec la série importée. Ce fichier ne fournit pas de volumes. Nour affiche toujours les clôtures MASI, sans fabriquer de volumes ni de bougies récentes.
- La séance annulée du 17/09/2026 reste absente. Les trous historiques restent absents.

Les observations anciennes viennent des exports Investing.com fournis le 03/10/2026 et intégrés au moteur principal. La provenance initiale de Nour est conservée ; un journal complémentaire identifie ce transfert, le commit et le blob sources, la copie utilisée et les contrôles de recouvrement. Il s'agit d'un transfert daté, sans dépendance d'exécution envers le moteur principal.

## Affichage

Le MASI affiche désormais tout l'historique par défaut, aussi sans JavaScript. La couverture complète reste visible près du graphique. Le bouton « Tout » et la réinitialisation reviennent à cette profondeur. Un raccourci « 3A » sélectionne 756 séances disponibles selon la convention des autres raccourcis (21 / 63 / 252). Les dates réelles et le nombre de séances affichées restent explicites.

## Validation

67 tests Python réussis, dont extension rejouable, refus atomique des divergences, rejet des valeurs invalides et séances futures, de week-end ou annulées, conservation des clôtures existantes et affichage statique intégral du MASI. Test Node de navigation conservé.

Contrôle navigateur Chrome 145 : 916 clôtures présentes, profondeur initiale intégrale, raccourci 3A, retour à Tout et lecture des première/dernière dates. Zoom, déplacement, vue d'ensemble, comparaison exacte des clôtures, clavier et plein écran vérifiés sur ordinateur ; pincement et défilement vérifiés en simulation mobile. Le moteur principal n'a pas été modifié.
