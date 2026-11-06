# Compléter les chiffres annuels et réparer les fiches — 6 novembre 2026

## Résultat du lot

Reprise de la PR 41, branche `nour-reconcile-nov06`. Le moteur principal reste
strictement en lecture seule. Nour reçoit 28 interventions documentaires sur
14 sociétés : 13 ajouts issus de pages primaires relues, 10 réutilisations exactes
de CA déjà contrôlés dans les relevés métier, 5 précisions ou compléments de
provenance. Les 77 dossiers financiers et les 80 sociétés de marché sont
inventoriés dans `financial-coverage-2026-11-06.json`.

Les faits annuels contiennent désormais 28 CA contre 14 avant le lot, et 12 PNB
inchangés. Ces compteurs ne prouvent pas une couverture sectorielle complète :
les assurances, holdings et sociétés sans dossier ont des besoins distincts.
DIS, DLM et IBM n'ont toujours pas de dossier annuel renseigné dans Nour ; cela
ne signifie pas que ces sociétés n'ont rien publié.

`financial-completion-2026-11-06.json` conserve chaque valeur avant/après et les
sources de ce lot. Les semestres, cours et historiques ne sont pas modifiés.

## Pages contrôlées

Les pages indiquées sont des pages PDF ; la page imprimée est précisée lorsqu'elle
diffère. Les documents ont été téléchargés, identifiés, rendus et lus. Seules les
pages et lignes sélectionnées sont contrôlées, sans certification du rapport entier.

| Société | Pages PDF / imprimées | Décision |
| --- | --- | --- |
| ADH | 8, 9, 53, 54, 59, 74 / identiques | CA 2025 2 708,923803 MMAD ; comparatif 2 594,688796 ; RNPG exact 453,719263 ; capitaux groupe 9 481,694524 et 9 319,494058 |
| AKD | 50 / 98–99 ; 78 / 154–155 | CA 4 413,384274 et 2 954,038793 MMAD ; EBITDA publié 1 214 MMAD consultable, sans débloquer automatiquement le multiple de dette |
| DSW | 18–19 / identiques | CA 2 076,18375105 et 1 904,63654734 MMAD ; total des produits distinct |
| HPS | 47 / 92–93 ; 58 / 115 ; 61 / 120–121 | CA 1 476,348064 et 1 204,347601 MMAD ; RNPG 105,777740 au lieu de 106 arrondi ; pro forma distinct |
| CSR | 131 / 261 ; 149 / 297 ; 152 / 302 | CA 10 487,1 et 10 238,6 MMAD ; produits ordinaires 14 402,1 et 15 260,4 distincts |
| TQA | 114 / 226–227 ; 115 / 228 | CA 10 637,640 et 10 878,079 MMAD ; capitaux groupe 6 772,744 et 6 664,816 ; montant RNPG inchangé, provenance complétée |

Sources et SHA-256 :

- ADH : https://www.ammc.ma/sites/default/files/Addoha_RFA_2025.pdf — `0bec51e016409c0204221352b76c179087461a19e4ac7e1076622f0c130b6dbb`
- AKD : https://www.ammc.ma/sites/default/files/Akdital_RFA_2025.pdf — `82b9d050c7275c416b70116fc17d4d6e7187997b22e12029c83d639340d04d5f`
- DSW : https://www.ammc.ma/sites/default/files/Disway_RFA_2025.pdf — `feb9d97611e4f893e308a79bc9137a300a5900d97e7f63c8212862fc741960ce`
- HPS : https://www.ammc.ma/sites/default/files/HPS_RFA_2025.pdf — `d50b7fda92170c16ace9e1f649286333a0175f74c2051fc7856b179351b88ee2`
- CSR : https://www.ammc.ma/sites/default/files/Cosumar_RFA_2025.pdf — `7da285e005cb965a42fbb8302087b277787015172a33aa1b70d48d9f4d415d90`
- TQA : https://www.taqamorocco.ma/sites/default/files/2026-04/TAQAMorocco-RFA-2025.pdf — `999a778c755af856ded4c0544a9244413e8fc62a8e09441e3bffecbb32afb35b`

Le document TQA provient de l'émetteur après échec de l'accès AMMC. Ses faits
conservent leur URL et empreinte propres ; la référence globale AMMC du dossier
n'est pas réétiquetée. Les états TQA sont en KMAD, ceux d'ADH, AKD, DSW et HPS
en MAD, le tableau CSR en MMAD.

Les CA ARD, LES, MUT, SNP, CTM, GAZ, SRM et IMI sont transférés à l'identique
depuis leurs relevés métier contrôlés existants, tout comme AKD et DSW. Leur
ancienne date de revue est conservée. Il ne s'agit pas de nouvelles revues de PDF.
ENK reste en TND sans conversion ou insertion MMAD inventée.

## Réserves maintenues et corrections de lecture

ADH : le CA publié reste distinct de la simulation ancien mode 3 535 MMAD.
La comparabilité du CA 2024 après changement de comptabilisation n'est pas
établie par les pages revues ; seule la croissance reste suspendue, les deux
montants annuels sont consultables. L'EBITDA ne se déduit pas des provisions
nettes : la réserve existante reste active.

HPS : le CA du CPC n'est pas le total des produits d'exploitation. Le périmètre
CR2 et le comparatif publié sont mentionnés ; aucune croissance à périmètre
constant n'est affirmée. CSR : les autres produits d'activité ne remplacent
pas la ligne CA explicitement confirmée par la gestion.

TQA : le multiple publié 1,7x et celui proche de 2,0x calculé sur les postes
référencés restent non rapprochés ; seul ce multiple est suspendu. Les montants,
le calendrier propre des filiales et les autres calculs restent disponibles.
Les dettes sensibles ADI/MUT ne sont pas débloquées par ce lot.

## Réparations techniques et interface

- Le cours, la variation et l'heure de validation sont masqués lorsqu'une cotation
  est mise en quarantaine, même s'il reste un prix numérique dans une entrée.
- Fermeture du `details` de collecte réparée : auparavant 2 ouvertures pour une
  fermeture dans l'en-tête ; navigation désormais hors de la zone repliée.
- Alertes identiques regroupées à l'écran ; diagnostics structurés conservés.
- Carte CA annuel ajoutée lorsque sa preuve a une unité, devise, période et base
  compatibles. Elle reste visible quand seule la croissance est non comparable.
- Doubles relevés identiques entre faits annuels et métier regroupés en conservant
  leurs origines ; les observations discordantes restent séparées.
- Rejeu du lot métier du 23 octobre corrigé : conservation des nouveaux faits et
  des revues postérieures, refus explicite des conflits non datés ou de même date.

## Principal consulté sans modification

Lecture au commit `f6aaba35de051b65fcb41b98ea94f1c71a01bd8f`, fichier
`pipeline/faits_financiers.json`, blob Git `052e06ee816894caf069242838be263055914d08`.
L'empreinte Git de la copie locale correspond. Le rapport de rapprochement est
`principal-reconciliation-2026-11-06.json`, sans application automatique.
Un RFA identique n'établit pas à lui seul l'unité, le périmètre et la période de
tous ses tableaux. Les valeurs déjà plus précises dans Nour sont conservées.

## Vérification et reprise

Les tests financiers ciblés contrôlent les valeurs exactes, la séparation CA/
produits, les conversions, la conservation des semestres, le multiple TQA
indisponible et le CA ADH affichable malgré la croissance suspendue. Les tests
de présentation couvrent quarantaine, structure HTML et doublons. Les règles
réutilisables sont conservées dans le journal des leçons et la mémoire commune.

Les résultats de vérification complète et la publication réellement observée
seront consignés ci-dessous. Aucun contrôle local seul ne prouve le déploiement.

Contrôle local complet réussi : `python tools/verify_nour.py --build --asof
2026-11-06`, 503 tests Python, contrôles JavaScript et audits des exports.
La régression de l'import a aussi été relancée séparément : 9 tests réussis.
Les 77 références semestrielles ont été comparées avant/après et sont identiques.
Les dossiers ADI, ENK et RDS sont inchangés. Les contrôles conservent les
indicateurs de marché déjà mis en quarantaine ; ils ne les présentent pas comme
des calculs validés. Le navigateur local ne peut pas lancer Chromium dans cet
environnement ; les parcours Chromium du workflow distant restent à observer.

## Publication observée

La [revue de la PR 41](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/42227720398) a réussi sur le commit `1717a497cd37a4598716964f85f73746672b6d64` (arbre identique au lot testé localement). Fusion dans Nour : `7d22449f05abf2a06ccbc16ff1dff2d718c7ed18`.

La [publication 42229347268](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/42229347268) a terminé avec succès le 6 novembre 2026 à 15:15:11, heure de Casablanca (14:15:11 UTC). Collectes, vérification complète, parcours Chromium normaux et avec ADI en quarantaine, déploiement, parcours sur le site réellement servi et audit public du marché ont réussi.

La fiche ADH réellement servie a ensuite été ouverte dans le navigateur : CA annuel 2 708,92 MMAD, RNPG 453,72 MMAD, comparatifs CA/capitaux et liens PDF p.54/p.53 présents. Le cours reste indisponible et la croissance reste bloquée par sa réserve de méthode : aucune résolution de ces points n'est affirmée. La date de données affichée est le 6 novembre 2026. Le moteur principal n'a reçu aucune écriture.

La couverture demeure partielle. Le dossier d'inventaire conserve les manques et les réserves par société ; les trois dossiers annuels DIS/DLM/IBM restent à renseigner. Aucune certification globale ni validation prédictive n'est revendiquée.
