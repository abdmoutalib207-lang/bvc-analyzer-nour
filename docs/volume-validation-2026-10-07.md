# Publication et concordance des volumes - 7 octobre 2026

## Incident reproduit

Le run `37680246795` a reussi les collectes et les 132 tests Python, puis
echoue sur `tools/test_assistant.cjs` : la question « Quel volume global MASI ? »
exigeait inconditionnellement « totaux concordants ». Le rendu autorise pourtant
trois reponses honnetes : concordance, ecart, couverture non confirmee.
Les runs programmes suivants ne sauvegardaient ni ne deployaient leurs exports.

Un autre test temporel supposait que MRL avait toujours une cotation ancienne.
La collecte du 7 octobre fournit une nouvelle cotation MRL : cet etat ne doit
pas devenir un invariant du test de conversation.

## Correction ciblee

- Le test sur l'export reel verifie le statut effectivement produit et le montant.
- 17 scenarios stables, sans reseau : concordance, ecart, couverture incomplete,
  statut absent/inconnu, montant nul vs absent, volume d'une autre date,
  et MRL avec cotation fraiche ou ancienne. Les sources ne sont pas modifiees.
- Les 12 parcours Chromium verifient aussi la reponse sur le volume global,
  avant et apres publication, sans supposer la concordance de chaque seance.
- Une assertion en echec affiche maintenant la reponse effective.
- Le workflow conserve le journal de verification et les exports publics du
  candidat en cas d'echec, pendant 7 jours. Ces artefacts ne sont pas publies
  et ne constituent pas une preuve de deploiement. `pipefail` conserve l'echec.

Aucune modification du calcul financier, du score, des tolerances de
rapprochement, des references semestrielles ou du moteur principal.
Un ecart reste visible ; il n'est ni efface ni transforme en concordance.

## Controle du PDF fourni et de la collecte locale

Source : document utilisateur « Indices du mercredi 7 octobre 2026.pdf »,
CDG Capital Bourse, 4 pages, tableaux controles visuellement et extraction
recoupee avec les codes sources du depot. SHA-256 :
`7bcfedeaa0cf361cdaf06b84d79f3e66bf9298aa9352f6a267ccd93517494733`.
Le lien `blob:` appartient au navigateur utilisateur et n'est pas une URL
publique permanente.

Les 66 lignes avec quantites echangees positives ont ete comparees une par une
a la collecte locale du 7 octobre : cloture, quantite, montant et date.
Aucune difference sur les 66 lignes. Les lignes a zero ou date invalide du PDF
ne deviennent pas des cotations historiques.

| Mesure | PDF : somme des lignes echangees | Synthese MASI CDG collectee |
| --- | ---: | ---: |
| Montant MAD | 243 452 039,35 | 243 452 050,90 |
| Titres echanges | 572 237 | 572 240 |
| Lignes | 66 | 67 |

Difference de montant (lignes moins synthese) : -11,55 MAD. Le rapprochement
reste `incomplete` (66/67), pas `matched`, meme si l'ecart est tres petit.
La ligne supplementaire annoncee par la synthese n'est pas identifiee par
le PDF ou la reponse de cotations obtenue. Aucune ligne fictive n'est ajoutee.

ADI : 345,00 MAD, 20 957 titres, 7 225 467,80 MAD ; identique au PDF.
MASI (source distincte : API CDG, pas ce PDF de titres) : 16 990,7724 points,
variation +0,58 %, seance du 7 octobre.

## Verification avant livraison

`python tools/verify_nour.py --build --asof 2026-10-07` : 132 tests Python,
320 cas titre/theme, 29 questions precises, 17 cas adverses de volume/date,
419 reponses de domaines, 30 cas de conversation, audit de 89 pages et
411 controles arithmetiques sans echec. Original ECC et liens verifies.

La couverture de code en pourcentage, le typage, l'audit WCAG complet,
les performances de navigation et un fournisseur LLM reel ne sont pas mesures.

## Publication effectivement verifiee

Correctif : `d283e0ea51d4b1ba45e10638336cf86f6dd16a4d`.
Instantanes recollectes et sauvegardes par le bot :
`d3a65833d9d248ea9e32fb222a75a7ace11fe490`.
Run `37683651954`, job `113005788993` : conclusion `success`.
Les journaux confirment 132 tests Python, les 17 scenarios volume/date,
411 controles arithmetiques, 12 parcours Chromium avant deploiement et
12 parcours sur le site effectivement publie. Toutes les collectes reussissent.

Le site public a ete recharge et ses reponses testees directement :
cloture MASI du 7 octobre a 16 990,77 points, volume global, volume ADI
et PER MRL. MRL est date du 7 octobre sans avertissement de cotation ancienne.
`runtime.json` annonce `last_closed_session: 2026-10-07` et
`built_at: 2026-10-07T20:39:41.218203+00:00`.

### Le releve publie est distinct du PDF et du premier releve local

La nouvelle collecte CDG realisee par le workflow a 20:39 UTC ne donne pas
les memes volumes que le PDF fourni et le premier releve local ci-dessus.
Les dates et clotures des 66 lignes restent identiques ; 10 quantites et
montants different : ADH, ADI, AFI, CIH, HPS, MNG, MUT, RDS, SMI et STK.
Leur somme baisse de 512 titres et 224 124,50 MAD. Le motif de ces changements
dans les reponses CDG n'est pas etabli ; ne pas les attribuer a des annulations
de transactions sans preuve, ni presenter le PDF comme identique au site actuel.

| Mesure | Lignes du releve publie | Synthese CDG du releve publie |
| --- | ---: | ---: |
| Montant MAD | 243 227 914,85 | 243 227 926,40 |
| Titres echanges | 571 725 | 571 728 |
| Lignes | 66 | 67 |

L'ecart de -11,55 MAD, les 3 titres et la ligne non identifiee restent presents.
L'assistant public affiche le total de la synthese CDG avec
« couverture non confirmee · 66 / 67 lignes », sans fausse concordance.
ADI publie : 345,00 MAD, 20 952 titres, 7 223 742,80 MAD.
Les chiffres du PDF et du premier releve local ne sont pas forces dans
les donnees de production ; chaque comparaison est rattachee a son releve.
