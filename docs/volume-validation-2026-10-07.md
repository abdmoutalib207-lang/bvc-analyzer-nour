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
La publication et les parcours navigateur restent a confirmer dans le run
du commit correctif ; le document ne pretend pas qu'ils ont deja reussi.
