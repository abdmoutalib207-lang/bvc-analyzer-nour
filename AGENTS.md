# Travail sur BVC Analyzer Nour

## Périmètre

Ce dépôt est `abdmoutalib207-lang/bvc-analyzer-nour`. Le dépôt principal
`abdmoutalib207-lang/-bvc-analyzer` est exclusivement consultable : aucune
écriture, branche, PR, secret ou configuration ne doit y être créé ou modifié.
Les instructions utilisateur et les règles de l'environnement priment sur ECC.
Ne lancer des sous-agents que si l'utilisateur demande explicitement une
délégation ou du travail parallèle. Les profils ECC ne constituent pas cette autorisation.

## Invariants

- Le moteur reste déterministe, sans NLP décisionnel. Une IA conversationnelle
  est une couche d'explication séparée, sans accès d'écriture aux scores ou aux ordres.
- Les fréquences historiques ne sont pas des probabilités de prochaine séance.
  Pas de prix synthétiques, interpolation de trous, sorties manquantes imputées,
  fondamentaux semestriels annualisés ou backtests avec données futures.
- Distinguer RNPG et résultat total, capitaux propres groupe et totaux, PNB et CA.
  Un dénominateur non vérifié laisse le ratio indisponible. Préserver les références S1.
- Les données absentes, anciennes, contradictoires et réserves restent visibles.
  Une référence AMMC n'est pas une certification de tous les ratios.
- Aucune clé API dans `web/`, les journaux ou le dépôt. Une configuration d'IA
  et l'envoi des questions à un fournisseur doivent être explicites.

## ECC disponible localement

Lire `docs/ecc-integration.md` et `.ecc/memory/project.md`. Les originaux figés,
leur licence et leurs empreintes sont dans `vendor/ecc/`. Les compétences sont
découvrables dans `.agents/skills/` (Codex) et `.claude/skills/` (Claude Code).
Les profils de revue Claude sont dans `.claude/agents/`; ce sont des profils,
pas des processus permanents. Aucun hook global, service payant ou MCP activé.

Appliquer les compétences selon le changement, sans copier leurs commandes
génériques npm/pytest lorsqu'elles ne correspondent pas à ce dépôt Python stdlib.
Ne pas installer leurs dépendances optionnelles ni lancer une commande de mise
à jour ECC automatiquement. Les exemples en amont restent des exemples.

## Vérification et livraison

`python tools/ecc.py verify` vérifie provenance, empreintes et liens locaux.
`python tools/verify_nour.py --build --asof YYYY-MM-DD` construit, teste les
contrats Python, les contrôles JS et audite les pages. Les étapes non effectuées
(typage, couverture, audit axe complet, vrai fournisseur LLM) sont dites non mesurées.
Après publication, vérifier le workflow et les pages réellement servies.
Ne jamais présenter un JSON construit avant déploiement comme preuve de publication.

Les exports `web/assistant-data.json` sont dérivés du rapport sans recalcul du
score. Le serveur optionnel utilise exclusivement ses propres données et un
modèle configuré par l'administrateur; le navigateur ne fournit aucun fait libre.
