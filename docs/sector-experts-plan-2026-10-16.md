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

## Lot 2 — audit de fiabilité documentaire

- `nour/sector_audit.py` inventorie les 80 sociétés depuis le rapport calculé, avec métier, statut de rapprochement, pages sélectionnées et faits annuels manquants.
- `tools/audit_sector_readiness.py` permet le contrôle automatique de ce rapport sans réseau ni PDF téléchargé.
- `web/sector-readiness.json` est un export documentaire transparent ; `web/metiers.html` en est la vue lisible, accessible par le menu « Métiers ».
- Les banques et assureurs ne peuvent présenter des multiples industriels de dette nette : le contrôle bloque la publication si ces valeurs sont présentes.
- Une preuve « page sélectionnée contrôlée » doit porter date, unité, devise MAD, périmètre comptable, page, URL primaire HTTPS et empreinte SHA-256.
- Aucun KPI métier absent n'est imputé. Les profils spécialisés n'ajoutent aucun résultat financier non vérifié.
- Le moteur conserve les scores, les historiques et les chiffres financiers existants ; seules des métadonnées de provenance et de présentation sont ajoutées.

La revue CI doit encore valider le lot avant toute fusion. Une revue documentaire exhaustive et la qualification métier des sociétés non encore couvertes restent nécessaires.

## Lot 3 — couverture des métiers et garde-fous RNPG

- **78 sociétés sur 80** disposent d'une grille de lecture métier indicative ; **DIS et HAL** restent volontairement non qualifiées jusqu'à identification documentaire. Cette couverture mesure la présence d'une grille, **pas** la fiabilité de leurs résultats.
- Les métiers hospitaliers (AKD), pharmaceutiques (SOT, PPM) et distribution médicale (VCNE) sont séparés.
- Sont également distingués : banques, assurances, courtiers, leasing, crédit à la consommation, paiement, immobilier locatif et promotion, BTP, tourisme, agroalimentaire, agriculture, mines, métallurgie, ports, télécoms, automobile, IT, chimie, énergie, holdings et distribution.
- La file de rapprochement identifie désormais les **faits manquants** et les **faits présents mais non vérifiés**. Elle inclut la référence du rapport et, lorsqu'elle existe, la page PDF indicative du poste à contrôler.
- Le résultat net **consolidé total** de TGCC, SGTM et CMGP est exposé comme élément de vérification, **jamais** substitué au RNPG. BPA, PER et ROE restent indisponibles sans numérateur pertinent vérifié.
- Dossier de travail : [Rapprochement des résultats part du groupe](group-earnings-reconciliation-2026-10-16.md).
- Les PDF AMMC n'ont pas été vérifiés indépendamment lors de cette passe : aucune valeur n'est reclassée en « vérifiée » sur la seule foi de la référence existante.

### Conditions de clôture du lot

1. CI GitHub réussie sur **le dernier commit**, pas un commit antérieur.
2. Contrôle de la page métiers sur ordinateur et mobile et de la concordance avec l'export JSON.
3. Trois éditions locales 09:45, 12:45, 16:00, archivage et statut provisoire/confirmé contrôlés.
4. Revue primaire des anomalies bloquantes, sans déblocage arbitraire.
5. Décision explicite de fusion/publication ; le lot ne se déploie pas seul.
