# Registre des sources économiques marocaines — Nour

**Périmètre :** inventaire des institutions fourni par l'utilisateur et complété avec le HCP. Cette couche de contexte est **séparée** du moteur de calcul, des faits comptables et du score canonique.

## Livrables

- `data/economic_source_catalog.json` : 36 institutions, rôle, métiers concernés, usages, liens candidats et état de vérification.
- `nour/economic_sources.py` : validation stricte, interdiction de promotion des sources de contexte en preuves comptables, présentation HTML échappée.
- `sources.html` : annuaire dans le site statique Nour, avec état explicite de chaque adresse.
- `economic-sources-summary.json` : résumé reproductible, aucun import automatique.
- Tests unitaires, contrôle de concordance et QA navigateur.

## Politique de preuve

1. **Comptes d'un émetteur :** rapport financier primaire de l'émetteur ou dépôt AMMC, version, page, période, unité, périmètre, empreinte PDF et contrôle indépendant.
2. **Prix et opérations sur titres :** Bourse de Casablanca, Maroclear et avis émetteurs. Un ISIN ou une opération sur titres ne certifie pas le RNPG.
3. **Contexte sectoriel :** ACAPS pour assureurs et courtiers, BAM pour banques et crédit, Office des Changes pour commerce extérieur, HCP pour statistiques macro, ANP/Tanger Med pour les ports, ONDA pour les aéroports, etc.
4. **Contexte réglementaire et stratégique :** ministères, DEPP, TGR, Cour des comptes, Conseil de la concurrence, CESE, organismes d'investissement et EEP.
5. **Interdiction :** aucun chiffre macro/sectoriel, communiqué non rapproché ou lien candidat ne peut alimenter automatiquement un résultat net, une dette, un BPA, un PER, un ROE ou un score.

## Conditions avant une collecte automatique

- Confirmer l'URL exacte, la publication, les droits de réutilisation et les restrictions d'accès.
- Définir unité, fréquence, période, disponibilité point-in-time, périmètre géographique/sectoriel et changements méthodologiques.
- Tester les séries manquantes, révisions, doublons et retard de publication.
- Maintenir la distinction entre données publiques, indicateurs sectoriels et résultats d'émetteurs.
- Soumettre toute installation ou service payant à une autorisation préalable.

**État actuel :** inventaire de découverte uniquement. Aucun connecteur externe supplémentaire, aucune ingestion automatique et aucun déblocage de ratio.

## Collecte automatique — première étape sur sept organismes

- Configuration : `data/sector_source_watch.json` (BAM, ACAPS, HCP, Office des Changes, ANP, ONDA, Tanger Med).
- Collecteur : `nour/sector_sources.py`, commande `python tools/update_sector_sources.py`.
- Workflow : exécution à l'édition de **16 h, heure de Casablanca**, ainsi que lors des déclenchements manuels et des mises à jour de `main`, **uniquement après fusion et autorisation de publication**.
- Sorties : `data/sector_source_candidates.json` (pages et liens candidats, horodatages, empreinte de page), `data/sector_source_health.json` (succès/échecs), visibles dans `sources.html`.
- Sécurité : uniquement HTTPS et origines officielles explicitement autorisées ; limites de durée/taille, isolation des erreurs, dernière collecte réussie conservée en cas d'échec.
- **Limite volontaire :** la première étape détecte les publications et liens téléchargeables, mais ne lit pas automatiquement leurs chiffres, ne valide pas les PDF et n'alimente ni ratios ni scores. Les statistiques par société nécessitent un extracteur propre à la source, un contrat de données, un contrôle des unités/périodes et des tests indépendants.
- Aucun changement du dépôt principal ; aucune modification des résultats comptables existants.

La liste des liens ne prouve pas l'existence d'une API ni le droit de redistribution des documents. Les éventuels liens hébergés hors des origines officielles autorisées sont ignorés jusqu'à revue.
