# Lot Nour : qualité comptable et comparables — 11 octobre 2026

Périmètre : Nour exclusivement. Aucun fichier, branche, PR ou réglage du moteur
principal modifié. Base de départ `89b8bf19abdefb763969ec21dcbd062244e4bf19`.

## Apport de Simply Wall St

Sources consultées :
- [Méthode des références sectorielles](https://github.com/SimplyWallSt/Company-Analysis-Model/blob/master/industry_averages.markdown)
- [Informations ADI](https://simplywall.st/stocks/ma/real-estate-management-and-development/cbse-adi/alliances-developpement-immobilier-shares/information)
- [Santé financière ADI](https://simplywall.st/stocks/ma/real-estate-management-and-development/cbse-adi/alliances-developpement-immobilier-shares/health)

La méthode publiée propose notamment des médianes et un élargissement géographique
quand un secteur national comporte moins de cinq entreprises. Nour conserve une
implémentation indépendante : au moins quatre autres ratios compatibles, sans
élargissement automatique à une région ou au marché entier. Ce seuil est une
convention prudente, pas une preuve de significativité statistique.

La version récupérée de la page d'information ADI porte des cours du 24/08/2026,
et celle de santé financière du 08/06/2026. Elles ne forment pas un instantané
actuel unique. Les informations financières sont normalisées par S&P Global ;
la page distingue les analystes recensés des contributeurs aux estimations.
Les données, prévisions, objectifs et scores du fournisseur ne sont ni copiés
dans les calculs ni collectés automatiquement. Un lien de consultation secondaire
est proposé sur ADI. Le dépôt méthodologique annonce CC BY-NC-SA 4.0 ; aucun
texte, code ou visuel sous cette licence n'est incorporé au moteur Nour.

Décision : utile comme référence méthodologique et pour repérer des écarts à
vérifier. Pas retenu comme alimentation automatique gratuite et stable. Une telle
alimentation nécessiterait un accès documenté et des conditions de réutilisation
adaptées, ainsi qu'une vérification des périodes et conventions comptables.

## Revue primaire ADI

[Rapport annuel 2025 AMMC](https://www.ammc.ma/sites/default/files/ADI_RFA_2025.pdf)

SHA-256 : `0d076ef448b6228ec8ff2ad60c2368044382d545ef84f51afb133636e4c538bc`.
Pages PDF et imprimées 21, 22, 50 rendues puis lues visuellement. Le rapport
complet, la moyenne pondérée des actions, l'autocontrôle et le semestre ne sont
pas recertifiés par ce lot.

| Fait | Valeur retenue | Page |
|---|---:|---:|
| RNPG 2025 | 407,601 MMAD | 22, recoupé 21 |
| Fonds propres groupe 2025 | 3 993,181 MMAD | 21 |
| Fonds propres groupe 2024 | 3 668,286 MMAD | 21 |
| Fonds propres ensemble consolidé 2025 | 4 084,918 MMAD | 21 |
| CA 2025 | 2 431,512 MMAD | 22 |
| CA 2024 | 2 363,364 MMAD | 22 |
| Titres émis à la clôture | 22 078 588 | 50 |

Le CA exact remplace les résumés arrondis 2 432 et 2 363 : croissance 2,88 %,
contre 2,92 %. ROE de clôture inchangé à 10,21 %. ROE sur fonds propres moyens
ajouté séparément : 10,64 %, sans effet sur le score ni mélange des comparaisons.
RNPG 407,601 et minoritaires -5,843 recoupent le résultat total 401,758.
Le total des fonds propres ne remplace jamais leur part du groupe pour le P/B.
Rejeu idempotent : `python tools/reconcile_adi_oct11.py`. Le S1 reste identique.

## Dette : contrôle sur tout l'univers

Le calcul dette financière moins trésorerie-actif est rapproché de l'endettement
net publié lorsqu'il est présent. Écart supérieur au maximum de 1 MMAD et 2 %
du montant publié : valeurs conservées dans le rapprochement, dette nette et
multiple non utilisables. La tolérance absorbe les arrondis mais ne certifie pas
un périmètre. Une absence de référence est marquée `not_cross_checked`, jamais
transformée en zéro. Une trésorerie nette n'est pas un multiple négatif.

| Titre | Calcul bilan (MMAD) | Publication (MMAD) | État |
|---|---:|---:|---|
| ADI | 1 361,489 | 1 303 | À rapprocher |
| MNG | 10 933,2 | 12 674 | À rapprocher |
| MUT | 989,222 | 828 | À rapprocher |

Ces postes proviennent des références Nour existantes ; ils ne sont pas trois
nouvelles revues intégrales des PDF. Chez MNG, le texte importé évoque les dérivés
et comptes associés ; chez MUT, une dette bancaire. Une explication textuelle
ne suffit pas à certifier une égalité sur pièce. Aucun des deux nombres n'est
choisi automatiquement. DTT, HAL et MSA restent dans la tolérance ; MSA conserve
son montant de trésorerie nette, avec multiple absent.

## Groupes de comparaison

Registre indépendant `nour/peer_groups.py`, appliqué aux identités du référentiel
Nour et aux rapports annuels déjà référencés :
- promoteurs ADI/ADH/RDS séparés des foncières ARD/IMI/BAL ;
- assureurs WAF/ATL/SAF séparés des courtiers AFM/AGM ;
- crédit-bail MGL/MRL, crédit consommation EQD/SLM/DIS et paiements CASH séparés ;
- DHO et REB ne sont pas assimilés à des entreprises industrielles comparables.

Les autres groupes restent les secteurs larges existants, explicitement
étiquetés comme tels. Ce lot ne prétend pas achever toute la taxonomie par métier.
Même groupe, norme, périmètre, exercice, date de clôture comptable, monnaie et
date de cours sont requis. Les pairs, valeurs, exclusions et raisons d'absence
sont exportés et expliqués sur les fiches et dans l'assistant. Aucun chiffre
extrême n'est supprimé uniquement pour sa distance à une médiane.

## Stabilité du workflow

Le run `37952817561` du 09/10 a échoué sur un test qui exigeait l'absence de cours
provisoire ADI, alors que le collecteur en avait fourni un. Le test lit désormais
l'état du rapport et des scénarios indépendants vérifient cotation présente,
absente, expirée et clôturée. La couverture documentaire du test n'est plus
figée à 77 références.

## Validation et limites

Le lot conserve `nour-quant-v1`. À date et entrées de marché identiques, les 80
scores ne changent pas. Le vieillissement normal d'un cours peut modifier son
état lors d'une construction à une date ultérieure : ce n'est pas un effet de
la nouvelle comparaison.

La comparaison plus stricte réduit les références disponibles : les autres
titres conservent leurs ratios individuels et les motifs d'abstention. Les
pièces comptables encore importées, les dettes à rapprocher, les changements
de capital et le fournisseur IA Cloudflare restent des chantiers distincts.
Pas de performance prédictive ou d'acceptation par les utilisateurs prétendue.
