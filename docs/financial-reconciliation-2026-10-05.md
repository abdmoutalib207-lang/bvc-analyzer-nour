# Rapprochements ciblés du 5 octobre 2026

Périmètre : Nour uniquement. Le dépôt moteur principal est resté en lecture seule.
Les montants semestriels existants sont conservés ; aucune annualisation ni prédiction.
Le contrôle porte sur les pages sélectionnées, pas sur une certification globale.

| Titre | Conclusion retenue | Limites |
|---|---|---|
| CASH | Fonds propres groupe 790,776 MMAD, bilan p.65 = total p.68 moins minoritaires ; 24 553 090 titres recoupés par capital, note BPA et prospectus IPO p.39 | Sous-total 790,351 conservé pour audit ; lignes intermédiaires erronées non utilisées ; BPA indicatif de clôture, non moyenne pondérée IAS 33 |
| EQD | 1 485,722 MMAD groupe, tableau p.63 ; total moins minoritaires du bilan p.58 recoupe à 1 KMAD près | Le bilan répète les réserves totales en part groupe malgré 18 KMAD minoritaires ; réserve d’arrondi maintenue |
| HAL | RNPG comptable 99,83237679 MMAD confirmé ; EBE 525,676, dette nette 3 106,608 MMAD ; ratio 5,91 | Dette et EBE au KMAD arrondi. Personnel non financier exclu. BPA historique 2025, PER/P/B actuels bloqués après augmentation 2026 |
| CDM | BPA historique 2025 79,36, conforme au CPC et au quotient du RNPG par 10 881 214 titres | Résumé 79,44 non retenu ; 11 626 499 titres après juillet 2026 ne sont pas mélangés aux comptes 2025 ; PER/P/B actuels bloqués |
| MGL | Fonds propres sociaux 1 228,220 MMAD confirmés au bilan et à la variation | Graphique 1 155 non utilisé ; données déjà correctes, périmètre social préservé |
| M2M | 8,780283 MMAD S1 2026 est le total consolidé, pas un RNPG ; interprétation de contradiction retirée | RNPG non isolé, rapport complet requis. Pas d’inférence exacte depuis BPA arrondi. Dette nette stricte annuelle suspendue car placements inclus dans trésorerie importée |

## Preuves et reproductibilité

Les URL, pages, empreintes SHA-256 et opérations de rapprochement sont dans
`data/facts_reference.json` et `tools/reconcile_financial_oct05.py`.
L’ancien relevé HAL est conservé dans `reconciliation_prior_annual`.
Le script est ciblé, idempotent et refuse un exercice/source inattendu.

Eqdom et le prospectus Cash Plus ont été rendus par le workflow **en lecture seule**
du [contrôle primaire](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/37339088766).
Le workflow n’écrit ni les données financières ni le site.
Les pages de ces PDF ont ensuite été effectivement inspectées visuellement.

Le rapport complet M2M S1 2026 n’a pas pu être contrôlé : l’accès public de
l’émetteur présente une vérification anti-bot, non contournée. Ce manque est
visible dans la fiche ; aucune clôture fictive du problème documentaire.

Le contrôle de publication a également révélé un test de clôture dépendant de
l’ancienneté du snapshot réel. Le test simule désormais explicitement une clôture
absente, puis une clôture présente ; les règles de publication ne sont pas modifiées.
