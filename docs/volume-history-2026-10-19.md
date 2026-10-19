# Historique des volumes transmis le 19 octobre 2026

Export utilisateur `historique_volume.xlsx`, feuille `in`, A1:E39, empreinte
SHA-256 `a8e93cc8455683d2beb774bfede0915902fba6a8cb13bc9924079ee9a3c10785`.
38 lignes et 21 séances du 21 septembre au 19 octobre 2026. Les métadonnées du
classeur ne prouvent pas son origine réseau. Le statut demeure documentaire,
fourni par l’utilisateur et relu ; aucune collecte officielle automatique prétendue.

| Séance | Marché | Volume MAD | Transactions | Titres échangés | Ligne |
| --- | --- | ---: | ---: | ---: | --- |
| 19/10/2026 | Central | 113 956 983,12 | 3 671 | 876 356 | in!A2:E2 |
| 16/10/2026 | Central | 117 005 677,43 | 3 114 | 506 826 | in!A3:E3 |
| 12/10/2026 | Central | 52 945 136,05 | 3 317 | 199 770 | in!A11:E11 |

Les 3 671 transactions du 19/10 confortent le compteur « contrats » de la capture
officielle, sans établir une équivalence universelle entre ces deux libellés.
Les anciens compteurs fournisseurs 2 851 et 2 355 restent des observations brutes
dont la date propre n’était pas attestée ; le fichier ne les rattache à aucune
autre séance par déduction. Pour le 16/10, la ligne datée donne 3 114 transactions.

Le contrôle `compare_current` recherche uniquement la même séance et le marché
central. Il conserve séparément les divergences de montant, quantité et compteur.
Une séance non couverte reste non couverte. Les transferts, apports de titres et
augmentations de capital ne sont jamais additionnés au marché central.

Ce fichier ne permet pas d’identifier l’instrument manquant dans l’écart actuel
de 44 MAD / 11 unités / une ligne. L’incident demeure ouvert. Aucune bougie ni
archive existante n’est écrasée. L’export alimente une référence publique séparée
et un rapprochement à chaque construction ; il ne devient pas un flux automatique.

Anti-récidive : tester les dates exactes, les marchés séparés, les centimes,
les doublons, les types des compteurs et l’absence de repli vers la veille.
Voir `tests/test_volume_history.py`.
