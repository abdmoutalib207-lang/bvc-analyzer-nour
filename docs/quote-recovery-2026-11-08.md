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

## Contrôles après collecte fraîche

La première publication (42485855155) a été refusée avant déploiement :
les diagnostics de dix conflits de volumes étaient copiés dans le contexte de
chaque société, faisant dépasser à T2S le plafond de 40 000 octets.
Le contexte est maintenant limité aux incidents du titre et aux incidents
collectifs ; compteurs et statuts globaux, erreurs de sources, preuves et réserves
financières restent conservés. Sur l'artefact échoué : T2S passe de 40 780 à
37 617 octets, sans augmenter le plafond. La parité Python/Worker est testée.

Cette collecte a aussi révélé des quantités CDG modifiées sur dix lignes,
dont ADH (1 566 874 contre 1 573 414 conservés) et Vicenne (29 883 contre
30 883). Leurs prix et OHLC sont identiques. Aucune quantité n'est choisie
arbitrairement pour effacer cet écart.

Le rapport expose donc `price_observation` uniquement lorsque les prix OHLC
primaires et conservés concordent exactement, pour la même séance et le même
titre, avec source et collecte datées. Les prix et ratios correspondants sont
consultables sur la fiche, dans le tableau du marché et dans l'assistant ;
`fundamental.quote_valuation` conserve le prix réellement utilisé pour les
ratios. Les contraintes comptables s'appliquent toujours. ADH : 38,70 MAD,
PER 34,33 et P/B 1,64 ; Vicenne : 305 MAD, sans déblocage de ses ratios financiers.

Les volumes contestés, statistiques courantes et scores restent indisponibles.
Un véritable conflit de prix ne produit aucune observation utilisable. L'écran
indique « Cours publié · volume à vérifier » et distingue ce prix de la
validation complète d'une cotation. Les incidents historiques ne sont pas
supprimés et aucun rapprochement multisource n'est revendiqué.

## Publication et contrôle réellement servi

Les PR 42 puis 43 sont fusionnées. Le code publié est
`4cb7a4587dfba9726746ad7b61056740f41998cd` ; les données et pages sont
enregistrées dans `89a9676bc4fee07a3071078957d9998da55704b8`.
Le [cycle 42512685007](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/42512685007)
est terminé avec succès le 8 novembre à 19:13 UTC.

Contrôles effectivement exécutés :

- 514 tests Python réussis, contrôles JavaScript et gate complet réussis,
  localement sur les données de l'échec puis sur la collecte fraîche en CI ;
- 48 parcours navigateur sur la construction normale, 48 sur le site temporaire
  avec ADI bloqué, puis 48 sur le site public réellement déployé ;
- audit public des montants/quantités : aucune défaillance du contrat de
  publication ; résultat explicite `checked_with_reservations` ;
- contrôle HTTP indépendant du rapport public et de la fiche ADH :
  80 titres, 78 cours affichables, DIS/DLM suspendus ; les six prix du tableau
  ci-dessus sont servis avec la séance du 5 novembre ;
- relecture visuelle dans Chromium de la fiche publique ADH : 38,70 MAD,
  PER 34,33, P/B 1,64 ; historique jusqu'au 5 novembre, 840 séances.

Le relevé utilisé par le contrôle final concorde avec les lignes conservées :
la publication comporte 78 prix canoniques et aucune `price_observation`.
Cela ne résout pas les dix divergences de quantités observées par le collecteur
un peu plus tôt dans le même cycle. Elles restent dans les diagnostics et
le journal. Les réponses successives de la source diffèrent ; ni une
corroboration indépendante ni la résolution de ces incidents ne sont affirmées.
L'intégrité globale reste partielle : 66 lignes contre 67 attendues, écart
de 932,62 MAD et 221 titres sur l'agrégat ; la source secondaire est indisponible.

Le repli prix seul a été vérifié sur l'artefact réellement divergent :
dix prix datés consultables, volume/statistiques/scores bloqués. L'oracle
financier de publication vérifie maintenant le prix explicitement déclaré dans
`quote_valuation` avant de recalculer les ratios ; un prix incohérent est refusé.
Le contrôle empêche donc aussi une disparition ultérieure des ratios lors de
l'audit de publication.

La croissance du CA ADH et son ratio dette nette/EBE restent suspendus pour
leurs motifs financiers documentés ; les restrictions propres aux autres
sociétés sont conservées. Ce lot ne prétend pas compléter tous les fondamentaux.
Le principal n'a reçu aucune écriture.

Leçons de reprise : tester le collecteur puis le contrôle secondaire, qui
peuvent recevoir des réponses différentes ; contrôler le rapport après son
oracle financier, puis les pages réellement servies. Un test isolé du moteur
ne suffit pas à prouver qu'un chiffre restera présent après publication.
