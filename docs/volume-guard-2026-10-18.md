# Correction du 16 octobre et garde multisource

La comparaison des 61 lignes des PDF CDG et Wafabourse fournis le 18 octobre,
puis des API publiques des deux distributeurs, retrouve exactement
117 005 677,43 MAD et 506 826 titres. Le détail Nour conservait
116 448 828,23 MAD et 504 567 titres, soit un écart de 556 849,20 MAD et
2 259 titres. Le montant global Nour était correct ; le détail restait en conflit.

| Code Nour | Quantité conservée | Quantité recoupée | Écart MAD |
| --- | ---: | ---: | ---: |
| BOA | 11 089 | 11 092 | 543,00 |
| CMGP | 23 199 | 25 199 | 520 000,00 |
| CSR | 3 851 | 3 951 | 17 300,00 |
| DTT | 260 | 261 | 345,00 |
| HPS | 8 684 | 8 685 | 517,00 |
| IAM | 66 458 | 66 603 | 13 050,00 |
| JET | 2 309 | 2 310 | 1 440,00 |
| MOX | 32 | 33 | 384,00 |
| STK | 2 926 | 2 928 | 95,70 |
| TGCC | 4 107 | 4 112 | 3 174,50 |

Les OHLC restent identiques. Seuls quantités et montants de cette séance sont
rapprochés, sur preuve de chaque ligne. Les scores archivés ne sont pas réécrits.
Le journal conserve les valeurs avant/après et les conflits résolus.
Le moteur principal est resté exclusivement consulté.

## Contrôle automatisé

`tools/check_market_integrity.py` utilise le collecteur CDG et l'action publique
Wafabourse `MARKET-LIST-SYMBOL`, comme son frontend public. Son jeton de proxy
est éphémère, obtenu par la requête normale du frontend et jamais exporté.
Une mise à jour de ce contrat ou une panne donne un refus explicite ; aucun
contournement de connexion ni nouvel abonnement n'est utilisé.

Les quantités de l'API Wafabourse sont correctes (`QteEchangee`). Le PDF du
18 octobre dupliquait le montant monétaire dans « Qté » : cet export ne doit
jamais être interprété comme une quantité d'actions. Les données restent
attribuées à la séance réelle, pas à la date d'impression du dimanche.

La garde exige une séance clôturée, des identités uniques dans le référentiel
opérateur, une couverture identique, les montants/cours par ligne, puis les
sommes DH et titres. Des erreurs opposées peuvent s'annuler dans le total :
le contrôle ligne par ligne reste donc obligatoire. Les données manquantes
et les anciennes références d'instruments sans transaction ne valent pas zéro.

Une correction transactionnelle des seuls volumes est permise après ces
contrôles. Toute quantité à réviser doit aussi être attestée par le second
fournisseur ; une quantité absente n'autorise aucune révision de ce champ.
Prix divergents, séance différente, doublons, données partielles,
provisoires, source miroir, chiffres non finis ou quantités monétaires déguisées
ne peuvent pas autoriser le remplacement. Sans seconde source, aucune nouvelle
correction de conflit ; un dernier snapshot déjà cohérent peut rester consultable,
avec le contrôle externe indiqué indisponible. Deux distributeurs distincts ne
garantissent pas que leurs flux amont sont indépendants.

Le rapport lie la preuve à l'empreinte exacte de `market_snapshot.json` ; une
ancienne preuve ne peut donc pas valider silencieusement une autre version.
Le dernier audit de publication vérifie de nouveau montants, quantités, couverture
et preuve de rapprochement avant sauvegarde des pages. Les tâches programmées
et la mémoire durable sont détaillées dans `market-control-team.md` et
`error-memory.md`. Les diagnostics sont conservés même en cas de publication refusée.
