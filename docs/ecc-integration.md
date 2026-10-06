# ECC dans Nour — 6 octobre 2026

Intégration locale au dépôt, issue de [ECC](https://github.com/affaan-m/ECC),
commit figé `ef648e01899ba3e8dc6371642deaaf64b4477775`, licence MIT conservée
dans `vendor/ecc/LICENSE`. Le moteur principal reste exclusivement consultable.

## Ce qui est réellement intégré

| Compétence | Usage dans Nour |
| --- | --- |
| verification-loop | Contrôle exécutable adapté : construction, Python, JS, audit des exports et diff |
| browser-qa | Revue des interactions, mobile, clavier et site réellement publié |
| make-interfaces-feel-better | Lisibilité, zones tactiles, état des contrôles et mouvement réduit |
| search-first | Recherche des solutions et sources avant ajout de dépendance |
| security-review | Entrées utilisateur, clés côté serveur, limites et erreurs explicites |
| content-hash-cache-pattern | Référence pour traitements coûteux de documents; aucun cache PDF nouveau prétendu actif |
| python-testing | Guide de tests; le projet conserve sa suite unittest et ses mocks |
| strategic-compact | Points de reprise documentés et séparation exploration/livraison |

Trois profils de revue : code-reviewer, python-reviewer, silent-failure-hunter.
Leur présence ne lance pas trois processus : ils sont disponibles dans Claude
Code. Codex utilise les compétences et les instructions partagées; ces profils
Claude ne deviennent pas automatiquement des rôles multi-agents Codex.

Les fichiers en amont sont archivés dans `vendor/ecc/`. Le manifeste conserve
commit et SHA-256 de chaque copie. Les liens `.agents/skills/ecc-*` et
`.claude/skills/ecc-*` pointent vers les mêmes fichiers, sans duplication.
`python tools/ecc.py install` restaure les liens locaux hors réseau, refuse
les écrasements et ne touche aucun répertoire global. `verify` ne modifie rien.

Les instructions `AGENTS.md`/`CLAUDE.md` et `.ecc/memory/project.md` expliquent
les invariants financiers, la séparation IA/calcul et les limites de la mémoire.
Les commandes npm/pytest génériques d'ECC sont des exemples; aucun outil non
installé n'est présenté comme exécuté. Ni hook global, ni MCP, ni API commerciale,
ni apprentissage sur les conversations privées n'est activé par cette intégration.

## Contrôles qui s'exécutent

```bash
python tools/ecc.py verify
python tools/verify_nour.py --build --asof 2026-10-06
```

Le workflow quotidien construit déjà les pages, puis lance `verify_nour.py`
avant de sauvegarder et publier. Il contrôle les fichiers ECC, la suite Python,
la syntaxe JS, les quatre scénarios de test JS (graphiques, radar, laboratoire,
assistant), les liens/exports de l'assistant et leur égalité exacte avec le rapport.
Le workflow installe Playwright 1.62.1 dans son répertoire temporaire et exécute
12 parcours réels Chromium (quatre pages à trois largeurs), avant déploiement
puis sur l'URL publiée. Les captures sont conservées en artefact pendant 14 jours.
Le navigateur n'appelle aucun fournisseur LLM. Ces parcours ne remplacent pas
une comparaison visuelle avec un référentiel approuvé ni un audit WCAG complet.

Les pourcentages de couverture, le typage statique, un audit WCAG complet et
la réponse d'un vrai fournisseur LLM ne sont pas mesurés par cette commande.
Un contrôle local ne prouve pas que GitHub Pages a publié : vérifier Actions
et le contenu réellement servi après le déploiement.

## Fenêtre d'assistance

Voir [architecture et activation](assistant.md). Le mode public utilise une
lecture déterministe des données, honnêtement étiquetée sans IA générative.
ECC est l'outillage de développement; le modèle conversationnel est un composant
séparé. Les frais d'une API éventuelle ne sont pas inclus dans ECC.

## Mises à jour

La version amont est figée. Une mise à jour demande une revue des fichiers,
une nouvelle provenance et les mêmes contrôles. Le manifeste ne se rafraîchit
jamais silencieusement. Ne pas installer les centaines de modules sans usage
identifié : OCR commercial, enrichissement Gemini, agents autonomes et services
de recherche restent des intégrations distinctes à examiner selon le besoin.
