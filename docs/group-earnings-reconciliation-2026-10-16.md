# Dossiers RNPG — TGCC, SGTM et CMGP

Statut : **en attente de rapprochement documentaire indépendant**.
Les pages et chiffres ci-dessous proviennent de `data/facts_reference.json`, qui importe des relevés historiques du moteur principal. Ils ne sont **pas** une vérification indépendante du PDF et ne permettent pas de débloquer un ratio.

| Émetteur | Rapport primaire référencé | Page indicative | Chiffre relevé, résultat consolidé total | Question à résoudre |
|---|---|---:|---:|---|
| TGCC | https://www.ammc.ma/sites/default/files/TGCC_RFA_2025.pdf | 96 | 1 161,165 MDH | Retrouver le résultat attribuable aux actionnaires du groupe, et vérifier les intérêts minoritaires. |
| SGTM | https://www.ammc.ma/sites/default/files/SGTM_RFA_2025.pdf | 88 | 1 341,942 MDH | Vérifier le résultat part du groupe et les minoritaires. L'égalité apparente des capitaux propres du groupe avec l'ensemble consolidé **ne prouve pas** que les résultats nets soient identiques. |
| CMGP | https://www.ammc.ma/sites/default/files/CMGP_RFA_2025.pdf | 68 | 252,754943 MDH | Retrouver le RNPG dans les états IFRS, et distinguer « résultat net des entreprises intégrées » de « résultat attribuable aux propriétaires ». |

## Procédure de revue

1. Ouvrir le rapport officiel et identifier sa version exacte et sa date.
2. Lire le compte de résultat consolidé et l'état de variation des capitaux propres, puis la note sur les participations ne donnant pas le contrôle.
3. Relever **RNPG** (pas simplement le résultat total), la page imprimée et la page PDF, la période et la devise.
4. Vérifier l'unité (MAD, KMAD ou MMAD), le périmètre et les éventuelles opérations sur titres.
5. Enregistrer les métadonnées et l'empreinte SHA-256 du PDF contrôlé. Comparer indépendamment la valeur relevée au dossier.
6. Si RNPG = résultat total, conserver la **preuve explicite** des intérêts minoritaires nuls ; ne pas inférer l'égalité.
7. Calculer BPA, PER et ROE uniquement après la validation du numérateur **et** des dénominateurs correspondants.
8. Exécuter les tests et laisser les ratios indisponibles si la preuve est incomplète.

Le moteur conserve les valeurs consolidées totales comme **preuves à contrôler** sans les substituer au RNPG. La page `metiers.html` affiche la file de vérification et les pages indicatives.

**Blocage actuel :** les URL AMMC ont été référencées mais leur contenu n'a pas pu être vérifié indépendamment dans cette passe. Aucun chiffre nouveau ni déblocage n'a été introduit.

## Recoupement indépendant découvert le 16 octobre 2026

Les fiches **officielles de la Bourse de Casablanca** publient un « Résultat net (4) » dont la note (4) précise : **résultat net part du groupe pour les comptes consolidés**. Les communiqués émetteurs de TGCC et SGTM confirment la qualification « part du groupe ».

| Société | RNPG 2025 (MDH) — candidat officiel | Résultat net consolidé total relevé (MDH) | Différence total − RNPG (MDH) | Source indépendante |
|---|---:|---:|---:|---|
| TGCC | **952,053** | 1 161,165 | **209,112** | https://www.casablanca-bourse.com/fr/live-market/emetteurs/TGC ; https://www.ammc.ma/sites/default/files/CP_TGCC_2025.pdf |
| SGTM | **1 341,942** | 1 341,942 | **0,000** | https://www.casablanca-bourse.com/en/live-market/emetteurs/GTM ; https://www.sgtm.ma/wp-content/uploads/2026/03/CP-resultats-annuels-2025.pdf |
| CMGP | **244,010766** | 252,754943 | **8,744177** | https://www.casablanca-bourse.com/fr/live-market/emetteurs/CMG |

**Ce sont des rapprochements candidats, pas encore des valeurs injectées dans les ratios Nour.** Les pages HTML de la Bourse fournissent des chiffres officiels, mais il reste à confirmer leur emplacement exact dans les PDF annuels, les minoritaires, la date/version du document, le SHA-256 du fichier et les dénominateurs historiques. Le résultat net consolidé total ne remplace jamais le RNPG.

**Contrôle complémentaire du nombre d'actions :** Bourse de Casablanca indique **34 674 332** titres pour TGCC 2025 contre **34 674 300** déduits du capital dans le relevé Nour (écart 32 titres). Ne pas utiliser automatiquement l'un ou l'autre pour le BPA sans vérification de la moyenne pondérée et de l'augmentation de capital. SGTM : 60 000 000 titres à la clôture, avec augmentation de capital sur l'exercice ; CMGP : 17 000 900 titres. Les BPA et PER restent indisponibles dans Nour tant que les preuves exigées ne sont pas complètes.

**Réserve de fusion :** ce rapprochement réduit l'incertitude sur le RNPG mais ne constitue pas une certification des comptes. Il doit être repris dans les preuves primaires avant tout déblocage.
