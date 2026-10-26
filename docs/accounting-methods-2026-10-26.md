# Méthodes comptables — lot du 26 octobre 2026

## Résultat et portée

Le moteur Nour distingue le référentiel effectivement déclaré par une société
des règles générales applicables sous conditions. Aucune conversion de comptes,
aucune modification des formules, des chiffres canoniques ou du score. Le moteur
principal `-bvc-analyzer` demeure exclusivement en lecture seule.

Le registre `knowledge/accounting_methods.json` contient 16 thèmes et 11 revues
primaires limitées à des pages sélectionnées des publications annuelles 2025.
Sur l'état de construction du lot : 80 titres, 11 revues de méthodes, 66
référentiels déclarés restant à approfondir, 3 publications manquantes et aucun
conflit entre la déclaration existante et les nouvelles pages contrôlées.
Cette couverture ne certifie ni les autres pages des rapports ni tous leurs
chiffres. Une nouvelle période, URL ou empreinte exige une nouvelle revue.

Les profils sont ajoutés au rapport après le calcul du score. Ils accompagnent
les fiches dans les volets repliés, le guide `comptabilite.html`, les réponses
locales de l'assistant et les champs sélectionnés pour l'assistant optionnel.
Les changements ADI/RDS/Wafa Assurance produisent une courte mention de
comparabilité ; les explications détaillées restent accessibles à la demande.

## Rectifications de la réponse soumise

- La circulaire AMMC 03/19 permet des comptes consolidés en normes en vigueur
  au Maroc ou IAS/IFRS ; la cotation n'impose pas IFRS à tous les groupes.
  Le recueil AMMC de mars 2026, page PDF 762, articles 2.7 et 2.8, porte la règle
  actuelle. L'option IFRS devient définitive selon ce texte.
- Les comptes sociaux ne sont pas universellement « CGNC » : les référentiels
  sectoriels, notamment le PCEC des établissements de crédit, restent distincts.
- Wafa Assurance applique IFRS 17/IFRS 9 dans son consolidé 2025 ; AtlantaSanad
  déclare un référentiel marocain dans le rapport revu. Les produits d'assurance
  et le résultat des services d'assurance sont deux notions distinctes.
- ADI et TGCC déclarent une consolidation CNC avis n°5 ; RDS et Addoha déclarent
  IFRS. Le secteur immobilier ou BTP ne suffit pas à choisir le référentiel.
- Le PCSI actualisé s'applique à compter du 1er janvier 2025 selon l'avis CNC
  n°21, dont le report est publié par le ministère des Finances. ADI et RDS
  décrivent des effets différents selon les documents et les périmètres.
- HPS déclare en 2025 ses frais de recherche et développement en charges
  (143,7 MMAD) dans ses comptes en normes marocaines. IAS 38 ne signifie pas
  activation automatique ; une activation conforme n'est pas une manipulation.
- IAS 40 ne rend pas la juste valeur universelle. Aradei publie sa méthode
  particulière, avec immeubles en construction au coût jusqu'à achèvement.
- Une hausse des ECL ne prouve pas l'anticipation d'une crise. Un coût du risque
  dépend aussi des volumes, migrations, paramètres et reprises.
- Le dividende ne se déduit pas du RNPG. Les comptes sociaux, pertes antérieures,
  réserves obligatoires, report bénéficiaire, situation nette et décision de
  l'assemblée interviennent (loi SA, articles 329 à 331, recueil page PDF 102).
- L'absence de cotation en actions ne supprime pas les obligations d'information
  d'un émetteur de titres de créance faisant appel public à l'épargne. Nour
  explique une publication utile sans inventer un cours d'action OCP/ONEE/RAM.

## Documents effectivement revus

Les pages ci-dessous sont les pages du PDF, pas nécessairement les pages
imprimées. Les SHA-256 complets, URLs et dates de revue sont dans le registre.
Chaque page citée a été rendue puis inspectée visuellement. Les autres pages
ne portent aucun statut de contrôle visuel par ce lot.

| Titre | Pages PDF | Constat limité au document 2025 |
| --- | --- | --- |
| ADI | 14, 24, 25 | Consolidé marocain CNC avis 5 ; promotion à l'achèvement, services à l'avancement ; commentaire de changement de règles |
| ADH | 59 | Consolidé IFRS ; méthode détaillée de revenu non revue dans ce lot |
| RDS | 17, 21 | IFRS consolidé ; acte notarié à partir de 2025 ; changement rétrospectif consolidé, prospectif social |
| ATL | 146 | Référentiel marocain déclaré dans le rapport des commissaires aux comptes |
| ARD | 7, 8 | IFRS ; immeubles de placement à la valeur de marché, construction au coût jusqu'à achèvement |
| HPS | 61 (double page 120–121) | CNC avis 5 ; R&D en charges ; méthodes de prestations décrites |
| TGCC | 98 (double page 194–195) | CNC avis 5 ; aucune attribution automatique d'IFRS 15 |
| EQD | 64 (double page 126–127) | Consolidation CNC ; provisionnement BAM déclaré et traitement financier LOA |
| SLM | 83 | Comptes sociaux PCEC ; pas d'assimilation automatique à des comptes IFRS |
| WAF | 20 | Première publication IFRS 17/IFRS 9 en 2025, bilan de transition au 01/01/2024 et comparatif retraité |
| ATW | 57, 83 | Consolidé IFRS ; principes de pertes attendues et paramètres de risque décrits |

Pour ADI, les 2,432 milliards de DH publiés et les 2,7 milliards à règles
2024 constantes sont deux présentations de gestion distinctes et arrondies.
La seconde ne remplace pas le chiffre canonique et ne résout pas l'écart de
dette nette déjà documenté (58,49 MMAD). Aucun rapprochement de dette nouveau
n'est prétendu réalisé par ce lot.

Les règles générales renvoient aux synthèses et indications primaires de la
Fondation IFRS : IFRS 9, IFRS 17, IFRS 15 et principal/agent, IAS 2, IAS 37,
IAS 38, IAS 40, IFRS 16. Elles sont conditionnelles au référentiel publié.
La source du PCSI est la publication du ministère relative à l'avis CNC n°21.

## Transmission et mémoire

AGENTS.md, CLAUDE.md et `.ecc/memory/project.md` renvoient à la même procédure
`docs/agent-learning.md`. Trois leçons relues sont ajoutées avec
`nour.error_memory.record_lesson` : référentiel par document, R&D sans activation
automatique, publié/retraité/simulation distincts. Les anciens incidents et
leçons sont conservés. Les intervenants qui lisent ce dépôt disposent ainsi
des mêmes méthodes à leur prochaine reprise ; aucun modèle n'est réentraîné,
aucun agent permanent ou service payant n'est activé.

## Vérification

Les tests dédiés vérifient les 11 dossiers, les périodes et empreintes, les
preuves de pages, les conflits locaux, le référentiel propre du semestre et
l'égalité exacte des fondamentaux, indicateurs techniques, scores, statistiques
historiques et résultats sectoriels avant/après sur les 80 titres. Les tests de
réponses utilisent l'export réel et contrôlent 106 réponses et régressions :
choix de méthode, titres, année différente, semestre, suivi de conversation et
absence de mutation des données. Aucun appel LLM n'est nécessaire.

Le contrôle complet requis reste `python tools/verify_nour.py --build --asof
2026-10-26`. Les parcours navigateur incluent le guide et des questions HPS,
RDS et Wafa Assurance à trois largeurs, avec leurs liens de sources, y compris
sur une génération où ADI est volontairement mis en quarantaine. Les résultats observés sont consignés ci-dessous.

## Limites à reprendre

Les autres méthodes détaillées doivent être revues par lots d'émetteurs.
Le référentiel déjà relevé sur 66 dossiers n'est pas une revue de toutes leurs
notes comptables. Les trois dossiers sans publication annuelle renseignée dans Nour (DIS, DLM
et IBM) restent à compléter ; aucune absence de publication officielle n’est
affirmée. Aucune promesse de répondre correctement à toute question possible.
Les réponses doivent distinguer faits, règles générales et hypothèses, et
demander la période lorsqu'elle manque. Aucune normalisation IFRS/CGNC, aucun
backtest point-in-time nouveau et aucune causalité économique ne sont inventés.
Le vrai fournisseur LLM, le typage, le taux de couverture et un audit complet
d'accessibilité restent non mesurés. L'intégration de contexte comptable utilise
le sélecteur de politique déjà déployé, sans changement du binaire Worker ;
sa transmission est vérifiée par les tests Python/JS, sans appel commercial.

## Preuves complémentaires et exécution du lot

Le tableau de retraitement RDS, page PDF 18 du même RFA (empreinte du
registre), a aussi été rendu et contrôlé visuellement. Son chiffre d’affaires
2024 ajusté est de 233,682 MMAD contre 135,909 MMAD publié à l’origine. La base
de croissance déjà présente dans Nour est bien 233,682 MMAD ; aucun remplacement
par l’ancienne base n’a été effectué. Ce contrôle complémentaire ne certifie
pas les autres postes de cette page.

La vérification locale complète est passée : 473 tests Python, 106 réponses
comptables, contrôles JS/Worker et audits des exports, pages, marché et calculs.
Le contrôle arithmétique publié par cette construction contient 4 184 contrôles
sans échec. La révision JET du test de préservation vérifie maintenant que le
libellé semestriel importé est transmis au profil, tout en exigeant l’identité
de tous les autres champs.

La [PR 39](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/pull/39)
a passé la [revue 40416119748](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/40416119748) :
473 tests Python et 96 parcours navigateur, 48 avec ADI en quarantaine et
48 sur la génération normale. Les deux ensembles incluent le guide et les
réponses comptables aux trois largeurs. Aucun appel à un vrai fournisseur LLM.
Fusion : `d104fff84f85f5924d839b775e31397e1401409f` ; arbre de code revu
`1f87bc8dd974be0986cffadcb5ea1dd539305364`.

La [publication 40417297600](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/40417297600)
a terminé avec succès le 26 octobre 2026 à 23:22:28 UTC. Elle a reproduit
les 473 tests Python et les 106 réponses, puis 144 parcours Chromium :
48 sur la génération normale, 48 avec ADI en quarantaine, 48 sur les pages
réellement servies après déploiement. Ces parcours publics incluent
`comptabilite.html`, ses 80 lignes et ses sources, ainsi que les questions
HPS/RDS/Wafa Assurance à trois largeurs. L’artefact préparé après sauvegarde
est identifié par le commit `84fbb4621e75179bc099a552febe8c15540d135a`.
Son export de couverture contient 80 titres, 11 revues primaires de méthodes,
66 déclarations à approfondir, 3 dossiers à compléter et aucun conflit.

Le contrôle public a été exécuté par Chromium dans le workflow. Aucun contrôle
manuel supplémentaire de l’interface publique, aucun appel commercial à un
modèle et aucune activation d’agent permanent ne sont prétendus réalisés.
Les instructions de reprise et les trois leçons relues sont enregistrées avec
ce lot ; les anciens incidents restent conservés.
