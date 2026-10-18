# Historiques et dossiers particuliers — 18 octobre 2026

Le moteur principal a été consulté exclusivement en lecture. Source figée :
`0a0bf7c2039f72e1aca135bce0b87e7ec10a0d49`.
État Nour antérieur : `6e146ed357d4f829c4fd3ebd0fea1489e19d3028`.

## Réconciliation appliquée

Les séries complètes de `pipeline/candles/` ont été rapprochées des manifestes
`datasets/historiques_importes/`. Le fichier agrégé limité aux 250 dernières
séances n'a pas servi de source d'import. Les codes opérateur sont contrôlés
avec `data/source_codes.json`, notamment Sonasid / Stokvis.

46 historiques changent : 14 519 lignes ajoutées, 7 429 observations corrigées,
aucune suppression. L'archive passe de 43 146 à 57 665 observations. IBM : 745,
MDP : 746, SLM : 745, SAF : 703. CMT conserve exactement ses 703 observations
et sa fenêtre post-reprise ; ZLD reste inchangé faute de manifeste opérateur.
Les dates de référence de DAR, NEJ et PPM sont alignées sur leur dernière
observation de la série figée (export ou observation quotidienne), avec l'ancienne date dans l'audit. Ce sont toujours
des références anciennes, sans montant de séance reconstitué.

La série opérateur documentée est prioritaire uniquement dans la période de
son manifeste. L'audit `data/history_reconciliation.json` contient les dates,
champs, nombres, empreintes avant/après, fichiers source et exports reçus.
Les empreintes des exports sont celles consignées par le principal ; cette
opération n'est pas une nouvelle certification indépendante de chaque CSV.

Après la période d'export, les observations Nour déjà présentes ne sont jamais
remplacées automatiquement. Les divergences sont consignées avec les deux
valeurs. Les dix conflits récents de collecte restent visibles. Une nouvelle
ligne récente n'est ajoutée qu'avec quantité positive. Les zéros présents dans
un export sont conservés comme observations sans transaction, sans interpolation.
Dates futures, week-ends, séance annulée du 17/09/2026, doublons et OHLC invalides
ne peuvent pas être importés comme séances valides.

Aucun score, ratio financier ou champ de recommandation du principal n'est
importé. Les indicateurs Nour sont recalculés par ses méthodes existantes sur
les séries réconciliées. Les snapshots de scores déjà archivés ne sont pas réécrits.
Des titres peuvent conserver une limite de liquidité ou de fraîcheur même avec
un historique profond ; aucune clôture récente n'est fabriquée pour les satisfaire.

## Trois situations distinctes

- **DIS** : suspension, absence de transactions dans les exports, retrait
  d'agrément et dossier de liquidation. Dernier dépôt identifié : septembre 2012.
- **DLM** : suspension, absence de transactions dans les exports, demande de
  liquidation annoncée en novembre 2022. Derniers comptes identifiés : 2021.
- **IBM** : cotation encore observée le 16/10/2026, publications financières
  anciennes (2022 et S1 2023). Aucun ratio 2025 ne provient de ces anciens comptes.

Le registre daté `data/issuer_status.json` conserve les références AMMC et Bourse
de Casablanca. Il distingue suspension de cotation et radiation juridique ; la
seconde n'est pas affirmée faute d'acte confirmé. Les anciennes références
26,25 MAD et 40 MAD ne sont plus présentées comme des clôtures récentes datées.
Les liens documentaires d'archives ne certifient pas le contenu intégral des PDF.

L'univers reste de 80 dossiers, dont deux dossiers suspendus conservés. La
couverture courante porte sur 78 dossiers : 77 références annuelles et un
retard de publication expliqué (IBM). Les compteurs bruts d'absence de document
restent disponibles, avec ces catégories pour éviter de confondre archive,
retard connu et dossier oublié.

Fiches, accueil, revue sectorielle, consultation locale et contexte IA partagent
ce statut. Le mode IA n'obtient aucun droit d'écriture supplémentaire.

## Reproduction

Dans un cache en lecture seule du commit principal indiqué, conserver
`pipeline/candles/*.json` et `datasets/historiques_importes/*.json`, puis lancer :

```sh
python tools/reconcile_history.py --source /chemin/cache-principal \
  --source-commit 0a0bf7c2039f72e1aca135bce0b87e7ec10a0d49 \
  --base-commit 6e146ed357d4f829c4fd3ebd0fea1489e19d3028 \
  --asof 2026-10-18
```

Sans `--apply`, cette commande est une simulation. La réapplication sur une
archive déjà réconciliée n'ajoute ni ne remplace d'observations.
