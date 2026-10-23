# Équipe de contrôle Nour et surveillance persistante

Le travail est réparti entre collecte, contrôle des chiffres, vérification
indépendante et supervision de l'intégration. Pendant le développement, ces
missions peuvent être confiées à des agents distincts avec périmètres limités.
Leur activité conversationnelle ne constitue pas un service IA exécuté 24h/24.

La permanence opérationnelle repose sur les contrôles du dépôt :

| Mission | Exécution persistante | Preuve |
| --- | --- | --- |
| Collecte | Collecteurs CDG et Wafabourse, après clôture | Sources datées et empreintes |
| Contrôle financier | Sommes DH et titres, puis chaque ligne et prix | `data/market_integrity.json` |
| Vérification indépendante | Tests, audit final du rapport et navigateur | Workflow de revue puis publication |
| Supervision | État réel des collectes, refus de publier un bilan incohérent | Résumé GitHub Actions |
| Mémoire | Incidents et corrections conservés, leçons et tests | `data/error_memory.json`, `data/market_integrity_log.json` |

Le workflow quotidien contrôle les éditions de 09h45, 12h45 et 16h00 et ajoute
une vérification de clôture à 17h15, heure de Casablanca, les jours ouvrés.
Il ajoute un filet de sécurité à 19h00. Un réveil tardif est réaffecté au
dernier créneau dû du jour, sans recréer une édition de la veille.
Le watchdog dispose de réveils à :05, :25 et :55 de 09h à 19h et après
chaque publication ; il rattrape seulement le créneau courant.
Il actualise aussi la consultation chaque heure de 09h45 à 17h45, sans
remplacer les éditions archivées. L'heure réelle de collecte est affichée
séparément de la date de séance et de la construction des pages.
Les contrôles de clôture ne valident pas une observation intrajournalière.
Les horaires GitHub sont des déclenchements planifiés, pas une garantie
d'exécution à la seconde. Les agents n'ajoutent aucun abonnement LLM ni
accès d'écriture au moteur principal.

Une correction automatique ne porte que sur quantités et montants : les OHLC
doivent être identiques, la séance et les titres doivent correspondre, chaque
ligne doit concorder entre distributeurs, puis les agrégats doivent se retrouver.
Une divergence de prix ou une source incomplète interdit l'arbitrage automatique.
Si les listes détaillées de deux fournisseurs concordent exactement mais que
leur agrégat annoncé diverge, les lignes peuvent être publiées dans le périmètre
explicite `validated_title_lines`. Le rapport final doit vérifier à nouveau la
séance, les empreintes et chaque prix, montant et quantité. Le total annoncé
reste non confirmé, sans correction automatique ni ligne manquante inventée.
L'incident global reste ouvert et visible dans les pages et l'assistant.
Des fournisseurs différents peuvent partager un flux amont ; le contrôle ne
prétend pas certifier leur indépendance ni l'intégralité du marché hors périmètre.

Le journal d'incidents est sauvegardé même si la publication est refusée,
sans publier les données de marché refusées. Les incidents résolus ne sont pas
effacés ; une réapparition rouvre le dossier avec son compteur d'occurrences.
