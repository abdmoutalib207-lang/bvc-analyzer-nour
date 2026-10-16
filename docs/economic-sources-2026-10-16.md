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
