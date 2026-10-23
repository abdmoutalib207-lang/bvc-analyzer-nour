# Rapprochement complémentaire — 23 octobre 2026

Travail exclusif dans Nour. Les PDF annuels des six dossiers ADI, MUT, CFGB,
CMGP, SGTM et ENK ont été téléchargés ; leurs pages sélectionnées ont été
rendues et lues. Les empreintes des cinq premiers sont identiques aux versions
antérieurement contrôlées. Une nouvelle consultation ne résout donc pas leurs
contradictions. Les pages et SHA-256 figurent dans
[`2026-10-23-followup.json`](../knowledge/financial_reviews/2026-10-23-followup.json).
La date de publication, distincte de la date de revue, reste non vérifiée.

| Titre | Constat chiffré | Décision |
|---|---|---|
| ADI | 2 114,079 − 752,590 = 1 361,489 MMAD, contre dette nette publiée 1 303 ; écart 58,489. Retirer 60,916 de crédit-bail ne ferme pas le pont. | Ratios de dette concernés suspendus. Les autres calculs restent disponibles. |
| MUT | 1 248,950 − 259,728 = 989,222 MMAD, contre dette nette **bancaire** publiée 828 ; écart 161,222 non expliqué par un pont documenté. | Dette suspendue ; cinq calculs indépendants ajoutés. |
| CFGB | RNPG 370,445 MMAD / 35 007 960 titres ≈ 10,581737 MAD ; BPA publié 10,89. Le total consolidé 381,362 ne remplace pas le RNPG. | BPA/PER suspendus ; coefficient d’exploitation calculé séparément. |
| CMGP | RNPG 244,010766 MMAD et BPA 14,35 au compte de résultat ; note BPA : 252,754943 MMAD et 14,87, même moyenne de 17 000 900 titres. | Contradiction interne maintenue, BPA/PER suspendus. |
| SGTM | RNPG 1 341,942 MMAD ; BPA publié 37 contre 22,3657 MAD par titre de clôture. | Dénominateur ajusté/moyen à rapprocher ; BPA/PER suspendus. |
| ENK | Annuel SCE tunisien en TND ; semestre 2026 IFRS distinct. Aucun taux de change documenté. | Six ratios sectoriels homogènes disponibles ; aucun BPA MAD, PER, P/B ou montant MAD déduit. |

## Douze nouveaux calculs réellement disponibles

| Titre | Formule | Valeur 2025 |
|---|---|---|
| CFGB | (513,422 charges générales + 100,560 amortissements/dépréciations corporelles et incorporelles) / 1 247,229 PNB × 100 | 49,2277 % |
| MUT | 181,834 résultat opérationnel / 2 021,823 CA × 100 | 8,9936 % |
| MUT | 126,161 RNPG / 2 021,823 CA × 100 | 6,2400 % |
| MUT | 315,384 EBE publié / 2 021,823 CA × 100 | 15,5990 % |
| MUT | 262,726 flux opérationnel / 2 021,823 CA × 100 | 12,9945 % |
| MUT | 2 021,823 CA / moyenne(3 702,790 ; 3 382,884 actifs) | 0,5707 × |
| ENK | 78,487051 résultat opérationnel / 717,159964 revenus × 100 | 10,9441 % |
| ENK | 59,657964 RNPG / 717,159964 revenus × 100 | 8,3186 % |
| ENK | 12,182432 CAPEX décaissé / 717,159964 revenus × 100 | 1,6987 % |
| ENK | 37,007597 flux opérationnel / 717,159964 revenus × 100 | 5,1603 % |
| ENK | 717,159964 revenus / moyenne(443,518793 ; 512,318302 actifs) | 1,5006 × |
| ENK | 580,013991 coût des ventes / moyenne(154,485171 ; 195,008393 stocks nets) | 3,3192 × |

Les montants de cette table sont en MMAD pour CFG/Mutandis et **MTND pour
Ennakl**, avant division. Les ratios homogènes n’exigent pas de taux de change ;
ils n’équivalent pas à des montants convertis en MAD. Les calculs monétaires
explicitement nommés en MMAD et les unités physiques restent indisponibles
pour des entrées TND sans conversion documentée. Aucune conversion implicite
n’est ajoutée aux fondamentaux historiques ni au score.

Le coefficient CFG inclut les amortissements et exclut le coût du risque. Ses
composantes publiées négatives sont conservées ; leur somme est contrôlée avant
le calcul. Le CAPEX Ennakl conserve le décaissement négatif d’origine ; les
cessions restent séparées. Le coût des ventes conserve son signe publié et sa
normalisation positive explicite. Les acquisitions **nettes** Mutandis ne sont
pas utilisées comme un CAPEX brut : l’indicateur correspondant reste absent.

## Preuves reproductibles et limites

- Import idempotent : `python tools/import_finance_followup_oct23.py --check`.
- Avec les six PDF téléchargés : ajouter `--pdf-directory CHEMIN` pour vérifier
  leurs empreintes, y compris les dossiers dont le blocage reste ouvert.
- `tests/test_finance_followup_oct23.py` vérifie les douze valeurs par fractions,
  les devises/unités/périodes incompatibles, les signes et les composantes, les
  restrictions maintenues et l’égalité de **toutes les sorties hors compartiment
  sectoriel pour les 80 titres**, avant/après ajout des faits.
- L’oracle sectoriel indépendant contrôle aussi les devises et la somme des
  composantes de charges. Les tests d’injection ADI, multi-titres et publication
  atomique restent requis par la validation complète.
- Le rapport [des 80 sociétés](mission-2026-10-23.md) est régénéré à partir des
  sorties contrôlées ; la couverture détaillée est publiée dans `couverture.json`.

Les onze titres partiellement bloqués le restent : aucun statut n’est amélioré
par apparence. Les pertes CAR/SNP/UNI et capitaux propres non positifs STK/STR
ne justifient pas un multiple positif fabriqué. La revue de pages sélectionnées
et la réussite des tests arithmétiques ne sont pas une certification des comptes.
Les références effectives de CI, de fusion et du site servi sont données dans
la PR et le compte rendu de livraison ; ce document ne les anticipe pas.
