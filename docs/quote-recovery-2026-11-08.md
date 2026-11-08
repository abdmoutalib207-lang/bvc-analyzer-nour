# Récupération des six cours masqués — 8 novembre 2026

Le problème était un blocage persistant du contrôle local : une ligne déjà
mise en quarantaine n'était jamais réexaminée quand Wafabourse restait indisponible.
Pour ADH, DSW, ENK, MNG, RDS et VCNE, les cours et les bougies du 5 novembre
étaient pourtant présents et exactement identiques au nouveau relevé CDG.

Les historiques du principal ont été consultés au commit figé
`c92384a3a202d99322557e4f36199ad9a224a5f0`, strictement en lecture seule.
Les six dernières bougies sont identiques à Nour ; aucune copie destructive
d'historique n'était nécessaire. Les quantités, dates, empreintes et URLs sont
conservées dans `quote-recovery-2026-11-08.json`. Le principal et CDG peuvent
partager leur fournisseur amont ; cette égalité ne vaut pas validation indépendante.

| Titre | Cours MAD | Séance |
| --- | ---: | --- |
| ADH | 38,70 | 05/11/2026 |
| DSW | 750,00 | 05/11/2026 |
| ENK | 46,00 | 05/11/2026 |
| MNG | 1 489,00 | 05/11/2026 |
| RDS | 177,00 | 05/11/2026 |
| VCNE | 305,00 | 05/11/2026 |

Le relevé CDG a été récupéré de nouveau le 8 novembre : 81 lignes. La dernière
cotation ADH est le 5 novembre à 15:42:09, pas une cotation du 6 ou du 8.
Ne jamais dater une séance avec l'heure de consultation du flux.

La correction autorise un nouveau contrôle primaire uniquement si l'ancienne
quarantaine a le même symbole, code, domaine, séance et OHLCV/montant exacts,
avec un champ secondaire explicitement absent. Le relevé courant doit encore
passer tous les contrôles internes habituels. Une contradiction réelle, une
autre séance, un champ différent ou un relevé secondaire contradictoire restent
bloqués. Le statut multisource reste faux ; aucun agrégat n'est certifié.

Les anciens incidents restent ouverts dans le journal, avec leurs preuves.
Leur origine n'est pas reconstruite par supposition : les anciennes entrées
ne documentent pas toujours les valeurs avant/après. Cette reprise ne les
déclare pas résolus et ne modifie aucun cours ni volume pour le faire concorder.

Après retraitement local des observations courantes, les six prix redeviennent
consommables par le moteur, les historiques et les calculs admissibles : ADH
PER 34,33, DSW PER 16,55 ; les restrictions financières propres aux autres
indicateurs restent appliquées. Il ne s'agit pas d'un remplacement du libellé
« indisponible » dans l'interface.

Contrôle ciblé : sept tests de rapprochement local réussis, dont deux nouvelles
régressions couvrant les six lignes inchangées et le maintien des vrais conflits.
La validation complète et la publication seront vérifiées avant clôture.
