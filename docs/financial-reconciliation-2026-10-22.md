# Revue des résultats annuels — 22 octobre 2026

Nour uniquement. Le moteur principal reste strictement en lecture seule.
Cette revue complète le correctif statistique de la PR #24, fusionnée et publiée
par le [workflow 39871404100](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/39871404100).
Le manifeste public et `calculation-health.json` ont été lus après déploiement :
générateur `117d346f1c113575237136dc749396d330f2c433`, 80 titres,
4 184 assertions indépendantes, aucun écart détecté.

## Pièces et périmètre

Dix PDF annuels 2025 ont été téléchargés depuis les URL AMMC déjà référencées.
Les pages retenues ont été rendues et lues visuellement. Les 38 faits conservés
dans [`2026-10-22.json`](../knowledge/financial_reviews/2026-10-22.json)
portent URL, SHA-256 complet, page PDF/imprimée, unité originale, devise,
périmètre et date de clôture. Ce contrôle ne certifie pas les rapports complets.

| Titre | Résultat retenu, MMAD | Pages PDF retenues | Décision |
|---|---:|---|---|
| AKD | RNPG 443,680156 | 78 | Distinct du total 494,331591 ; minoritaires 50,651435 |
| ARD | RNPG 534,413 | 6 | Part des propriétaires explicitement publiée ; juste valeur toujours signalée |
| CTM | RNPG 56,204 | 65, 66 | Total 16,083 et minoritaires −40,121 distincts |
| DSW | RNPG 85,45793176 | 18, 19 | Ligne RNPG explicite, ici égale au total |
| GAZ | RNPG 750,500 | 172 | Ligne part groupe du communiqué annuel inclus au RFA |
| IMI | Part groupe 41,486 | 21, 79 | Attribution du résultat au groupe dans le tableau de variation ; minoritaires nuls |
| LES | RNPG 8 | 70, 81, 82 | Total 5, minoritaires −3 ; chiffres consolidés arrondis au million |
| SNP | RNPG −185,186 | 50, 51 | BPA négatif disponible ; PER positif indisponible |
| SRM | Social 12,06621642 | 18, 103, 104, 128 | Résultat reclassé sous la clé sociale ; capitaux propres et titres relevés |
| STR | Social 0,47601982 | 15, 17, 27 | Fonds propres négatifs et réserves du commissaire aux comptes conservés |

Le total consolidé ne devient jamais RNPG par hypothèse. SRM et Stroc étaient
rangés sous une clé consolidée malgré leur périmètre social. Ces anciens faits
sont archivés dans `reconciliation_prior_oct22`, puis retirés des faits actifs ;
les nouveaux champs sociaux sont explicites. Tous les semestres et les
67 autres dossiers annuels sont inchangés.

## Dénominateurs et limites

Les titres de clôture restent un dénominateur indicatif, pas une moyenne pondérée
inventée. CTM, Aradei, SRM et Immorente donnent des nombres explicites dans les
pages retenues. Pour les autres, le capital annuel exact est rapproché du nominal
officiel AMMC/Bourse, dont les URL sont conservées dans le relevé.

Lesieur : 276 315 100 MAD de capital exact (p.70), divisé par 10 MAD de nominal,
donne **27 631 510 titres**, recoupés sur la fiche officielle. L'ancien nombre
27 600 000 provenait du capital consolidé arrondi à 276 MMAD. Le résultat annuel
reste arrondi à 8 MMAD : un PER calculé à partir de ce bénéfice demeure indicatif
et sensible à l'arrondi. Aucun bénéfice précis supplémentaire n'est déduit du BPA
publié, lui-même arrondi à zéro dirham.

Immorente : le comparatif du bilan donne 827,116 MMAD de fonds propres groupe,
contre 827,083 à l'ouverture 2025 du tableau de variation. Aucun ROE moyen n'est
ajouté sans rapprochement. Les fonds propres de clôture restent 822,320 MMAD.

Stroc : les fonds propres sociaux restent **−340,89243583 MMAD**. P/B et ROE
sont indisponibles ; le bénéfice publié n'efface ni cette situation ni l'opinion
avec réserve et les limites de continuité décrites p.27. Les comptes ne sont pas
consolidés malgré les participations, comme le précise le commissaire aux comptes.

## Résultat sur le même instantané et la même date

Comparaison au 22/10/2026, sans remplacement des cours et sans rajeunissement
de leur date. Les ratios de valorisation restent suspendus si le cours est ancien.

| Indicateur disponible | Avant | Après |
|---|---:|---:|
| BPA | 50 | 60 |
| PER | 39 | 47 |
| P/B | 46 | 47 |
| ROE de clôture | 54 | 63 |
| ROE sur fonds propres moyens, complément séparé | 13 | 21 |

Les dossiers ayant au moins un indicateur bloqué passent de **19 à 11**.
Les huit dossiers débloqués passent en **revue requise**, pas en certification :
les autres faits importés n'ont pas tous une provenance primaire complète.
Répartition : 63 dossiers à revoir, 11 avec blocage, 6 sans réserve détectée par
le garde. Les nombres de références annuelles/semestrielles restent inchangés.

Blocages conservés : ADI/MUT (dette), CFGB/CMGP/SGTM (BPA/PER documentaire),
ENK (conversion monétaire), CAR/SNP/UNI (PER non pertinent en perte/nul),
STK/STR (fonds propres non positifs). Les 80 comparaisons et réserves sont dans
[`financial-reconciliation-2026-10-22.json`](financial-reconciliation-2026-10-22.json).

Aucune formule, pondération ou seuil de score n'est modifié. Certains scores
existants évoluent mécaniquement avec les résultats fondamentaux devenus
utilisables ; cela ne constitue ni une validation prédictive ni une recommandation.

## Reproduction

```sh
python -m tools.import_primary_oct22 --pdf-directory /chemin/vers/les/pdf
python -m tools.import_primary_oct22 --check
python tools/verify_nour.py --build --asof 2026-10-22
```

L'import refuse une URL ou une empreinte contradictoire, préserve un exercice
plus récent et est identique au deuxième passage. Les tests couvrent le RNPG
distinct du total, les reclassements sociaux, les arrondis de BPA/PER, les pertes,
les capitaux négatifs et la conservation des conflits documentaires précédents.
Les nouvelles pièces ne sont pas des comptes 2026 et aucun semestre n'est doublé.

Validation locale : **370 tests réussis**, procédure complète `Nour gate PASS`,
4 184 assertions techniques/liquidité/statistiques et 493 assertions financières
(559 en incluant 66 contrôles de cohérence des scores), sans écart détecté.
Les contrôles de prix, volumes, secteurs et exports restent actifs. Typage,
pourcentage de couverture, accessibilité complète et vrai fournisseur LLM non mesurés.
Les exports sont régénérés par le workflow ; une réussite locale ne prouve pas
la publication de ce second lot, à vérifier séparément après fusion.
