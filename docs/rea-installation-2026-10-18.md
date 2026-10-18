# REA pour le chantier Nour — 18 octobre 2026

## État vérifié

Installation officielle npm `rea-agents@6.5.0`, Node.js 24.19.0, séparée du moteur et de ses dépendances.
Le paquet téléchargé annonce l'intégrité npm :
`sha512-C6BG7LyrAdR74mSjertM6PrxJkcNZ2bfQNOJornPo9erDEp2tyPRVYPnV5Yodr+1RqewCQla68WulXlVnveD+A==`.

Dans l'environnement de développement de cette conversation :
- CLI : `/root/.local/share/bvc-nour/rea/node_modules/.bin/rea`.
- Raccordement Codex : `/root/.codex/config.toml` ; sauvegarde automatique `config.toml.rea.backup`.
- Instructions officielles : `/root/.agents/skills/reverse-engineer-anything`, version 42.
- `rea --version` : 6.5.0.
- `rea doctor --client codex --skill --json` : healthy=true dans ce périmètre.
- Un vrai lancement stdio MCP a répondu à initialize puis tools/list : 207 outils, dont inspect_web_page, capture_browser_scenario et analyze_javascript_application.
- Ce test de serveur séparé ne signifie pas que les outils sont automatiquement ajoutés aux outils de la conversation Work Mode déjà ouverte. Ils restent utilisables par CLI pour les fonctionnalités dont les prérequis sont disponibles.

Cette installation concerne l'environnement de travail, pas le PC Windows ni l'iPhone de Noure.
Cet environnement peut être réinitialisé ; les commandes ci-dessous permettent de réinstaller la version identifiée.
Aucun composant REA n'est ajouté aux pages publiques, aux collecteurs ou au backend IA de Nour.

## Limite observée pour les sites web

Aucun exécutable Chrome/Chromium n'a été trouvé sur PATH.
L'installation standard du Chromium Headless Shell de Playwright 1.58.2 a échoué :
archive téléchargée invalide, message `End of central directory record signature not found`.
Aucun navigateur local fonctionnel ni scénario interactif IDBourse/TradingView n'est donc annoncé validé.
Les outils de décompilation natifs optionnels n'ont pas été installés : ils ne sont pas nécessaires à l'étude de sites.

## Installation sur un ordinateur Windows avec Codex local

Prérequis officiels : Node.js 22.x >=22.19, 24.x >=24.11 ou 26+, avec npm.
Dans PowerShell :

```powershell
node --version
npm --version
npx --yes rea-agents@6.5.0 setup --client codex --dry-run --json
```

Lire les chemins et changements proposés, puis appliquer pour ce seul client :

```powershell
npx --yes rea-agents@6.5.0 setup --client codex --yes
npx --yes rea-agents@6.5.0 doctor --client codex --skill --json
```

Redémarrer le client Codex local concerné et vérifier qu'il annonce les outils REA.
L'installation dans PowerShell ne relie pas à elle seule l'application ChatGPT iPhone à un serveur MCP local.
Le navigateur Chrome du PC peut servir aux captures ; suivre le guide officiel et son endpoint CDP local.

## Périmètre d'étude pour Nour

Cibles demandées : IDBourse et TradingView.
Commencer par une fonctionnalité précise : fiche titre, recherche, choix de période, comparaison ou présentation des données absentes.
Conserver les observations, leurs limites et les différences avec Nour avant de proposer une modification.
Les calculs canoniques, sources et contrôles de Nour restent déterministes.
Le moteur principal BVC Analyzer reste strictement en lecture seule.

REA observe les éléments disponibles au navigateur ; il ne révèle pas automatiquement les calculs exécutés sur un serveur distant et ne certifie pas les chiffres d'une plateforme.

## Références officielles

- https://github.com/morluto/rea
- https://github.com/morluto/rea/blob/main/docs/installation.md
- https://github.com/morluto/rea/blob/main/docs/browser-observation.md
