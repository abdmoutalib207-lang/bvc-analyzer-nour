# Assistant Nour : interrogation des données publiées

## Résultat

L'assistant combine plusieurs rubriques au lieu de s'arrêter au premier domaine
reconnu. Il expose les valeurs canoniques des bandes de Bollinger et de
l'histogramme MACD. Il filtre et classe les chiffres disponibles sur les 80
titres, sans recalculer les ratios ni changer le score.

Exemples utilisables dans la consultation locale et comme demandes IA :

- `Cours, PER, RSI et VaR ADI`
- `Synthèse complète ADI avec actualités et sources`
- `Bandes de Bollinger ADI`
- `Histogramme MACD ADI`
- `Les 5 PER les plus faibles en 2025`
- `Quelles valeurs ont un PER inférieur à 15 et un ROE supérieur à 10 % ?`
- `Les 5 PER les plus faibles du secteur Banque en 2025`
- `Valeurs avec dette nette suspendue`
- Après un classement : `Et avec un ROE supérieur à 10 % ?`

## Contrats

`knowledge/assistant_metrics.json` définit les champs, unités, noms et domaines
interrogeables. Il référence les sorties du moteur, sans formule financière.
`backend/query.cjs` et `nour/assistant_query.py` sélectionnent les mêmes champs.
Le générateur copie le module JS vers `web/assistant-query.js` pour le navigateur.
Le Worker importe cette même source, conservée sous `backend/` pour que les
modifications déclenchent aussi sa compilation Cloudflare. La suite compare ses
contextes avec ceux du serveur Python.

Les filtres numériques utilisent les opérateurs `<`, `<=`, `>`, `>=`, `=` ou
leurs formulations françaises, reliés par `et`. Les classements demandent une
direction explicite. Les listes affichent cinq résultats par défaut, jusqu'à
vingt sur demande, et conservent le nombre total de correspondances. Un secteur
doit correspondre au référentiel publié. Ce filtre reste distinct des groupes
de comparaison comptable stricts.

Une valeur absente n'est jamais un zéro. Les dates de cours et exercices restent
distincts. Le filtre annuel exclut les exercices absents ou différents. Les
motifs `blocked` sont séparés des statuts simplement `unavailable`. Les
opérateurs non reconnus, la logique `ou`, le semestre, le TTM, les exercices
multiples et les classements techniques historiques sont refusés explicitement.
Il ne s'agit pas d'un langage de requête général ni d'une comparaison sectorielle
certifiée. Les prix anciens, états historiques et conflits restent exposés.

Les réponses financières existantes gardent leurs contrôles spécialisés : dette
rapprochée, EBE distinct d'un EBITDA recalculé, RNPG distinct du total, social
distinct du consolidé, capital, semestre et comptes annuels non interchangeables.

## Contexte IA

Le navigateur transmet seulement la question, les symboles, le consentement et
l'identifiant du relevé. Le serveur reconstruit les sélections depuis son propre
index public Nour. Les faits libres envoyés par un client ne sont pas acceptés.

L'index expose aussi les motifs de disponibilité des ratios, la couverture,
l'audit du montant de séance, l'intraday, l'archive du score et les paragraphes
de briefing. Seule l'édition demandée et les commentaires des titres demandés
sont récupérés ; le sous-arbre fondamental du briefing n'est pas dupliqué.

Les listes conservent toutes les réserves annuelles et la dernière publication
des titres transmis, avec les preuves pertinentes et leurs pages PDF. Si leur
contexte dépasse 40 000 octets, le serveur retire des dossiers entiers de fin de
liste et annonce le nombre omis. Il ne raccourcit pas une réserve pour faire
tenir un titre. Un seul dossier encore trop volumineux reste un refus explicite.
La réponse locale garde sa liste demandée.

L'en-tête public `X-Nour-Assistant-Version: nour-data-queries-v2` permet de
constater le déploiement de cette architecture sans exposer de secret ni appeler
le modèle. Il ne démontre pas la qualité d'une inférence réelle.

Les dates de questions quantitatives, même accompagnées d'actualités, ne
permettent pas de réutiliser les ratios actuels comme données historiques.

## Validation et limites

La suite ajoute des comparaisons directes avec les valeurs canoniques, les
critères, les exercices et les secteurs ; elle contrôle l'immuabilité, les
blocages, les preuves, le budget et la parité Python/Worker. Les parcours
navigateur testent aussi les classements, réponses combinées et bandes sur trois
largeurs. Les tests du fournisseur restent simulés : ils ne mesurent pas la
qualité d'une véritable inférence Mistral en production.

Cette évolution élargit les questions utiles à partir des données disponibles.
Elle ne promet pas toutes les formulations ou toutes les connaissances de la
Bourse. Aucun article intégral absent, indicateur non calculé ou chiffre non
publié n'est inventé. Le laboratoire local garde ses fonctions de calcul et ses
filtres ; les séries brutes ne sont pas transmises au modèle. Les quotas, secrets,
origines autorisées et le bouton de désactivation Cloudflare restent contrôlés
par la configuration existante.
