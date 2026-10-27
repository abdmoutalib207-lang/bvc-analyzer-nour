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

Avant une correction de collecte ou de calcul, lire `data/error_memory.json`
et `docs/error-memory.md` lorsqu'ils existent. Conserver les incidents résolus,
la preuve avant/après et un test anti-récidive ; une panne de source ne résout
jamais un incident. Voir `docs/market-control-team.md` pour les rôles spécialisés
et leurs contrôles programmés. Les profils ne sont pas des processus IA permanents.

`python tools/ecc.py verify` vérifie provenance, empreintes et liens locaux.
`python tools/verify_nour.py --build --asof YYYY-MM-DD` construit, teste les
contrats Python, les contrôles JS et audite les pages. Les étapes non effectuées
(typage, couverture, audit axe complet, vrai fournisseur LLM) sont dites non mesurées.
Après publication, vérifier le workflow et les pages réellement servies.
Ne jamais présenter un JSON construit avant déploiement comme preuve de publication.

Les exports `web/assistant-data.json` sont dérivés du rapport sans recalcul du
score. Le serveur optionnel utilise exclusivement ses propres données et un
modèle configuré par l'administrateur; le navigateur ne fournit aucun fait libre.

## Méthodes partagées et apprentissage après chaque tâche

Lire `docs/agent-learning.md` et `docs/accounting-methods-2026-10-26.md` pour
les travaux financiers ou d'assistance. Le registre
`knowledge/accounting_methods.json` distingue règles générales et choix
documentés par société, période et périmètre. Ne pas déduire IFRS du secteur,
ni convertir des comptes en changeant seulement leur libellé.
Les lots suivants et leurs résultats sont indexés dans `.ecc/memory/project.md` ;
lire le dernier dossier de reprise applicable avant une nouvelle revue.

À la fin de chaque tâche, consigner la conclusion, les preuves, les contrôles
effectivement exécutés et les limites dans le document de reprise concerné.
Toute erreur réutilisable devient une leçon relue via
`nour.error_memory.record_lesson` et un contrôle anti-récidive quand pertinent.
Conserver les anciennes leçons et incidents ; mettre à jour la mémoire commune
dans le même lot Git. Une observation non vérifiée reste candidate.
Cette mémoire partagée est une procédure de travail, pas un réentraînement de
modèle ni la preuve qu'un agent permanent est installé ou actif.
