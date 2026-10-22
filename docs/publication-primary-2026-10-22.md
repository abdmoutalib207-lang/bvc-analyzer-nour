# Publication du 22 octobre : fraîcheur et niveau de preuve séparés

Le run 39846316520 collecte les 61 lignes de clôture mais refuse la publication
à l'audit final : `incomplete`, malgré `publication_safe=true` dans le garde-volume.
Le détail retenu retrouve exactement les agrégats de la source principale :
196 645 452,38 MAD et 1 025 534 actions. Le moteur principal montre ces mêmes
agrégats et ADI à 369 MAD, mais utilise aussi CDG : ce n'est pas une deuxième
source indépendante. Aucune modification du moteur principal.

Wafabourse renvoie pour ALM la date `01/01/1900 10:17:00`, contre
`22/10/2026 10:17:00` chez CDG. La date Wafabourse n'est jamais remplacée.
Des montants détaillés divergent également dans les observations de contrôle :
une source invalide n'est pas une preuve de consensus. Le statut multisource
reste faux. Les observations CDG peuvent varier entre deux captures ; toute
discordance de lignes ou d'agrégats du relevé retenu continue à bloquer.

## Contrat nouveau, explicite et borné

`primary_checked` / `primary_only` publie exclusivement un snapshot inchangé
retrouvant chaque OHLC, cours, date, quantité et montant CDG ainsi que ses deux
agrégats et son univers exact. Le rapport exporté est contrôlé à nouveau contre
les preuves par ligne, les empreintes des observations et le SHA-256 exact du
snapshot. Une preuve périmée, un cours/volume modifié, un doublon, une somme
incohérente, une correction proposée ou un conflit valide refuse ce mode.

Ce statut ne certifie pas l'exactitude financière de la source principale.
Il permet de consulter une donnée actualisée avec réserves sans appeler
« validation multisource » une observation qu'on ne peut pas recouper.
La bannière publique et l'assistant conservent cette distinction. Aucun incident
n'est résolu et aucune correction de volume n'est autorisée par ce statut.
Un second fournisseur valide et contradictoire reste un conflit bloquant.

Les prix primaires et leurs horloges proviennent du changement préparé en PR 23 :
cotation (heure locale explicitement fournie par la source), collecte (instant
avec fuseau), dernier contrôle du collecteur (tentative distincte). Un titre non
échangé conserve sa vraie date antérieure ; les informations absentes le restent.

## Anti-récidive

`tests/test_primary_publication.py` vérifie les sources invalides ou indisponibles,
les preuves trafiquées/périmées, les modifications d'exports, les conflits valides,
les écarts agrégés et les dates 1900. `tests/test_quote_clocks.py` protège la
distinction des trois horloges et l'immuabilité des calculs de clôture.
Les parcours Chromium contrôlent les prix et horloges sur l'accueil et les fiches.
La réussite locale n'est pas une preuve de publication ; vérifier Actions et Pages.
