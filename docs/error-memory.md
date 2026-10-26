# Mémoire durable des incidents de collecte

`data/error_memory.json` est un journal structuré, version 1, conservé dans le
dépôt Nour à chaque collecte. Il complète les diagnostics du dernier run ; il
ne remplace ni les observations sources ni les tests.

`update_error_memory(memory, audit, now=None)` retourne une nouvelle mémoire
sans modifier ses entrées. Chaque incident est identifié par séance, code,
symbole et champs contrôlés. Les répétitions incrémentent un compteur ; elles
ne créent pas une copie du même incident. Première et dernière observations,
valeurs avant/après, preuves et nombre de réouvertures restent enregistrés.
Un incident résolu reste présent. Une récidive rouvre son état en conservant
sa dernière résolution documentée.

Une panne, une source absente ou un simple statut « matched » ne résolvent
rien. La résolution exige une séance identique, un rapprochement interne et
multisource positif du garde-volume, des liens publics de preuve et une portée
de symboles/champs explicitement validée. Un incident sans séance connue ne
peut pas être résolu par une séance ultérieure. Les quantités sans seconde
source indépendante restent décrites comme contrôlées par CDG et son agrégat.

`record_lesson(memory, lesson, now=None)` conserve séparément les règles
durables rédigées après revue. Son entrée comporte `id`, `title`, `rule` et
`evidence`. Les titres et règles sont des textes relus, jamais des exceptions
réseau brutes. Aucun incident n’est effacé par l’ajout d’une leçon.

Seuls les champs financiers numériques autorisés, les empreintes SHA-256 et
les URL publiques des sources autorisées sont ingérés automatiquement. Les
paramètres d’URL, authentifiants, clés, réponses HTTP et messages d’erreur
bruts ne sont pas conservés. La mémoire n’entraîne aucun modèle et ne modifie
aucun calcul ; ses règles anti-récidive doivent avoir un contrôle exécutable.

Les contrôles planifiés du workflow et les tests en PR constituent la
surveillance persistante. Les profils de spécialistes facilitent la revue
lors du développement ; ce ne sont pas des processus IA actifs en continu.

Le 26 octobre 2026, un test d'injection a reproduit la classe d'erreur
`fixture_relative_test_clock` : date d'analyse au 23 octobre, mais volume nul
injecté dans la dernière bougie collectée, désormais datée du 26. Le moteur
excluait correctement cette bougie future ; l'assertion bloquait la publication.
Injecter le défaut dans une séance effectivement incluse dans la fenêtre testée,
vérifier exactement l'exclusion supplémentaire et conserver un cas avec une
séance collectée postérieure à l'analyse. Ne pas retirer le filtre temporel ni
désactiver la suite de publication. Voir la
[preuve avant/après](refresh-test-window-2026-10-26.md).
