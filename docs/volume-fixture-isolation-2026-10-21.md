# Publication bloquée par un scénario de test dépendant du relevé courant

Exécution en échec : 39669754678, job 119464190328, le 21 octobre 2026.
La suite Python passe ; `tools/test_assistant_volume.cjs`, ligne 128,
refuse ensuite une réponse contenant « totaux concordants ».

Le scénario fixe une référence documentaire du 19/10 et un rapprochement
externe limité à 61 lignes, mais omettait de fixer son audit interne.
Il héritait donc de `market_volume_audit` du relevé courant. Dès que celui-ci
devient `matched`, la réponse reproduit ce statut, contradictoire avec le
scénario incomplet simulé. Ce défaut appartient au test, pas au calcul du jour.

Le scénario définit maintenant explicitement son audit interne : incomplet,
61 lignes sur 62, écart de 44 MAD / 11 unités. Ses assertions restent présentes.
Une seconde vérification exécute toute la suite sous quatre états de l’audit
courant : concordant, divergent, incomplet et indisponible. Elle reproduit
l’échec avant correction et passe après, sans modifier les données sources.
Elle fait partie de `verify_nour.py` et de la chaîne de publication existante.

Aucun collecteur, calcul, montant, volume ou garde financier n’est modifié.
Les incidents de données conservés dans le journal restent inchangés.
