# BVC Analyzer Nour

**Prototype indépendant** alimenté par une copie en lecture seule des données du moteur BVC Analyzer au 25/09/2026. Nour inclut l'univers des **80 titres** : 78 historiques disponibles dans cette archive, deux absents (DIS et DLM). Il ne modifie ni les sources du projet principal ni son déploiement.

## Voir immédiatement le résultat

Ouvrir [l'interface pré-générée](web/index.html) dans un navigateur : **aucun serveur, paquet ou JavaScript n'est nécessaire pour voir les cours, le graphique par défaut et les dernières séances**. Sélectionner un ticker dans le tableau pour ouvrir sa fiche, puis télécharger son historique complet en CSV. JavaScript ajoute simplement le filtre des titres et les périodes **1M / 3M / 1A / Tout** des graphiques.

Pour régénérer le rapport et consulter le site par HTTP :

```bash
python run.py --asof 2026-09-26
python run.py --asof 2026-09-26 --serve
# puis http://127.0.0.1:8765/
```

Le serveur écoute sur `127.0.0.1` seulement. `web/index.html` et 80 pages `web/titres/TICKER.html` sont des fichiers HTML autonomes avec graphique SVG déjà dessiné ; `web/historique/TICKER.csv` contient toutes les séances présentes dans l'archive de ce titre. `web/report.json` expose les mêmes contrôles de qualité pour un usage programmatique.

Pour exporter une courbe en image partageable, `python tools/export_chart.py ADI` crée `web/ADI_historique.png` à partir des cours et volumes archivés. Cette commande facultative demande Matplotlib ; les pages HTML et les graphiques SVG intégrés n'en ont pas besoin.

## Provenance

- Source figée : archive du projet principal, commit `dd8e89f29f6e6777f783db634a12fcccb3d5088a`. Les cours viennent de `data.json`, les séries complètes de `pipeline/candles/*.json`. Des empreintes SHA-256 par fichier sont conservées dans `data/market_snapshot.json`.
- Pour reconstruire la copie à partir d'une autre archive **contrôlée** : `python tools/import_market.py --source /chemin/vers/archive`, puis `python run.py --asof AAAA-MM-JJ`. Ce script n'écrit jamais dans l'archive source.
- Les longueurs d'historique varient : ADI 811 séances, CMT 688, SMI 577, T2S 38. Le chiffre affiché est le nombre réellement présent, pas une promesse de trois années pour tous les titres.
- Les anciens champs `sig` et `sigBvc` sont conservés uniquement pour comparaison. La seule décision émise par Nour porte sur **l'état des données** : `OBSERVABLE`, `LIMITÉ`, `INDISPONIBLE`, `SUSPENDU`.

## Contrôles et limites

- Le moteur confronte dernier cours et dernière bougie, âge du prix, suspensions/reprises, OHLC et profondeur de série. Les ouvertures hors des extrêmes sont signalées ; les clôtures hors fourchette sont rejetées. CMT : sept séances depuis la reprise, aucune estimation de sortie chiffrée avant dix séances comparables.
- Valeur échangée de la dernière séance : montant du snapshot. Valeur historique : **estimation** clôture × titres, jamais un montant de transaction exact. Aucun spread, carnet ni « Smart Money » n'est déduit de la seule courbe.
- Le site est **figé**. Pour une séance ultérieure, les données doivent être importées et revérifiées ; Nour ne prétend pas être un flux en direct. La qualité et la direction boursière sont deux notions distinctes.

Tests : `python -m unittest discover -s tests -v`. La [feuille de route](ROADMAP.md) décrit la connexion aux nouvelles séances et la validation à réaliser avant toute utilisation décisionnelle.
