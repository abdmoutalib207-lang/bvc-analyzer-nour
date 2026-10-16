# Nour — plan d'expertise sectorielle, expérimental

Branche : `nour-sector-experts-three-editions-oct16`. Moteur principal : lecture seule.
Pas de modification de `nour-quant-v1`, pas de publication, pas de dépendance installée.

## Méthode de travail

1. Identifier l'activité réellement exercée par la société et son périmètre consolidé.
2. Sélectionner des indicateurs propres au métier, sans supposer leur disponibilité.
3. Identifier l'émetteur, le document primaire, la page, la date, les unités, le périmètre et les réserves.
4. Réconcilier les comptes (RNPG, minoritaires, fonds propres, dettes, dénominateurs).
5. Vérifier les opérations sur titres, changements de capital et dates d'effet.
6. Calculer indépendamment puis comparer au résultat de Nour ; suspendre en cas de divergence.
7. Vérifier l'historique, les prix et la liquidité séparément des fondamentaux.
8. Présenter les faits, l'interprétation et les inconnues sans prévision inventée.

## Métiers

- Banques : PNB, coût du risque, solvabilité et créances en souffrance ; pas de dette nette/EBITDA industriel.
- Assurance : primes, sinistres, résultat technique et solvabilité ; courtage distinct.
- Promotion immobilière : préventes, livraisons, encaissements, marge, BFR et dette.
- BTP : commandes, marge des chantiers, BFR, capex et trésorerie.
- Tourisme/hôtellerie : occupation, ADR, RevPAR, saisonnalité et capex.
- Santé/pharmacie : mix produits, marges, stocks, capex, conformité si publiée.
- Agriculture/intrants : saisonnalité, stocks, créances, mix et marges.
- Ports/logistique : volumes EVP/tonnage, capacité, utilisation, investissements.
- Mines : production, teneurs, coûts unitaires, métaux, capex.
- Technologie/services : revenus récurrents uniquement si documentés, concentration clients et cash-flow.

La taxonomie est volontairement partielle : la société peut avoir plusieurs métiers.
`nour/sector_methods.py` est une **liste de contrôle**, non une source de chiffres,
ni un moteur de recommandations. Les symboles et classifications doivent être
confirmés contre le référentiel BVC avant intégration à des calculs. En particulier,
les activités diversifiées exigent une revue segment par segment.

## Organisation des revues

Profils de travail (fichiers `.claude/agents/nour-*.md`) :
- analyste comptable et rapprochement des sources ;
- spécialiste banque/assurance ;
- spécialiste activités opérationnelles (BTP, immobilier, tourisme, santé, agriculture, mines, ports) ;
- spécialiste quantitatif/risque/liquidité ;
- responsable QA, sécurité et publication.

Les profils sont des instructions de revue. Ils ne sont **pas** des agents
autonomes actifs ou des comptes externes. Aucun abonnement, clé, hook ou service
n'a été installé.

## Trois éditions Casablanca

- 09:45 : ouverture et contexte, prix intrajournaliers explicitement provisoires.
- 12:45 : état de mi-séance, comparaisons avec le point du matin.
- 16:00 : tentative de clôture, **non confirmée** si CDG ou la BVC n'ont pas
  encore fourni une séance complète et validée. Ne pas transformer un point
  provisoire en clôture.

Le workflow conserve la vérification avant publication. GitHub Actions peut
retarder ou manquer un cron. La vraie mise en service nécessite la revue,
les tests, la fusion et la vérification du site servi.

## Critères d'acceptation

- Trois crons, exactement, avec fuseau Casablanca ; archives des trois éditions.
- Aucune écriture dans le dépôt principal.
- Aucun ratio nouveau sans document primaire et contrôle indépendant.
- Absences, contradictions et changements de capital visibles.
- Aucun changement du score canonique.
- Tests unitaires, publication simulée et QA mobile avant fusion.
- Contrôle de la séance réellement servie après déploiement.
