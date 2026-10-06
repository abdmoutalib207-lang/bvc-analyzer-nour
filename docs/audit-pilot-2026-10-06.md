# Audit d'utilisabilité et de préparation au pilote — Nour

Date : 06/10/2026. Périmètre : produit, données, calculs, exploitation et
assistant; aucune analyse réglementaire. Base inspectée : `848a429` et site
effectivement servi après le workflow
[37533659969](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/37533659969).
Le moteur principal reste exclusivement consultable et n'a pas été modifié.

## Verdict et pourcentage

**Pilote limité possible après publication et contrôle du présent lot. Diffusion
large prématurée. Préparation estimée : 80/100; moteur de calcul : environ 90 %
du périmètre actuellement annoncé.** Ces évaluations sont un jugement de
préparation fondé sur la grille ci-dessous, pas un taux de données exactes, une
certification ou une performance de prévision. Aucun pourcentage universel
d'achèvement n'est mesurable sans cahier des charges final.

| Dimension | Points / maximum | Justification et limite |
|---|---:|---|
| Calculs et garde-fous | 23/25 | 412 contrôles arithmétiques indépendants sur les valeurs disponibles, contrats et tests de non-fuite future; pas une validation empirique du score |
| Fondamentaux et traçabilité | 13/20 | 77 références annuelles; 15 revues de pages primaires, 62 imports encore à revérifier; ratios manquants conservés absents |
| Collecte et fraîcheur | 10/15 | Derniers workflows réussis et volumes rapprochés; retard de 204,6 minutes sur la dernière édition programmée, radar actualités partiel |
| Interface et graphiques | 14/15 | 89 pages contrôlées, graphiques interactifs, aide du laboratoire, parcours Chromium à 375/768/1440 px; Safari iPhone physique et accessibilité complète non mesurés |
| Assistant | 12/15 | Réponses ciblées, sources, contexte conservé, 29 cas précis et contrôles généraux; compréhension limitée aux intentions reconnues, pas une conversation générative |
| Organisation du pilote | 8/10 | Protocole et fiche de retours ci-dessous; pas encore de résultats de véritables testeurs |
| Total | **80/100** | Réévaluer après le pilote; ne pas confondre avec la fiabilité des prédictions |

Avant ce lot, la faiblesse des réponses ciblées justifiait 6/15 pour l'assistant,
soit 74/100 dans cette même grille. Les points ne proviennent pas d'une mesure
statistique et ne doivent pas être affichés comme une note financière.

## Les fondamentaux sont-ils corrects ?

L'arithmétique des **valeurs disponibles et de leurs entrées exportées** concorde :
43 BPA, 56 valeurs comptables par action, 40 PER, 53 P/B, 45 ROE, 55 dettes
nettes, 35 dettes nettes/EBITDA, 5 croissances de CA, 11 croissances de PNB,
2 rendements de dividende et 67 additions du score, soit **412 contrôles**.
Le recalcul utilise Decimal et les valeurs non arrondies des preuves, sans
appeler le calculateur Nour. Tolérance : demi-centième sur les sorties arrondies.
Cela contrôle la cohérence des calculs; cela ne prouve ni l'exactitude de toutes
les valeurs sources, ni leurs périmètres, ni tous les nombres d'actions.

| Couverture au 06/10 | Disponibles / univers |
|---|---:|
| Références annuelles | 77/80 |
| Références récentes semestrielles | 76/80 |
| BPA | 43/80 |
| PER au cours observé | 40/80 |
| P/B au cours observé | 53/80 |
| ROE annuel sur fonds propres de clôture | 45/80 |
| Dette nette/EBITDA industriel | 35/80 |
| PNB annuel | 11/80 |

Les ratios industriels ne s'appliquent pas à toutes les sociétés financières :
l'absence n'est pas toujours un dossier incomplet. Trois références annuelles
manquent : DIS, DLM, IBM. La présence d'une référence semestrielle n'atteste
pas une vérification indépendante : 68 gardent un statut d'import, sept portent
une revue primaire et JET un rapprochement avec réserves.

Les 15 dossiers annuels avec revue de pages primaires sont HAL, MRL, BOA, BMC,
BCP, CASH, ATW, CDM, EQD, SLM, AGM, MGL, MDP, CIH et SAF. Cette liste décrit
les preuves documentées du dépôt, pas une nouvelle revue intégrale de leurs PDF.
Les écarts sensibles et les changements de capital restent visibles : CIH,
CDM, HAL notamment gardent les ratios au cours actuel indisponibles lorsque
la comparabilité des dénominateurs n'est pas établie. CASH utilise les
rapprochements documentés du lot du 05/10, avec réserves et BPA de clôture
indicatif. M2M S1 publie un résultat total, sans RNPG isolé. JET S1 retient
le RNPG rapproché, avec réserve; aucun semestre n'est doublé.

Correction du présent audit : **12 preuves de nombre d'actions avaient une
unité d'affichage MMAD par défaut**. Elles sont désormais étiquetées « actions ».
Les entrées numériques, les ratios, les scores et les références semestrielles
du snapshot inspecté sont identiques avant/après cette correction.

## Ce que le moteur sait réellement faire

67 scores sont calculables, cinq partiels et huit non calculables. Le score
est descriptif : tendance, momentum, activité, liquidité et ROE annuel lorsque
disponible. Le PER, la dette/EBITDA et le RNPG semestriel ne sont pas directement
des facteurs de cette version du score. Une baisse semestrielle ne déclenche
donc pas automatiquement une baisse de note. Sa couverture doit être lue.

L'historique MASI contient 918 séances du 02/01/2023 au 06/10/2026. L'archive
des scores publiés ne contient qu'une première journée, le 06/10/2026 :
**aucune performance prospective du score n'est validée**. Les fondamentaux
actuels ne sont pas réinjectés dans les reconstructions historiques faute de
dates de disponibilité prouvées. Les rendements historiques sont calculés
sur cours, hors dividendes; les trous ne sont pas interpolés.

68 titres ont une observation de la séance d'analyse; 12 ont une date plus
ancienne ou absente. Une fiche ancienne ne doit pas entrer dans le volume
global de la séance. Le volume CDG et la somme des 68 lignes concordent à
349 551 480,02 MAD dans le snapshot inspecté. Les dates et états d'archive
macro sont propres à chaque marché; une collecte réussie n'implique pas que
tous les flux soient temps réel ou complets.

## Corrections de l'assistant et limites restantes

Le lot donne priorité à la mesure demandée et conserve le titre pour les
questions suivantes. Exemples à essayer : « MM50 ADI », « Et son RSI ? »,
« Compare le PER ADI et JET », « RNPG JET S1 2025 », « RNPG M2M S1 2026 »,
« Pourquoi le PER CIH est indisponible ? », « Volume global MASI »,
« MASI le 11/03/26 et le 31/03/26 », « Prix du Brent ».

Les dates invalides, titres inconnus, exercices absents et questions non
reconnues sont signalés. Le RN total ne devient pas un RNPG. ROIC, PER global
historique et scénarios conditionnels de prochaine séance restent absents.
La fenêtre suit des règles explicites; les formulations libres, les longues
conversations et les erreurs de frappe ne sont pas toutes comprises.
Une page déjà ouverte doit être rechargée pour récupérer une nouvelle collecte.
L'IA générative optionnelle reste désactivée; aucune clé ni appel payant ajouté.

## Protocole de remise à un groupe

Commencer avec **5 à 10 personnes pendant 10 séances**, comprenant quelques
utilisateurs d'iPhone. Toutes peuvent explorer l'interface et les graphiques;
les comparaisons comptables du pilote doivent distinguer les dossiers revus
des imports encore non revérifiés. Les indisponibilités sont des résultats
attendus, pas des valeurs à compléter à la main.

1. Première séance : trouver la date de collecte, comparer deux titres,
   sélectionner une plage MASI, ouvrir l'aide « ? », obtenir une réponse précise
   de l'assistant et ouvrir sa source.
2. Séances suivantes : chacun réalise trois tâches au choix et note succès,
   durée, question exacte et obstacle. Le responsable relève l'heure réelle
   de publication et les erreurs de collecte.
3. Chaque problème : date/heure, URL et titre, appareil/navigateur, action ou
   question exacte, résultat observé, résultat attendu, capture facultative.
   Aucun envoi automatique ni outil de communication n'est configuré.
4. Bloquant : chiffre attribué au mauvais titre/périmètre, donnée ancienne
   présentée comme séance actuelle, erreur de calcul confirmée, page
   inutilisable. Suspendre l'élément concerné et reproduire avant correction.
5. Critères de sortie : zéro défaut bloquant ouvert, au moins 90 % de réussite
   sur les tâches définies et 90 % sur un corpus de 20 questions réellement
   posées, avec « indisponible » accepté quand justifié; cinq publications
   consécutives contrôlées; un parcours Safari iPhone complet sans obstacle.
   Ces seuils sont les objectifs du pilote, pas des résultats déjà obtenus.

Avant une diffusion plus large : revérifier les 62 imports annuels par lots et
priorité d'usage, compléter les documents manquants, rapprocher les capitaux
non résolus, stabiliser les délais de collecte, mesurer les retours et
l'accessibilité, et constituer une archive prospective suffisante avant toute
affirmation sur le pouvoir du score. Une IA générative n'est pas un préalable
au pilote; une réponse exacte, datée et honnête sur ses limites l'est.

## Reproduction et validation

`python tools/verify_nour.py --build --asof 2026-10-06`
et `python tools/audit_readiness.py` : construction, 129 tests Python,
contrôles JS (320 contrôles généraux et 29 cas précis assistant, 2 400 cas de
contrôle du graphique, 108 cas laboratoire), 89 pages et audit arithmétique.
Les parcours Chromium réels sont exécutés par le workflow sur les pages
construites puis sur le site publié, avec captures à trois largeurs.
Le dernier workflow de publication doit être réussi avant remise au groupe.
La couverture de code, l'audit axe complet et un véritable fournisseur LLM
n'ont pas été mesurés. Le [relevé machine](audit-pilot-2026-10-06.json) conserve
les compteurs et la limite du contrôle arithmétique.
