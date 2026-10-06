# Assistant Nour : données et IA d'explication séparées

La fenêtre « Assistant Nour » est disponible sur le marché, les 80 fiches,
le laboratoire, le macro et les briefings. Un dialogue natif gère le focus,
le clavier et Échap; les commandes ont des zones tactiles de 44 px minimum.
Les échanges restent en mémoire dans la page, sans historique persistant.

## Mode public actuellement disponible

`assistant-data.json` copie un sous-ensemble du rapport calculé : dates, cours,
scores descriptifs, ratios, réserves, derniers semestres, statistiques et sources.
Son égalité avec le rapport est contrôlée avant publication. Le score et les
ratios ne sont jamais recalculés par l'assistant. Les données futures sont exclues.

`assistant.js` reconnaît explicitement des demandes de résumé, fondamentaux,
score, statistiques, macro et clôture MASI à une date (ISO ou jour/mois/année).
On peut choisir un titre et en mentionner deux pour lire leurs données.
Ce mode est étiqueté **lecture des données, sans IA générative** : c'est une
interface de consultation guidée, pas un LLM simulé. Il n'a aucun coût d'API.
Les demandes non reconnues sont limitées au contexte choisi; ce n'est pas une
conversation libre ni une analyse sémantique financière.

Les sources sont rendues avec textContent et des URL validées, sans HTML de
réponse injecté. Une donnée absente est dite indisponible. Aucune estimation
de probabilité de prochaine séance, recommandation d'ordre ou annualisation S1.

## Mode LLM optionnel : code préparé, activation distincte

`nour/assistant_server.py` fournit un raccordement à l'API Chat Completions
compatible OpenAI, notamment un serveur Ollama local. Aucun modèle n'est fourni
par ECC, téléchargé ou installé dans ce lot. Aucun vrai fournisseur n'a été
appelé pendant les tests. Le modèle et l'URL sont explicitement configurés.

Le serveur reste volontairement limité à `127.0.0.1`, avec contrôles Host et
Origin; il n'est pas un serveur de production public. Il refuse les demandes
sans consentement, les titres inconnus et les contextes trop volumineux.
Le modèle reçoit uniquement la question et les données sélectionnées relues
côté serveur, pas les faits ni l'URL fournisseur transmis par le navigateur.
Ni outils, ni accès GitHub, ni calcul modifiable, ni ordres ne lui sont accordés.

Pour le tester après avoir configuré un fournisseur dans votre environnement :

```bash
python run.py --asof 2026-10-06 --slot refresh
python tools/serve_assistant.py --port 8765
```

Ouvrir http://127.0.0.1:8765/, puis cocher l'envoi à l'IA dans la fenêtre.
La configuration publique demeure `endpoint: null`. Le serveur local fournit
une configuration différente seulement lorsqu'un fournisseur est configuré.

Variables serveur (aucune clé dans les pages ou dans le dépôt) :

| Variable | Usage |
| --- | --- |
| NOUR_LLM_BASE_URL | URL explicite se terminant par `/v1`; HTTPS, ou HTTP loopback pour Ollama |
| NOUR_LLM_MODEL | Identifiant du modèle installé/disponible chez le fournisseur |
| NOUR_LLM_API_KEY | Clé serveur requise pour un fournisseur distant |
| NOUR_LLM_TOKEN_PARAMETER | `max_completion_tokens` par défaut; `max_tokens` pour un fournisseur compatible l'exigeant |

Ollama documente `http://localhost:11434/v1` pour son interface compatible;
choisir un modèle réellement installé, pas un nom inventé par l'application.
Pour une API hébergée, les frais et limites dépendent du fournisseur; ECC ne
les supprime pas. Les abonnements de discussion ne sont pas des clés API.

Limites locales : 1 200 caractères par question, deux requêtes simultanées,
huit appels par minute et 100 par jour **par processus**; délai fournisseur
25 secondes, sortie 700 tokens maximum demandés. Ce ne sont pas un plafond
de facture garanti : redémarrer le processus remet ses compteurs à zéro.
Les erreurs ne dévoilent ni clé ni réponse brute et ne deviennent pas une
réponse IA inventée. Les redirections fournisseur sont refusées.

La réponse générée est affichée séparément de la référence chiffrée Nour.
Le prompt exige dates, réserves et absence de prévision; un prompt ne garantit
pas l'exactitude d'un LLM. Les chiffres du panneau de référence et les documents
d'origine priment. Le modèle n'a pas été validé financièrement dans ce lot.

## Activation sur le site public

GitHub Pages ne fait pas tourner ce serveur. Il faut un backend protégé
(authentification, contrôle des coûts persistant, limites, HTTPS et gestion
des clés) et une configuration frontend pointant vers ce backend. Aucune
installation d'hébergement supplémentaire ni API payante n'a été engagée ici.
Ce raccordement est prêt pour des essais locaux; l'IA générative publique
reste à activer une fois fournisseur et hébergement disponibles.

Références : [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages),
[clés et authentification OpenAI](https://developers.openai.com/api/reference/overview),
[Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create),
[compatibilité Ollama](https://docs.ollama.com/api/openai-compatibility).
# Réponses précises — lot du 06/10/2026

Le lecteur local répond désormais en priorité à la mesure demandée : PER, BPA,
P/B, ROE, dette nette, dette/EBITDA, PNB, RSI, MM20/50/200, MACD et son signal,
ATR (moyenne simple), support/résistance descriptifs, bêta, corrélation,
résultat annuel ou S1 et comparatif explicitement daté, capitaux propres,
nombre d'actions, volumes en MAD et en titres. Il compare jusqu'à deux titres,
lit jusqu'à six dates, et conserve le dernier titre dans le sélecteur pour une
question comme « Et son RSI ? ». Les clôtures des titres sont limitées aux
60 dernières observations de l'export; le graphique contient davantage.

Les valeurs sont copiées du rapport. Aucun score ni ratio n'est recalculé par
l'assistant. Un RN total ne remplace jamais un RNPG demandé. Une date invalide,
un exercice absent, un symbole inconnu ou une question non reconnue produit
une explication explicite. Le ROIC et le PER global du MASI sont absents.
Une demande à un seuil arbitraire ne crée pas de scénario conditionnel.
Les observations internationales ciblées conservent leur horodatage et état
d'archive. La dernière construction et le retard de collecte sont consultables.

Le mode reste déterministe, avec un vocabulaire et des formulations reconnus;
il ne comprend pas toute conversation libre. Les données chargées dans une
page restent celles de son ouverture : recharger pour recevoir une collecte
ultérieure. Le lot ajoute 29 cas de réponses précises aux 320 contrôles généraux,
et teste MM50 puis RSI en conservant le contexte dans Chromium aux trois largeurs.
