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

Deux leçons relues sont ajoutées par `record_lesson` en conservant toutes les
anciennes entrées : une occurrence candidate n'est pas une méthode comptable,
et la méthode immobilière dépend de l'émetteur. Les agents lisent l'index de
reprise partagé ; cette mémoire ne réentraîne aucun modèle.

## Validation et livraison

Les contrôles ciblés vérifient les dix nouveaux dossiers, la limite temporelle
de la revue du 27 octobre, l'absence de promotion AGMA, l'identité des calculs
sur 80 titres, les alias et les liens. Le jeu de réponses comptables compte
116 scénarios. Les parcours navigateur ajoutent les questions Immorente et
Balima aux trois largeurs pour contrôler la distinction de méthode.

La vérification complète, la revue CI et le résultat de publication seront
consignés après leur exécution. Le fournisseur LLM réel, le taux de couverture,
le typage et un audit complet d'accessibilité restent non mesurés. Les 56
dossiers restants ne sont pas décrits comme intégralement vérifiés.

La première revue navigateur a reproduit une erreur de scénario : l'analyse
était fixée au 26 octobre, excluant correctement les revues du 27. Le scénario
prend désormais le maximum entre la date du snapshot et la date du registre
comptable. Les horodatages des sources restent inchangés et sont contrôlés
séparément. Les tests d'analyse antérieure continuent à exiger l'exclusion des
nouvelles méthodes. La préparation du stress est rejouée avant la nouvelle CI.
