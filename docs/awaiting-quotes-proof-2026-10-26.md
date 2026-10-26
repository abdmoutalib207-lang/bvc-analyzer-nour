# Publication avant ouverture : preuve de clôture conservée

La publication de l’interface (run 40264100840) a été refusée à 03:29 UTC le 26 octobre. La collecte était `awaiting_quotes` : zéro nouvelle observation, cours et snapshot du 23 octobre inchangés. Le contrôle de volume avait enregistré un état `intraday`, alors que la vue d’ensemble servait encore la clôture précédente. L’agrégat fournisseur différait toujours des lignes (46,44 MAD et 12 titres) ; l’ancienne preuve valable portait explicitement sur les lignes contrôlées, pas sur cet agrégat.

Le cache conservait la preuve `detail_matched` de cette clôture et l’empreinte exacte `100f7036fd5f851b6724cc2143000eb824c8301553effc2731660c25addecdf1`. La reprise du contexte déjà contrôlé n’était autorisée que pour une erreur de collecte. Elle couvre désormais aussi `awaiting_quotes`, avec tous les autres contrôles inchangés : empreinte identique, preuve applicable et publiable, séance identique à celle du contexte archivé. Une observation nouvelle, un autre snapshot, une preuve refusée ou une autre séance ne sont pas admis.

La sortie est `retained_validated`, avec la preuve et ses dates originales, sans nouvelle certification multisource. Le montant global divergent n’est pas certifié et aucun incident n’est effacé. La correction ne modifie ni cours, ni ratios, ni scores.

Contrôle anti-récidive dans `tests/test_local_market.py` : reprise sur empreinte identique, refus après changement d’empreinte, preuve non publiable ou date incompatible. Rejeu hors réseau des fichiers de l’artefact `nour-failed-verification` du run 40264100840 : refus reproduit avec la condition précédente, puis audit global réussi avec la même entrée après correction. La vérification complète précède la nouvelle publication.
