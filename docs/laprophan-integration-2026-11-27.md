# LAPROPHAN dans Nour — 27 novembre 2026

## Résultat du lot

LPH entre dans le référentiel Nour (81 sociétés suivies), la recherche, les
fiches, les exports et le contexte documentaire de l’assistant. Code de collecte
CDG LPH, ISIN MA0000012882, première séance le 25 novembre 2026. Famille
métier : industrie pharmaceutique, distincte des hôpitaux et des équipements.
Le sigle est affiché en attendant un logo confirmé.

La collecte habituelle enrichit LPH : les observations du jour restent
provisoires avant clôture et ne deviennent pas des bougies par anticipation.
Les seuils du score, des indicateurs et des statistiques restent inchangés.
Deux séances ne suffisent pas au RSI, aux moyennes ou au score ; état LIMITÉ.
Aucun BPA/PER/PB/ROE n’est déduit de l’IPO ou importé du score principal.

## Sources consultées

- Bourse de Casablanca, dossier de presse IPO, section II : première cotation,
  LPH / MA0000012882, prix public 341 MAD, 17 315 725 actions après IPO.
  https://www.casablanca-bourse.com/sites/default/files/communiques-officiels/2026/11/dp_ipo_laprophan.pdf
- Bulletins officiels des 25 et 26 novembre 2026, p.1 : identité et OHLC.
  https://www.casablanca-bourse.com/sites/default/files/bulletins/2026-11/fr/BCFR_20261125.pdf
  https://www.casablanca-bourse.com/sites/default/files/bulletins/2026-11/fr/BCFR_20261126.pdf
- Fiche AMMC LAPROPHAN pour la découverte documentaire. La date du visa
  28 octobre ne remplace pas la première cotation du 25 novembre.
  https://www.ammc.ma/fr/espace-emetteurs/liste-des-emetteurs/55953
- Principal consulté exclusivement en lecture seule, commit
  `6fc7a4472ff64d0b6db6e5d58c4b6ec44e18bd51` :
  `pipeline/candles/LPH.json`, SHA-256
  `f52b7f5b489219fa21efd18b9f9a8ee632bd8c3d01c100f6b29f9120e543442d` ;
  `data.json`, SHA-256
  `2d768ae4b4cf91f41bb60e941f40573fb0625dc611e5f901f775b8db76522e83`.
  Ces empreintes portent sur les fichiers effectivement téléchargés.

| Séance | Ouverture | Haut | Bas | Clôture | Titres |
| --- | ---: | ---: | ---: | ---: | ---: |
| 25/11/2026 | 305 | 333 | 300 | 300 | 358 274 |
| 26/11/2026 | 305 | 312,95 | 303 | 310 | 89 933 |

Montant réel du 26 novembre : 27 766 801,55 MAD repris de data.json daté.
Aucun montant monétaire inventé pour le 25 novembre ; ni bougie au prix public
341 MAD, ni séances antérieures ou interpolées. L’observation directe CDG du
27 novembre confirme le code LPH et reste séparée des deux clôtures.

Les PDF officiels ont été consultés via leur texte publié. Le téléchargement
binaire local a renvoyé HTTP 503 ; aucune empreinte PDF calculée ni vérification
visuelle des pages n’est prétendue. Le hash PDF reste nul. Les documents du
principal apportent une provenance de reprise, sans transférer une certification.
Les comptes annuels et S1 restent à relever sur le document de référence AMMC.
Le nombre d’actions après IPO ne remplace aucun dénominateur annuel.

## Contrôles et publication

- Avant/après : les 80 enregistrements de marché existants et les métadonnées
  racines du snapshot sont identiques ; seul LPH et sa présence sont ajoutés.
- Tests dédiés : identité et premières bougies, seuils sur deux séances,
  absence de ratios, égalité des calculs des 80 titres existants, collecte
  provisoire puis clôture sans mutation des entrées.
- Les contrats de complétude Python/JS et les parcours navigateur suivent
  désormais la taille du référentiel ; les seuils financiers restent inchangés.
- La preuve de volume de l’ancien snapshot ne peut pas être réétiquetée avec
  le nouveau hash : elle a correctement refusé la première construction locale.
  Une collecte réelle intraday et son état de contrôle provisoire permettent
  la reconstruction, sans prétendre à un rapprochement de clôture nouveau.
- Vérification complète et publication distante : à compléter après exécution.
- Navigateur local indisponible : binaire Playwright absent et lanceur Chromium
  système sans exécutable réel. Le workflow existant conserve ses contrôles
  Chromium avant et après publication ; aucun contrôle n’est désactivé.

Leçon durable : `ipo_identity_before_short_history` dans error_memory.json.

## Reprise dans cette conversation

La PR #45 existante est reprise sans recréer le lot. Le premier contrôle
Chromium (run 45981862243, job 140447497146) échouait sur une assertion
exigeant une image de logo pour toute fiche, alors que LPH est explicitement
non vérifiée dans le catalogue. Le contrôle vérifie maintenant soit une
image déclarée vérifiée, soit le sigle exact et l’état de repli visible.
Les autres vérifications de cours, sources, mise en page et calculs restent actives.

Une nouvelle collecte réelle intraday du 27 novembre et sa preuve provisoire
liée au snapshot de 81 titres sont conservées avec leurs heures. Aucune
ancienne preuve de clôture n’est réétiquetée avec le nouveau hash.

Preuve documentaire complémentaire effectivement téléchargée et pages
sélectionnées contrôlées visuellement : note d’opération du syndicat de placement,
https://www.sahambank.com/wp-content/uploads/2026/11/LAPROPHAN_IPO_NO_033_2026.pdf
SHA-256 `97649c97cccf87110f56306af9576d953f0b8b058624fde0f96c999c9fe51542`.
Page PDF 23 : ISIN et première cotation ; page 50 : capital après IPO.
Ces pages corroborent l’identité ; elles ne certifient aucun ratio annuel.

La tentative de vérification locale sur la reprise exploratoire a été
interrompue pour repartir de la PR existante. Ses résultats partiels ne sont
pas présentés comme une validation complète du lot final.

La suite locale finale a exécuté 556 tests Python avec succès. Le contrôle JS
a ensuite détecté un libellé de la bibliothèque comptable encore figé à
80 actions : ce texte décrit désormais le référentiel des actions suivies,
sans décompte figé. Le contrôle de sélection conserve son compteur dynamique.

Les derniers liens génériques de retour aux valeurs, de couverture et de
référentiels comptables ne portent plus le décompte historique de 80 titres.
Les nombres du rapport et les compteurs d’interface restent ceux de l’univers réel.
