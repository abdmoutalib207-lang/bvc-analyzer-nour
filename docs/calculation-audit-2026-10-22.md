# Stabilisation des calculs — contrôle des 80 titres, 22 octobre 2026

Base auditée : `e859287736dff6803568467ab0e8d172f7de2f05`.
Le moteur principal a uniquement été consulté. Aucun cours, compte publié,
pondération ou seuil de score n'a été remplacé pour améliorer un résultat.

## Défaut démontré et correction

Les anciennes fréquences historiques utilisaient les clôtures de toutes les
lignes, y compris celles sans échange, et comptaient les horizons sur les
lignes disponibles du titre. Un trou de calendrier pouvait ainsi être comprimé
en une seule observation. Les ruptures de capital déjà exclues des mesures de
risque n'étaient pas exclues de ces fréquences.

`non_overlapping_returns_v2` fixe les fenêtres sur le calendrier MASI disponible :

- toute fenêtre contenant une séance absente, sans échange, avec clôture
  invalide ou date dupliquée est exclue ; aucun remplissage ni interpolation ;
- la frontière documentée de capital/reprise exclut l'intervalle qui la traverse ;
- les dates futures sont retirées avant la sélection de l'historique de reprise ;
- sans calendrier, les horizons sont explicitement des observations disponibles ;
- les comptes de fenêtres candidates, exclues et retenues restent visibles ;
- le minimum de 30 observations et les réserves de Wilson sont conservés.

Les nombres d'observations changent sur **77 fiches sur 80**. Ce chiffre inclut
l'alignement sur les dates MASI, pas seulement l'exclusion des volumes nuls.
Le snapshot contient 60 titres avec au moins une ligne historique de volume nul.

| Titre | Avant : observations 1 / 5 / 20 | Après : observations 1 / 5 / 20 |
| --- | --- | --- |
| ADI | 829 / 165 / 41 | 822 / 164 / 41 |
| RDS | 749 / 149 / 37 | 742 / 148 / 37 |
| Maghrebail | 753 / 150 / 37 | 198 / 13 / 0 |
| Maroc Leasing | 746 / 149 / 37 | 134 / 5 / 0 |
| Managem | 829 / 165 / 41 | 806 / 155 / 34 |
| Sothema | 749 / 149 / 37 | 625 / 93 / 13 |

Pour Maghrebail et Maroc Leasing, plusieurs horizons n'atteignent plus le minimum
requis : leur fréquence reste désormais indisponible au lieu de paraître précise.
Les 80 lignes avant/après et les empreintes des entrées sont conservées dans
[`calculation-audit-2026-10-22.json`](calculation-audit-2026-10-22.json).

## Recalcul indépendant avant publication

`nour/calculation_audit.py` ne rappelle pas les calculateurs contrôlés. Un second
calcul en `Decimal` (précision 40) vérifie les moyennes, EMA, RSI, MACD/signal,
ATR simple et Wilder, Bollinger, rendement 20 observations, extrêmes de fenêtre,
ratio de volume, médianes de liquidité, capacité/scénario de sortie, effectifs,
fréquences, médianes, percentiles et intervalle de Wilson.

Le contrôle vérifie aussi les sorties manquantes alors qu'elles sont calculables,
les horizons, frontières d'événements, calendrier et la présence de l'univers
complet. Un écart bloque `run.py` avant la génération finale des pages. Le même
contrôle est dans `verify_nour.py`, donc dans les vérifications de PR et avant
publication. Le détail produit est `web/calculation-health.json`.

Sur ces entrées : **4 184 contrôles techniques/liquidité/statistiques**, plus
**444 contrôles arithmétiques financiers** dans le garde existant (510 avec les
66 contrôles de cohérence des scores). Aucun écart numérique restant détecté
par ces contrôles. Ce nombre désigne des assertions, pas des documents certifiés.

Deux cas limites supplémentaires sont sécurisés : un compteur de reprise nul,
négatif, booléen ou absent ne réutilise plus la liquidité antérieure ; un prix
booléen ne devient jamais une cotation à 1 DH. Les indicateurs OHLC rejettent
également les prix d'ouverture/extrêmes non positifs et les reprises booléennes.

## Réserves financières conservées

Le garde financier classe encore 19 dossiers avec au moins un indicateur bloqué,
55 avec des éléments à revoir, et 6 sans réserve détectée par ce garde.
Ces statuts portent sur les contrats de données disponibles, pas sur une
certification intégrale des comptes. Une perte observée ou une devise non
convertie peut légitimement bloquer un PER sans constituer une erreur de calcul.
Les mesures indépendantes d'un indicateur bloqué restent disponibles.

L'arithmétique passe sur les données présentes ; les PDF, dénominateurs de capital,
périmètres de dette, cours et ajustements historiques ne sont pas tous recertifiés.
Le fichier JSON distingue ces réserves titre par titre. Aucune dette contestée
n'est débloquée, aucun semestre n'est doublé et aucun score n'est recalibré.

## Reproduction

```bash
python tools/verify_nour.py --build --asof 2026-10-22
python tools/audit_calculations.py
```

Validation locale : **364 tests Python réussis**, contrôles de syntaxe et
scénarios JavaScript réussis, audits du site, des volumes, des calculs et des
comparaisons sectorielles sans violation bloquante. La procédure complète
`verify_nour.py --build --asof 2026-10-22` termine avec `Nour gate PASS`.
Le pourcentage de couverture, le typage statique, un audit d'accessibilité
complet et un navigateur réel local ne sont pas mesurés par cette validation.

Les régressions injectent explicitement une mauvaise moyenne, un indicateur
calculable supprimé, une fausse fréquence, un percentile/intervalle altéré,
un univers incomplet, des séances sans échange, des trous, doublons et futures
observations. Le contrôle est également exécuté sur les 80 historiques du dépôt.

Les pages générées localement ne prouvent ni une fusion ni un déploiement.
Ce lot est préparé sur une branche dédiée pour revue ; la publication du site
reste distincte. Les exports sont régénérés par le workflow après fusion.
