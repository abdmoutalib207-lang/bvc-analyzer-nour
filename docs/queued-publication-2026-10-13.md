# Publication en attente : correction du 13 octobre 2026

Nour uniquement. Aucun changement au moteur principal ni aux calculs financiers.

Échec observé : run `38441608615`, job `115450446644`, étape
`Save validated snapshots and pages`. Calculs, tests et navigateur avaient
réussi ; l'envoi Git était refusé avec `main -> main (fetch first)`.
Le run était parti de `5d321764e2e3864c771a0b60c138c5d781bf2c59`,
alors que la publication précédente avait déjà créé un nouveau commit de données.

Le groupe de concurrence sérialise les publications, mais ne change pas le SHA
de l'événement qui a attendu. Checkout utilise maintenant explicitement `main`
au démarrage effectif du job, avant toute collecte. `NOUR_CODE_COMMIT` capture
le HEAD réellement lu ; runtime et archives ne présentent plus l'ancien SHA
d'événement comme identité du code exécuté. Exécution locale inchangée : repli
sur `GITHUB_SHA` en l'absence de cette variable.

Pas de force-push, de reset, de résolution automatique des conflits ni de
rebase aveugle des pages générées. Une écriture extérieure pendant le job peut
toujours faire refuser l'envoi : c'est une protection conservée, pas une panne
de source ni une erreur de ratios. Ne pas fusionner une autre modification de
Nour pendant une publication active si l'on veut éviter ce cas.

Les tests vérifient la sélection du commit réel, le checkout de main et l'absence
de force-push. Ils ne prétendent pas reproduire la file d'attente du service
GitHub ; la preuve d'incident est conservée dans les logs du run précité.
