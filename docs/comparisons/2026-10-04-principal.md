# Rapprochement Nour / moteur principal — 04/10/2026

Le dépôt principal a été consulté **en lecture seule**, au commit [5108beff13424b9bb8079dc86e0d59eaa6dcdb64](https://github.com/abdmoutalib207-lang/-bvc-analyzer/tree/5108beff13424b9bb8079dc86e0d59eaa6dcdb64). Aucun fichier, workflow ou paramètre du principal n’a été modifié. Les chiffres ci-dessous décrivent les entrées et calculs de ce commit ; ils ne constituent pas une vérification de ce que son interface publique affiche.

Sources consultées : `pipeline/resultats_semestriels.py`, `pipeline/ratios_financiers.py`, `pipeline/lecture_resultats.py`, `bpa.json`, `fondamentaux.json`, `datasets/resultats_s1_2026.json` et les relevés de fonds propres. Les valeurs sélectionnées sont conservées dans [le relevé JSON](2026-10-04-principal.json). Nour conserve ses propres calculs, sans dépendance à l’exécution du principal.

## Périodes et formules

- Annuel Nour : BPA indicatif = RNPG annuel 2025 / nombre de titres référencé, lorsque le dénominateur est vérifié ; une moyenne pondérée n’est revendiquée que si elle est explicitement sourcée. PER = cours / BPA, P/B = cours / (fonds propres groupe / titres). RN et fonds propres sociaux sont utilisés uniquement pour des comptes explicitement sociaux.
- Le principal calcule également le résultat glissant : **annuel 2025 + S1 2026 − S1 2025**. Son BPA glissant n’est donc pas comparable directement au BPA annuel Nour. Ce calcul exige des périodes, devises, périmètres et ajustements de capital compatibles ; doubler S1 ne serait pas équivalent.
- ROE annuel : RNPG 2025 / fonds propres groupe de clôture. Nour arrondit à deux décimales ; les ROE publiés du principal à une. Ce ROE ne remplace pas un ROE sur fonds propres moyens.
- Les anciens champs `per`, `forward_per`, `roic` et `wacc` de `fondamentaux.json` ne sont pas les recalculs `ratios_publies`. Ils ne sont pas importés comme valeurs vérifiées dans Nour.
- La détection automatique d’unités dans `lecture_resultats.py` utilise notamment des critères de plausibilité économique. Les ajouts Nour reposent sur les unités lues sur les tableaux primaires, avec page, SHA-256 et périmètre. Le PNB ne devient pas du CA.
- Dette nette : le principal inclut les titres de placement de l’actif circulant sauf restriction documentée, et publie aussi une variante stricte. Nour conserve explicitement la variante **dettes financières − trésorerie actif**, hors placements. Les montants ne sont donc comparables qu’à la variante stricte du principal. Pour ce lot financier, aucun ratio industriel dette nette / EBE n’est calculé par Nour.

## Résultats comparés à période annuelle identique

BPA en MAD ; ROE en %. « — » signifie indisponible, pas zéro.

| Titre | BPA annuel principal | BPA glissant principal | BPA annuel Nour | ROE annuel principal | ROE annuel Nour | Rapprochement |
|---|---:|---:|---:|---:|---:|---|
| MGL | 107,07 | 115,03 | 107,07 | 12,1 | 12,07 | BPA annuel identique ; ROE compatible après arrondi |
| MRL | 38,64 | 39,60 | 38,64 | 8,7 | 8,74 | Même constat ; dette subordonnée exclue des fonds propres |
| MDP | — | — | 1,40 | — | 16,32 | Ajout primaire Nour ; RN total du CPC, capital recoupé avec communiqué T4 |
| CASH | 9,87 | 10,83 | — | 30,7 | — | Nour bloque capital et fonds propres contradictoires |
| CIH | — | — | — | 11,1 | 11,15 | Nour retient les fonds propres corrigés 9 768,468 MMAD |
| CDM | 74,27 | 81,72 | — | 10,5 | 10,53 | Principal divise RN 2025 par titres après augmentation 2026 |
| ATW | 49,48 | 49,78 | 49,48 | 15,3 | 15,33 | BPA annuel identique ; base de clôture indicative, autocontrôle signalé |
| BCP | 22,15 | 23,64 | 22,15 | 12,2 | 12,18 | BPA annuel identique ; fonds propres stricts groupe hors FSG |
| BMC | 32,74 | 42,52 | 32,74 | 5,7 | 5,74 | BPA annuel identique ; arrondi du rapport à 33 MAD distinct |
| BOA | 17,31 | 18,36 | — | 12,0 | 11,99 | Capital modifié 2025 ; moyenne pondérée/ajustements non rapprochés |
| SAF | — | — | — | — | 11,16 | ROE historique avant fusion ; aucun ratio sur les nouvelles actions |

### Écarts matériels expliqués par les documents

**CIH** : formule principale `1089.362 / 9817.628 × 100`, soit fonds propres avant correction. Tableau annuel p.26 : `9 817 628 − 49 160 = 9 768 468 KMAD`, concordant avec les lignes groupe du bilan p.24. Nour retient cette valeur corrigée ; l’écart n’est donc pas seulement un arrondi. Le capital juillet 2026 de 38 641 338 titres est recoupé, mais les ratios par action restent bloqués faute de moyenne/ajustements validés.

**CDM** : `863.551e6 / 11626499 = 74,27 MAD` dans le principal, contre quotient historique `863.551e6 / 10881214 = 79,36 MAD`. Le communiqué du 28/07/2026 confirme 745 285 nouvelles actions et 11 626 499 titres après opération. Il ne transforme pas le nombre actuel en moyenne pondérée 2025. Nour conserve les deux comptes de titres comme preuves, sans afficher un BPA/PER/P/B comparable au cours actuel avant rapprochement.

**Cash Plus** : `242.296 / 790.351 × 100 = 30,66 %`, arrondi 30,7, dans le principal. Le bilan annuel p.65 donne par somme groupe 790,776 MMAD contre total groupe 790,351 p.68 : écart 0,425 MMAD non expliqué. Les nombres d’actions intermédiaires et le changement de nominal demandent aussi un rapprochement. Nour conserve le RNPG et les entrées d’audit, bloque les ratios concernés ; aucun total consolidé ne remplace silencieusement la part groupe.

**Sanlam** : le semestre primaire 2026, p.1, précise expressément que les indicateurs concernent Sanlam **avant fusion**. RNPG S1 -88,608 MMAD contre 1 177,155 en S1 2025, distinct du RNPG annuel 2025 de 676,523. La fusion approuvée le 02/07/2026 porte le capital à 5 341 874 titres, avec effet comptable annoncé rétroactif au 01/01/2026. Aucun mélange avec les comptes pré-fusion ou extrapolation dans Nour.

## Limites restantes

Les onze rapprochements ciblés ne constituent pas un audit de tous les ratios des 80 titres. Les 63 références initiales et les semestres antérieurs gardent leur provenance et leur statut d’import non indépendamment revérifié. Aucun NLP décisionnel, score du principal, objectif de cours ou estimation prospective ne pilote les statistiques historiques Nour.
