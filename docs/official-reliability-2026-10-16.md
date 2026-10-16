# Résultats publiés : fiabilité et automatisation du 16 octobre 2026

Périmètre exclusif : `abdmoutalib207-lang/bvc-analyzer-nour`. Aucune écriture
dans le dépôt principal. Pas de prévisions importées, de LLM décisionnel, ni
de modification de la formule `nour-quant-v1`.

## Une chaîne de calcul contrôlée

`nour.fundamentals.calculate` est la frontière commune des calculs. Elle
applique maintenant `nour.financial_audit` : unités monétaires et actions,
valeurs finies, dénominateurs entiers positifs, dates explicites et périmètres
comptables compatibles. Un résultat total ne remplace pas le RNPG. Une erreur
explicite suspend les seuls ratios concernés. Une métadonnée héritée absente
reste une revue requise, sans fausse qualification « certifié ».

Le contrôle distingue l'exercice annuel et la publication semestrielle plus
récente. Aucun semestre n'est doublé ni mélangé au dénominateur annuel.
Une absence de rapprochement économique n'est pas corrigée par une convention
choisie silencieusement : les suspensions de dette existantes sont conservées.

Chaque construction exécute aussi le recalcul indépendant en Decimal de
`tools.audit_readiness.publication_health`. Une incohérence d'un ratio publié
ou du score interrompt la publication. Le relevé reproductible est exporté
dans `web/financial-health.json`, avec l'inventaire de disponibilité. Le contrôle
ne certifie ni les PDF entiers, ni la qualité économique des indicateurs.
Un résultat net négatif explique un PER indisponible : ce n'est pas en soi une
erreur de donnée. L'interface conserve une seule section repliée de contrôles.

## Sources officielles et documents candidats

`data/official_sources.json` identifie les 80 sociétés de l'univers, conserve
les références AMMC héritées et inscrit cinq espaces investisseurs : Alliances,
Marsa Maroc, Vicenne, Attijariwafa bank et TotalEnergies Marketing Maroc. Les
75 autres sites restent à enregistrer ; aucune couverture intégrale des sites
officiels n'est annoncée. Bourse et Maroclear ont des rôles distincts de
référentiel titres/opérations sur capital, non de fourniture du résultat net ;
leurs collecteurs ne sont pas prétendus actifs par ce lot.

`python tools/update_official_sources.py` actualise un index de candidats
séparé des faits. HTTPS, origines et redirections sont contrôlés ; tailles et
délais sont bornés. Une panne conserve les derniers candidats valides et
publie une erreur datée. Zéro lien PDF visible dans une page dynamique n'est
pas présenté comme zéro publication. Une indexation n'est pas une lecture
comptable ni une validation. L'index AMMC parcouru est sa première page,
pas un inventaire exhaustif de ses archives.

Option de téléchargement explicite :
`python tools/update_official_sources.py --fetch-documents --max-documents 10`.
Les PDF sont limités et conservés hors git dans un cache par SHA-256 ; des
miroirs ne sont regroupés que si les octets sont identiques. Une correction
au même URL doit conserver la trace de son changement de contenu. L'extraction
de nouveaux faits comptables reste soumise à une revue des pages et périmètres.

Le workflow existant déclenche cette découverte à sa collecte de 18h les jours
ouvrés, ainsi qu'en lancement manuel ou après modification du code. GitHub
peut retarder un cron. Les calculs et contrôles, eux, sont rejoués à chaque
construction. Aucun appel LLM, abonnement ou ordonnanceur externe ajouté.

## Compléments primaires

- RDS : RNPG 2025 4,494 MMAD et 26 208 850 actions ; voir le relevé de pages
  `batches/2026-10-16-RDS.md`. Ne pas substituer le résultat total de 4,491 MMAD.
- TMA : comptes consolidés 2025 de l'avis d'AGO, avec référence complémentaire
  S1 2026 et réserve sur les définitions de dette. Les références semestrielles
  existantes sont préservées. Les ratios non justifiés restent absents.

Les autres dossiers n'ont pas été complétés artificiellement : en particulier,
les écarts de dette ADI et les placements non rapprochés conservent leur statut.

## Vérification et reprise

`python tools/verify_nour.py --build --asof 2026-10-16`
rejoue construction, tests Python/JS, audit des pages et calculs indépendants.
La CI ajoute les parcours navigateur, puis contrôle le site réellement servi.
Le succès d'une construction locale n'est pas une preuve de déploiement.

Branche du lot : `nour-official-reliability-oct16`. Après fusion, la prochaine
collecte reconstruit les sorties depuis les faits du dépôt ; elle ne lit pas
les ratios du moteur principal pour les réinjecter dans Nour.
