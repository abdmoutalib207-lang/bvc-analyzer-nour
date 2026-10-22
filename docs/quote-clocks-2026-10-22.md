# Cours principal et horodatages par valeur

Constat sur le site public le 22 octobre : ADI présentait 366 MAD (clôture du
21/10) en grand, alors que 357,35 MAD avait été collecté en séance le 22/10.
Le point provisoire était disponible dans le rapport, mais secondaire à l’écran.

Le moteur principal a été consulté en lecture seule : sa fiche rend explicite
la différence entre une valeur relevée en séance et un cours de clôture.
Nour reprend ce principe de lisibilité avec ses propres observations.

La liste complète et les fiches mettent désormais le cours provisoire disponible
en premier. Il garde son libellé, sa séance et son heure de collecte. La clôture
de référence reste affichée, et continue d’alimenter graphiques, ratios et score.
Sans point provisoire admissible, la clôture disponible reste le prix principal.
Aucun cours, score ou ratio canonique n’est remplacé par la présentation.

Deux horloges restent distinctes :

- `price_source_datetime` / `source_datetime` : date et heure locale brutes de
  `DateDernierCours`, conservées seulement si elles sont analysables ; l’affichage
  précise qu’il s’agit de l’heure indiquée par la source, sans inventer de fuseau ;
- `price_collected_at` / `intraday_observed_at` : moment effectif où le collecteur
  a recueilli le cours, avec fuseau, affiché en format français lisible.

Une heure source absente ou invalide reste non communiquée. Le passage global
du collecteur ne sert jamais à dater une transaction. Un titre non échangé garde
sa séance propre. Une bougie refusée conserve ses anciens horodatages.
Une observation identique acceptée actualise sa collecte sans changer ses cours.
Le contrôle de publication reste lié à la nouvelle empreinte du snapshot.

Vérification : cas en séance, clôture inchangée, observation périmée, date ancienne,
heure absente ou incohérente, conflit sans écrasement ; contrôles de prix et dates
sur la liste des 80 valeurs et les fiches testées dans Chromium.

## Blocage externe constaté pendant la livraison

La collecte du 22/10 retrouve 61 lignes et 196 645 452,38 MAD, sans différence
interne. La réponse Wafabourse contient cependant 60 lignes datées du 22/10,
20 emplacements vides et une ligne Aluminium du Maroc (`ALM`) portant
`DateDernierCours = 01/01/1900 10:17:00`, 2 titres, 3 720 MAD et 1 860 MAD
de cours. Son enveloppe ne contient pas de date globale de transaction.
Cette réponse ne peut pas attester une clôture du 22/10 pour ALM.

Le rapprochement final refuse donc la publication. Aucun remplacement de cette
date par l’heure de collecte ou celle du MASI n’a été effectué. La page officielle
ALM et le bulletin officiel BCFR_20261022.pdf ont retourné HTTP 503 lors de cette
vérification. BMCE a aussi été examiné en lecture seule dans le moteur principal :
son collecteur décrit une page avec heures mais sans date, insuffisante ici.

Cet état décrit le blocage initial de la PR 23. La suite est documentée dans
`publication-primary-2026-10-22.md` : publication avec réserves uniquement après
preuve exacte de la source principale, sans prétendre résoudre l’anomalie externe.
Les résultats de vérification et de publication se lisent dans le workflow réel.
