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

## Solution opérationnelle pour l'étude des sites

Le navigateur et REA s'exécutent ensemble dans GitHub Actions de Nour, via
`.github/workflows/nour_rea_browser.yml` et `.github/scripts/rea_browser_review.py`.
Le runner utilise son Google Chrome existant ; Chromium est la solution de repli si aucun navigateur compatible n'est présent.
Le workflow est manuel, sans programmation périodique ni modification des calculs ou de la publication de Nour.

Preuve initiale : [exécution 39093450970](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/39093450970), réussie.
REA 6.5.0 et Google Chrome 155.0.8059.39 ont produit une capture DOM, accessibilité,
URL et image pour la page Nour locale, https://www.idbourse.com/ et https://www.tradingview.com/.
Les trois observations ont le statut `captured` et aucune section demandée manquante ou tronquée.
Les images ont été extraites, leurs empreintes SHA-256 contrôlées et les deux pages externes inspectées visuellement.
Ce premier essai prouve le fonctionnement du navigateur et la lecture des pages d'accueil ; il ne constitue pas une analyse complète de leurs graphiques ou méthodes de calcul.

Pour relancer depuis GitHub : Actions → Nour REA browser investigation → Run workflow.
L'artefact `nour-rea-browser-evidence` contient les requêtes déclarées, les observations et `summary.json`, avec une conservation de sept jours.
Les cibles sont fixes ; aucun compte, cookie privé, code d'accès ou endpoint d'authentification n'est renseigné.
Une page refusée ou indisponible conserve un état distinct ; le succès de la capture locale ne signifie pas que tous les sites sont accessibles.
Les corps de requêtes et réponses et les valeurs d'en-têtes réseau ne sont pas collectés.

Le CLI et le raccordement locaux ci-dessus restent distincts de cette exécution distante : un outil MCP n'apparaît pas automatiquement dans la conversation Work Mode en cours.

## Cause du blocage dans l'environnement local

Aucun exécutable Chrome/Chromium n'a été trouvé sur PATH.
L'installation standard du Chromium Headless Shell de Playwright 1.58.2 a échoué :
archive téléchargée invalide, message `End of central directory record signature not found`.
Le diagnostic a établi que cette URL renvoyait HTTP 200 avec une page HTML de 195 octets `Site Unavailable`, au lieu du ZIP attendu.
L'installation locale de Chromium reste indisponible ; le workflow distant utilise son propre navigateur fonctionnel.
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

