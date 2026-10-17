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

## Mode IA facultatif : configuration publique et code de déploiement

La configuration publique pointe vers l'endpoint privé Cloudflare Workers AI /
Mistral Small 3.1. L'appel exige une activation volontaire et un code privé.
Le code reste par défaut en mémoire dans la page. L’option explicite « Garder
l’accès dans cet onglet » conserve un code validé dans `sessionStorage`, lié
à l’endpoint autorisé, pendant huit heures maximum sans prolongation à chaque
question. Il survit alors aux actualisations et changements de fiche dans le
même onglet. Le mode IA reste à activer volontairement après rechargement.
« Oublier le code », un refus d’accès ou l’expiration effacent la mémorisation.
Le bouton d’oubli annule aussi l’appel en cours pour qu’il ne restaure pas le code.
La fermeture normale de l’onglet termine ce stockage de session ; certains
navigateurs peuvent restaurer leur session, d’où l’expiration absolue et le
bouton d’oubli. Ce n’est pas un coffre chiffré : les scripts de la même origine
peuvent accéder au stockage. Aucun `localStorage` ni cookie n’est créé. Si le
stockage est bloqué, le fonctionnement en mémoire reste disponible et signalé.
Le mode local fonctionne sans ce code. Aucun secret n’entre dans les fichiers,
exports, journaux ou historique de conversation Nour.
Le badge distingue consultation locale et explication IA. La référence chiffrée
locale est affichée séparément de la prose générée.

Le module `nour/assistant_server.py` reste une passerelle locale optionnelle
limitée à `127.0.0.1` pour les essais serveur. Ses limites de huit appels par
minute et 100 par jour sont par processus ; elles ne sont pas des quotas
persistants de production. Variables : `NOUR_LLM_BASE_URL`, `NOUR_LLM_MODEL`,
`NOUR_LLM_API_KEY` (serveur uniquement), `NOUR_LLM_TOKEN_PARAMETER`.
Le frontend public privilégie l'endpoint Cloudflare explicitement autorisé.

Le lot de consolidation ajoute `knowledge/assistant_policy.json`, l'index
public dérivé `assistant-context.json` et une sélection compacte par question.
Il transmet les preuves, pages, périodes et réserves nécessaires, sans série
brute ni lignes du laboratoire. Les avertissements ne sont plus tronqués pour
faire tenir une réponse ; une demande excédant le budget est refusée clairement.
Un identifiant de snapshot empêche de mélanger une page ouverte et un backend
ayant reçu une publication plus récente. Les questions historiques ne
reçoivent pas les ratios actuels à la place d'une mesure non reconstruite.

`backend/worker.mjs` fournit maintenant un code de déploiement reproductible :
contrôles d'origine, secret vérifié par empreinte, lecture d'une URL Nour fixe,
quota transactionnel persistant global/par accès, désactivation administrateur,
rotation et erreurs minimales. Son fichier Wrangler est désactivé par défaut.
**Sa présence dans Git ne signifie pas que cette nouvelle version est déployée.**
L'endpoint déjà en ligne ne reçoit pas automatiquement les changements Python.

Voir [le lot de consolidation](consolidation-audit-2026-10-17.md) pour
l'activation distincte, les tests et leurs limites. Aucun code privé ne doit être
collé dans une conversation ou une PR. Les plafonds d'appels ne garantissent
pas un plafond de facture ; le budget fournisseur doit être contrôlé séparément.
Le prompt ne garantit pas l'exactitude : les faits Nour et leurs réserves priment,
et la qualité du modèle réel exige une évaluation dédiée après déploiement.

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
