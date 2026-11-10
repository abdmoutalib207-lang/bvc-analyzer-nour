# Contre-vérification MS Screener — 9 novembre 2026

## Résultat de la revue

Le rapprochement secondaire devient un contrôle documentaire automatique de
Nour, distinct des données qui alimentent les ratios et scores. Aucun code du
screener n'est exécuté ou copié. Aucun chiffre canonique n'est remplacé sur la
seule foi d'une concordance externe. Le principal reste en lecture seule.

La collecte réelle du 9 novembre à 15:06 UTC a examiné 1 033 lignes :

| Catégorie | Lignes |
| --- | ---: |
| Concordance numérique exacte | 94 |
| Faible écart, précision à vérifier | 10 |
| Écart numérique à rapprocher | 1 |
| Bases ou définitions non comparables | 590 |
| Donnée absente ou invalide pour la comparaison | 338 |

La cible comprend 80 titres ; 77 dossiers financiers existent dans Nour,
78 sociétés dans la source et 76 sociétés ont des lignes comparées. Ces
compteurs ne mesurent ni le nombre de PDF relus ni une certification financière.
La source annonce une génération à 13:19 sans fuseau attesté : aucun UTC n'est
inventé. Les collectes ultérieures peuvent modifier ces chiffres. Le premier
passage à 14:48 UTC comportait 1 032 lignes, 98 concordances et deux écarts.
Le contrôle final des libellés d'activité, notamment le PNB bancaire, réserve
les comparaisons dont le libellé semestriel Nour n'est pas documenté. Cette
différence de comptage ne résulte pas d'une modification des montants.

## Constats financiers contrôlés

- ADH : le CA 2025 de 2 708,923803 MMAD et le RNPG de 453,719263 MMAD
  correspondent à la page 54 du rapport officiel déjà archivé. Pages 8 et 54
  rendues et relues visuellement le 9 novembre, empreinte inchangée ; les autres
  pages ne sont pas prétendues relues aujourd'hui. La croissance brute
  4,40265 % est arithmétiquement exacte. La page 8 décrit un changement de
  comptabilisation ; elle ne devient pas une croissance à méthodes constantes.
- ADI : le RNPG 407,601 MMAD et le CA 2 431,512 MMAD concordent avec la fiche
  officielle de la Bourse. Le multiple externe 2,9x utilise 1 785,905 MMAD de
  dette nette et 614,625 MMAD d'EBE. Il exclut 424,416 MMAD de placements de
  trésorerie, contrairement au calcul strict Nour de 1 361,489 MMAD. Le pont
  vers 1 303 MMAD publié reste ouvert ; la réserve n'est pas levée.
- RDS : RNPG 4,494 MMAD ; le PER de 1 032,26 à un cours de 177 MAD est
  arithmétiquement cohérent. La petite différence de dette de 0,002 MMAD vient
  du total publié dans la note versus la somme de ses composants. Ne pas
  substituer le résultat total au RNPG, ni le comparatif original au retraité.
- AKD S1 : les deux écarts relevés au premier passage concernent 225 versus 225,051903 MMAD
  de RNPG et 2 532 versus 2 532,218920 MMAD de CA. La copie à en-tête émetteur
  publiée par Medias24 a été rendue et relue ; le RNPG se retrouve aussi par
  252,460278 − 27,408375. Les URL AMMC/Bourse étant indisponibles pendant la
  revue, l'identité du fichier miroir avec le fichier officiel n'est pas
  certifiée. Les montants Nour sont arrondis, pas des erreurs établies. Les
  précisions restent candidates, sans modification automatique. Dans le
  contrôle final, seul le RNPG figure comme écart numérique comparable ;
  l'activité reste réservée tant que son libellé propre n'est pas documenté.

Les fiches Bourse ne suffisent pas à certifier les capitaux propres groupe,
compte tenu de leur libellé générique. Les 888 références du screener sont
des libellés de documents, sans URL ni empreinte du PDF exact. Les détails,
pages, sources, hashes et limites sont conservés dans
`screener-primary-review-2026-11-09.json`.

## Identité et dimensions

Le registre `data/source_codes.json` prime sur une égalité textuelle de ticker.
SNA Nour est Sonasid, code SID dans la source. Stokvis est STK dans Nour,
SNA dans la source. Un rapprochement direct aurait comparé deux sociétés
différentes. Les noms attendus sont contrôlés, sans invention d'ISIN ni
appariement flou. Les absences et changements d'identité restent explicites.

Les comparaisons séparent unité/devise, période annuelle/semestrielle,
périmètre social/consolidé, régime comptable et version publiée/retraitée.
Un régime national générique ne certifie pas une transition CNC/PCGI. Un
montant dérivé, EBE/EBITDA, trésorerie avec/sans placements, consensus, projection
ou cours mobile n'est pas transformé en fait publié comparable. La période
Nour doit être propre au fait ; le millésime du dossier ne suffit pas.
Un libellé PNB explicite reste PNB. Une activité semestrielle sans libellé
vérifiable n'est pas appelée chiffre d'affaires par défaut. Les montants
d'Ennakl en TND gardent leur devise et leurs unités à rapprocher, jamais MMAD.

## Automatisation et accès public

`tools/update_screener_reconciliation.py` est exécuté à l'édition de clôture
documentaire (16h), lors des publications sur push et des éditions manuelles
explicites, dans le workflow existant. Ce contrôle Python ne fait aucun appel
à un LLM. Une panne externe ne bloque pas les autres collecteurs et conserve
le dernier succès daté avec l'état du dernier essai. Elle ne résout aucun écart.

Le script télécharge uniquement l'URL HTTPS fixe du bundle, avec origine et
redirections autorisées, délai, taille, Base64 stricte et décompression bornée.
Le JSON rejette les nombres non finis, les clés dupliquées et les types de
périmètre invalides. Les méthodes d'extraction et codes mal formés ne peuvent
pas faire échouer la présentation. Les faits Nour
et la source ont des empreintes distinctes ; les références externes ne
peuvent pas étendre la liste des domaines de publications autorisés.

La page `contre-verification.html`, liée depuis Sources, présente toutes les
catégories, les motifs, les unités et les provenances par société. Les états
futurs sont masqués pour les anciennes dates d'analyse ; une comparaison
ancienne ou portant sur des faits Nour modifiés reste réservée. Les exports
`screener-reconciliation.json` et `screener-primary-review.json` permettent
la reproduction des contrôles. Les volumes et cours ne sont pas modifiés.

## Vérification et publication

Tests ciblés : extraction sans exécution, décompression excessive, JSON
invalide, unité, signe, période, versions, scopes, pertes, identité SNA/STK,
immuabilité des faits, conservation du dernier succès, états futurs et périmés,
liens et rendu HTML. Le parcours navigateur couvre aussi la nouvelle page
à trois largeurs, y compris le détail ADI et l'absence de débordement.

La validation complète et la publication réellement servie sont détaillées ci-dessous.

## Validation et publication observées — 10 novembre 2026

La PR 44 est fusionnée au commit de code
`f37387021f8f444b7d031465ce7c8f6098cd4adf`.
La [revue 42838808668](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/42838808668)
a réussi : 551 tests Python, gate complet, 51 parcours Chromium sur le site
temporaire avec ADI bloqué et 51 sur la construction normale. Le sélecteur du
volet ADI cible son résumé direct ; le test attend l'affichage du tableau et
vérifie son en-tête directement, sans dépendre du retour à la ligne du texte.

La [publication 42840724962](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/42840724962)
a terminé avec succès : nouvelle collecte, 551 tests Python, contrôles JS,
gate complet et 153 parcours navigateur (51 normaux, 51 en quarantaine,
51 sur le site effectivement déployé). Aucun appel à un LLM.

Le contrôle automatique réel du 10 novembre à 15:06:20 UTC (16:06 Casablanca)
est `collected`, avec les 1 033 lignes du tableau ci-dessus. La génération
indiquée par la source reste le 9 novembre à 13:19, sans fuseau attesté.
Une collecte récente n'est donc pas présentée comme une nouvelle publication
des états financiers.

Relecture HTTP indépendante après déploiement :
`contre-verification.html` répond, 76 groupes de sociétés correspondent au
relevé JSON, le lien depuis `sources.html` est présent, la revue documentaire
sélectionnée est affichée et le générateur dans `runtime.json` est bien
le commit fusionné indiqué ci-dessus. Aucune correction canonique automatique.
Le principal n'a reçu aucune écriture.

Les 590 lignes non comparables et 338 manquantes restent explicitement hors
concordance. Elles ne prouvent ni une erreur du screener ni une absence de
publication officielle. Les 888 documents ne sont pas déclarés relus ou certifiés.
