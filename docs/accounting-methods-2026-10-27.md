# Comptabilité — second lot du 27 octobre 2026

## Résultat préparé

Dix nouvelles revues de pages primaires : BCP, BOA, BMCI (BMC), Crédit du Maroc,
CIH, CFG Bank, Sanlam, AFMA, Immorente et Balima. Couverture à la construction :
21 revues de méthodes, 56 référentiels déclarés restant à approfondir et 3
dossiers à renseigner, sur 80 titres. Aucun conflit de déclaration. Les comptes,
ratios et scores conservent leurs valeurs canoniques ; aucun retraitement IFRS
ou conversion de périmètre n'est fabriqué. Moteur principal en lecture seule.

## Collecte et preuves

Les accès directs à l'AMMC ont expiré dans l'environnement de travail. La
collecte a donc été exécutée dans un job GitHub du dépôt Nour, sans écriture
dans les faits ou le site. Le [run de collecte 40437849414](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/40437849414)
a récupéré les onze PDF prévus. L'artefact `nour-accounting-evidence`, ID
12704698668, regroupe PDF, texte et manifeste de candidats ; conservation sept
jours. Ses empreintes ont été revérifiées sur les fichiers téléchargés avant
promotion. Les URL et SHA-256 des dix revues sont dans le registre versionné.

La préparation est réutilisable par `tools/prepare_accounting_review.py` et le
workflow manuel `nour_accounting_review.yml`. Le lot est limité à douze titres,
trois téléchargements concurrents et des URL AMMC contrôlées. Il réutilise les
bornes et validations du téléchargeur existant. Les erreurs restent locales et
ne deviennent pas des absences de publication. Les occurrences textuelles ne
produisent que des pages candidates : zéro fait promu automatiquement, zéro
score modifié. Aucun modèle ni service d'agent permanent n'est utilisé.

| Titre | Pages PDF contrôlées visuellement | Méthode effectivement décrite |
| --- | --- | --- |
| BCP | 25 (double page imprimée 48–49) | Consolidé IFRS ; trois stages IFRS 9, pertes attendues à 12 mois ou à maturité |
| BOA | 122–123 (imprimées 242–245) | IFRS IASB, classement modèle de gestion/SPPI et trois buckets |
| BMC | 9–10 | IFRS 9 ; IFRS 17 non applicable au contexte BMCI selon le rapport |
| CDM | 8 (imprimée 9) | IFRS ; IFRS 9 avec maintien autorisé d'IAS 39 pour la couverture |
| CIH | 6, 9 | IFRS et présentation PCEC ; IAS 40 à la juste valeur depuis 2022, trois buckets IFRS 9 |
| CFGB | 35–36 (imprimées 68–71) | IFRS, coût amorti des immobilisations et IFRS 9 ; pas d'immeubles de placement déclaré à l'arrêté |
| SAF | 10–11 | IFRS 17 à partir de 2025 ; PAA décès/non-vie et VFA retraite ; transition FVA pour les contrats VFA |
| AFM | 60–61 (imprimées 59–60) | IFRS UE ; consolidation, logiciels acquis et contrats IFRS 16 |
| IMI | 22 | IFRS UE ; immeubles de placement à la juste valeur annuelle sur expertise indépendante |
| BAL | 46–47 | Consolidé en normes marocaines ; patrimoine au coût historique et amortissements linéaires |

Chaque page citée a été rendue et inspectée. Quelques rendus PNG étaient
tronqués ; les pages Immorente et Balima ont été rendues de nouveau en JPEG
avant leur inspection. Aucun statut de contrôle visuel n'est attribué aux
autres pages, ni aux chiffres détaillés non relus. La mention générale « méthodes
contrôlées » reste limitée aux choix cités, pas à une certification du rapport.

## AGMA : résultat distinct d'une absence de données

Le PDF AMMC `Agma_RFA_2025.pdf`, SHA-256
`7558ce34b46cbe9bf95d2c73a26cbe5cf2bd7aed678be5cde140ae65ac427f5c`,
comporte 17 pages. Les premières occurrences de « référentiel » concernent le
RNVA, sujet métier automobile. La page 17 inspectée est une liste de mandats,
pas une note comptable. Aucune note explicite de méthodes n'a été identifiée
dans ce document. AGMA conserve donc sa déclaration et ses chiffres existants ;
aucune promotion de revue de méthodes. Rechercher l'ETIC ou le rapport complet
avec notes comptables à la prochaine reprise. Cela ne démontre pas que ces
notes ne sont publiées nulle part.

## Assistant et transmission

Les profils alimentent automatiquement les fiches repliées, le guide, les
réponses locales et le contexte sélectionné de l'assistant optionnel. Sanlam
reçoit une courte mention de comparabilité liée à la transition de 2025.
Les alias usuels BMCI, AFMA, AGMA, CFG Bank, Sanlam, Immorente et Balima sont
reconnus. Les liens du guide et des méthodes dans les réponses sont autorisés
explicitement par le filtre de liens ; les chemins non prévus restent refusés.

Trois leçons relues sont ajoutées par `record_lesson` en conservant toutes les
anciennes entrées : une occurrence candidate n'est pas une méthode comptable,
la méthode immobilière dépend de l'émetteur et la date d'analyse du scénario
doit inclure la revue comptable testée sans redater les cours. Les agents lisent l'index de
reprise partagé ; cette mémoire ne réentraîne aucun modèle.

## Validation et livraison

Les contrôles ciblés vérifient les dix nouveaux dossiers, la limite temporelle
de la revue du 27 octobre, l'absence de promotion AGMA, l'identité des calculs
sur 80 titres, les alias et les liens. Le jeu de réponses comptables compte
117 scénarios. Les parcours navigateur ajoutent les questions Immorente et
Balima aux trois largeurs pour contrôler la distinction de méthode.

Les résultats observés de la vérification complète, de la revue CI et de la
publication sont consignés ci-dessous. Le fournisseur LLM réel, le taux de couverture,
le typage et un audit complet d'accessibilité restent non mesurés. Les 56
dossiers restants ne sont pas décrits comme intégralement vérifiés.

La première revue navigateur a reproduit une erreur de scénario : l'analyse
était fixée au 26 octobre, excluant correctement les revues du 27. Le scénario
prend désormais le maximum entre la date du snapshot et la date du registre
comptable. Les horodatages des sources restent inchangés et sont contrôlés
séparément. Les tests d'analyse antérieure continuent à exiger l'exclusion des
nouvelles méthodes. La préparation du stress est rejouée avant la nouvelle CI.

Le rejeu a ensuite confirmé qu'au 27 les cours synthétiques du 22 deviennent
périmés pour le PER. Le moteur retire correctement ces ratios, sans valeur
nulle imputée. L'assertion navigateur impose désormais le nombre exact de
candidats calculables dans l'export ; elle exige des PER affichés seulement
lorsqu'il en existe et l'absence de faux PER lorsque la sélection est vide.
Ce cas est aussi reproduit par le test JS. Aucun cours n'a été redaté et aucun
garde-fou financier n'a été retiré.

## Vérification observée avant fusion

Le contrôle local complet a passé 478 tests Python, les réponses comptables
et les audits. Le scénario complémentaire de sélection vide porte désormais
le jeu comptable à 117 scénarios. La préparation de quarantaine a été rejouée
avec succès en conservant les 79 autres titres et leurs CSV identiques.

La [PR 40](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/pull/40)
a passé la [revue 40440613043](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/40440613043) :
478 tests Python, 117 réponses et 96 parcours navigateur (48 dégradés et
48 normaux). Les questions Immorente/Balima sont incluses aux trois largeurs.
Les deux erreurs de scénarios précédentes sont expliquées ci-dessus et
leurs protections anti-récidive sont conservées ; aucun test financier n'est
désactivé. La fusion est `599a44506ce5ff87855b9c0c9be70b90ec7d1299`, pour
l'arbre de source revu `c0de901fca7d45eecf0d484a0a93a4a68e9ea0a7`.

## Prochain lot préparé pour la reprise

Douze titres restant à documenter, avec une référence annuelle déjà présente
dans Nour : MNG, SMI, CMT, JET, SGTM, COL, CIM, LHM, IAM, MIC, M2M et S2M.
La présence de ces URL ne vaut pas contrôle des méthodes. Le workflow manuel
peut préparer leurs PDF avec cette liste de symboles ; reprendre les règles
de source, période, périmètre et validation visuelle avant toute promotion.
Ce lot suivant n'est ni exécuté ni déclaré vérifié par ce dossier.

## Publication réellement observée

La [publication 40441830954](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/40441830954)
a terminé avec succès le 27 octobre 2026 à 03:17:45 UTC (04:17:45 à Casablanca).
Elle a passé 478 tests Python et les 117 scénarios comptables, puis 144
parcours Chromium : 48 normaux, 48 avec ADI en quarantaine et 48 après
le déploiement sur le site réellement servi. Les nouveaux cas comptables sont
inclus aux trois largeurs. Aucun appel à un fournisseur LLM réel.

Une lecture HTTP indépendante des fichiers publics `accounting-coverage.json`,
`comptabilite.html` et `publication.json` a confirmé : 80 titres, 21 revues,
56 déclarations à approfondir, 3 dossiers à renseigner et aucun conflit.
Le manifeste public identifie le run 40441830954, le générateur
`599a44506ce5ff87855b9c0c9be70b90ec7d1299` et l’artefact
`07dc87186a881ce1f7fd240d9aaf1d1c56b7a442`.
SHA-256 du guide public observé :
`9c6a266c7f41fc825b29363374f50f55f2b29b3e0822cdf38ff202e391412080`.
Les indicateurs de certification et d’usage dans le score restent faux.

Les trois leçons et le dossier de reprise sont versionnés. Les chiffres
canoniques restent ceux des sources financières déjà retenues ; aucune
modification du moteur principal, aucune activation d’agent permanent ou
de service IA payant supplémentaire. La revue détaillée des 56 déclarations
et les trois dossiers à renseigner constituent la suite du travail.
