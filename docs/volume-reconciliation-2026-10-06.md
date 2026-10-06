# Rapprochement du volume CDG — 6 octobre 2026

L'utilisateur a signalé un écart entre le volume global de Nour et le PDF
« Indices du mardi 6 octobre 2026.pdf ». Empreinte SHA-256 du PDF examiné :
`5b14c79d49e42371ec5d52b7d3fc8212002dffacfbc4ae14a31e799852621623`.

| Relevé | Montant DH | Actions échangées |
| --- | ---: | ---: |
| Somme des 68 lignes échangées du PDF | 349 551 480,02 | 1 219 185 |
| Somme des 68 fiches Nour datées du 06/10/2026 | 349 551 480,02 | 1 219 185 |
| Synthèse Nour relevée le 06/10 à 18:37:08 UTC | 346 377 516,02 | 1 213 968 |
| Écart PDF moins ancienne synthèse | 3 173 964,00 | 5 217 |

Le PDF comporte 81 codes uniques, dont 68 lignes avec échanges. Les fiches
Nour d'autres dates sont exclues : additionner toutes les dernières fiches
produirait un total couvrant plusieurs séances.

Pendant les vérifications, la réponse CDG initiale correspondait à l'ancienne
synthèse Nour. Une nouvelle lecture d'INDICE-SYNTHESE (champ DateJour
06/10/2026 19:00:57) et la somme des lignes MARKET-RESUME de la même séance
ont ensuite donné 349 551 480,02 DH, en accord avec le PDF et les fiches Nour.
Les réponses CDG ont donc évolué pendant le contrôle. On ne peut pas conclure
à des annulations de transactions à partir de ces seuls relevés.

La différence initiale était répartie sur neuf titres :

| Titre Nour | Écart DH (PDF moins réponse API initiale) |
| --- | ---: |
| AFI | 324,00 |
| AKD | 4 040,00 |
| ATW | 1 340 000,00 |
| CASH | 2 150,00 |
| CIH | 930,00 |
| CMGP | 810,00 |
| HPS | 1 629 075,00 |
| JET | 164 630,00 |
| TGCC | 32 005,00 |

## Correction

`market_volume_audit` rapproche le montant CDG avec les volumes réels des
fiches de la même date. Le nombre de fiches doit correspondre au nombre de
valeurs échangées annoncé par CDG, les symboles doivent être uniques et les
montants disponibles, finis et non négatifs. Sans cette couverture, le
rapprochement est incomplet et ne certifie aucun total. Les volumes estimés
et les fiches d'autres séances ne sont jamais utilisés.

Un écart supérieur à un centime apparaît explicitement sur la page de marché,
avec les deux montants et l'écart absolu. La synthèse CDG reste affichée ; le
contrôle ne remplace aucune observation et ne modifie aucun score. Une
concordance vérifie seulement la cohérence des montants, pas leur certification
comptable ni l'exhaustivité de la source. Le contrôle ne rapproche pas encore
le nombre d'actions ni le nombre de transactions.

Source publique : https://www.cdgcapitalbourse.ma/Bourse/market.
Le moteur principal n'a pas été modifié.
