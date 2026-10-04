# Lot annuel MGL, MRL, MDP, CASH

Pages sélectionnées des PDF primaires AMMC téléchargées et contrôlées visuellement le 04/10/2026. Les numéros ci-dessous sont les pages PDF (base 1), non une certification de tout le rapport. Les valeurs monétaires sont normalisées en MMAD à partir de l'unité réellement imprimée. Les semestres existants sont conservés ; aucune annualisation ni utilisation prédictive.

| Symbole | Comptes | Résultat retenu MMAD | Fonds propres utilisables MMAD | Actions utilisables | Activité |
|---|---|---:|---:|---:|---|
| MGL | Sociaux, établissements de crédit | 148,199 | 1 228,220 | 1 384 182 | Produit net 438,374 ; précédent 377,618 |
| MRL | Sociaux, établissements de crédit | 107,295 | 1 227,913 | 2 776 768 | PNB 387,199 ; précédent 379,187 |
| MDP | Sociaux, CGNC | 6,71310550 | 41,14596811 | 4 783 823 | CA 88,40888533 ; précédent 105,56386554 |
| CASH | Consolidés IFRS, part groupe | 242,296 | Indisponibles | Ratios bloqués | PNB 863,267 ; précédent 759,840 |

## Sources et contrôles

- MGL : [RFA](https://www.ammc.ma/sites/default/files/Maghrebail_RFA_2025.pdf), 78 pages, SHA-256 `b42dcbe782557763fa221dc7e0a1d8b27d89389694609a8d384e04bfb56f5d5b`. Bilan p.44, CPC p.46, fonds propres p.57, actions et nominal p.67. Le graphique p.6 affiche 1 155 MMAD ; le bilan et le tableau détaillé concordent à 1 228,220 MMAD. Écart consigné. Provisions et dettes exclues des fonds propres. Pas de dividende 2025 déduit du bénéfice 2024 distribué durant 2025.
- MRL : [RFA](https://www.ammc.ma/sites/default/files/MLE_RFA_2025.pdf), 59 pages, SHA-256 `c2e2497885b96a859ccbcdd7a01dc61be13d0bf7017403f6ff79517dfad09aa5`. Capital exact p.4 (277 676 800 MAD), passif p.38, CPC p.40, tableau des fonds propres p.55. Unité KMAD confirmée au résumé p.14. Dette subordonnée 120,109 MMAD exclue. Nombre d'actions = capital exact / [nominal AMMC 100 MAD](https://www.ammc.ma/fr/instruments-financiers/actions/action-maroc-leasing-sa), recoupé avec la [fiche émetteur BVC](https://www.casablanca-bourse.com/en/live-market/emetteurs/MLE270297). Le PNB 2024 du résumé p.14 (379,186) diffère du CPC (379,187) de 1 KMAD : CPC retenu.
- MDP : [RFA](https://www.ammc.ma/sites/default/files/Med_Paper_RFA_2025.pdf), 84 pages, SHA-256 `1c38089c7767c9d8d14d2f040bf10b7abd5ba07a97b431ff1e10c044e560e6b7`. Bilan p.38, CA p.39, résultat annuel total p.40, capital ETIC p.80. Unité MAD, conversion par 1 000 000. Le résultat net total inclut -2,95376174 MMAD relatifs aux exercices précédents : ne pas retenir 9,66686724 MMAD. Perte d'exploitation -10,35552586 MMAD compensée notamment par résultat non courant +22,12620377 MMAD. Le total de titres p.80 est incomplet (4 714 199), incompatible avec le capital exact et nominal 10 MAD. Le [communiqué T4 2025](https://www.ammc.ma/sites/default/files/CP_Med_Paper_T4_2025.pdf), p.1 contrôlée, confirme 4 783 823 actions et 47 838 230 MAD ; SHA-256 `9df850466cc4cf09a561028309ddf3226c8eeb0b3beaa35f6a7ab043c0235f44`. Ce dernier dénominateur est utilisé et l'anomalie ETIC reste visible.
- CASH : [RFA](https://www.ammc.ma/sites/default/files/Cash_Plus_RFA_2025.pdf), 108 pages, SHA-256 `e4a200dc1e2048a14280f411adeff0163090e697d7f743562e50a397ead4f090`. Bilan p.65 (imprimées 128-129), résultat p.66 (130-131), variation fonds propres p.68 (134-135), capital p.76 (150-151), BPA p.78 (154-155). Unité KMAD. RN groupe 242,296 distinct du total 241,283 avec minoritaires négatifs. Fonds propres groupe publiés 790,351 MMAD contre somme du bilan 790,776 MMAD ; pas de substitution du total consolidé 781,393. P/B et ROE indisponibles. Les 24 553 090 actions de clôture et nominal 10 MAD sont publiés ; les lignes d'augmentation/subdivision et le dénominateur moyen restent à rapprocher. Le BPA publié 9,87 n'est pas une preuve de moyenne pondérée. BPA/PER non calculés dans ce lot.

## Reproduction et limites

`python tools/import_annual_oct04_complement.py` puis `python run.py --asof 2026-10-04` et `python -m unittest discover -s tests -v`.

L'import conserve toutes les valeurs semestrielles et leur origine, et reste identique à son second passage. Les 76 autres dossiers ne sont pas remplacés. Les ratios par action MGL/MRL/MDP utilisent des titres de clôture documentés et sont indicatifs, pas des BPA moyens audités. Le ROE emploie les fonds propres de clôture, pas moyens. Les ratios sensibles CASH restent bloqués et les entrées non rapprochées visibles dans les preuves. Ce lot porte les références annuelles à 70/80 ; les semestrielles restent à 68/80. Les compteurs de BPA, P/B et ROE restent distincts.
