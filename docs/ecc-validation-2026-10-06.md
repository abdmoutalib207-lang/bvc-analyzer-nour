# Livraison ECC et assistant — 6 octobre 2026

Code d'intégration : `794d8a2057038e0032b54dc86486f902767c9adc`.
Correctif de présentation et conservation de toutes les réserves :
`2970c0be2deb41a2586752e8428e67bdd322fdd0`.

Publication finale contrôlée : [Actions 37411787290](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/37411787290),
job `112101604643`, conclusion **success**.

## Preuves

- Huit compétences ECC et trois profils de revue, provenance et liens locaux vérifiés.
- 121 tests Python réussis sur GitHub, dont les garde-fous du serveur optionnel.
- 320 scénarios titre/thème de l'assistant; formules, filtres du laboratoire,
  2 400 scénarios de graphique et filtres d'actualités toujours réussis.
- Audit des 89 pages, 80 titres et 917 séances MASI. Les données de l'assistant
  sont exactement dérivées du rapport, sans recalcul de ratios ou de score.
- Chromium : quatre pages (marché, JET, laboratoire, macro) à 375, 768 et
  1 440 px, soit 12 parcours sur la construction puis 12 sur le site publié.
  Dates, PER et source JET, réserves du S1, effacement, échappement du texte,
  dimensions du dialogue, retour de focus et Échap vérifiés sans appel LLM.
- Vérification visuelle supplémentaire du site public : bouton accessible,
  réponse JET sourcée et interrogation du MASI au 31/03/2026 (17 160,54 points).

Les entrées financières, les cours historiques, l'historique MASI et le code
de calcul restent identiques à la version précédant ECC (`ca350006...`).
Les rafraîchissements des collecteurs conservent leurs propres horodatages.
Le dépôt principal n'a reçu aucune écriture.

![Fenêtre réellement publiée](assistant-published-preview.jpg)

## Limites explicites

La fenêtre publique est une lecture déterministe des données, étiquetée sans
IA générative. Le raccordement Chat Completions compatible OpenAI/Ollama est
préparé pour des essais locaux, testé avec doublures : aucun vrai fournisseur,
modèle téléchargé ou compte API n'a été utilisé. Pour une IA publique, il reste
à configurer un fournisseur et un backend protégé; GitHub Pages est statique.

Les compétences et profils sont des ressources disponibles au développement,
pas des agents permanents. Le contrôle CI s'exécute réellement. Aucun hook global,
MCP externe, OCR commercial ou enrichissement décisionnel Gemini n'est activé.
La couverture de code en pourcentage, le typage statique, une comparaison visuelle
avec référence approuvée, un audit WCAG complet et l'exactitude financière d'un
LLM réel ne sont pas mesurés dans ce lot. Aucune performance prédictive revendiquée.
