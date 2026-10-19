# Provenance distincte des compteurs de séance

Le 19 octobre, le relevé global fournisseur annonce 113 956 983,12 MAD et
876 356 unités. Les 61 lignes d'actions recoupées donnent 113 956 939,12 MAD
et 876 345 actions. La capture du site de la Bourse de Casablanca transmise
par l'utilisateur corrobore le montant global et la quantité et affiche
3 671 **contrats**. Le compteur fournisseur « transactions » vaut 2 851.

La date du MASI ne certifie pas la date propre de tous les champs associés.
Le compteur 2 851 reste conservé comme observation source, mais sa date propre
non attestée l'exclut du compteur validé de séance. Aucun rattachement au 16
octobre n'est inventé : l'archive source disponible dans Nour annonce 2 355
pour le 16, et la capture du moteur principal montre aussi cette comparaison.
Le principal reste exclusivement consultable et n'est pas modifié.

`data/market_reference.json` conserve une transcription **revue manuellement**
de la capture officielle : séance précisée par l'utilisateur, heure de revue,
empreinte du fichier fourni, URL publique, unités et libellé « contrats ».
La capture isolée ne montre pas sa date de séance ; cette limite est explicite.
Les tentatives d'accès direct à la page officielle et au bulletin ont retourné
une indisponibilité HTTP. Ne pas présenter cette transcription comme une
collecte automatique du site officiel ni comme un rapprochement du détail.

La référence n'est appliquée que si sa séance et ses montants/quantités
correspondent exactement au relevé. Une ancienne référence, un total changé,
une preuve non relue, une URL étrangère, un compteur invalide ou une empreinte
absente la rendent inapplicable. Le contrôle final refuse une preuve altérée.
Le contrat de volume ligne par ligne et son blocage des corrections divergentes
restent inchangés. L'écart global de périmètre demeure ouvert dans le journal.

La présentation et l'assistant distinguent contrats officiels, compteur
fournisseur non daté et actions détaillées. Le relevé brut reste intact.
Le fichier public `market-reference.json` expose la méthode et les réserves.
Un changement de ce seul fichier de référence déclenche le workflow.

Vérification locale : 339 tests Python, 27 cas JS de volumes/compteurs,
autres suites JS et Worker, audit des exports et audit du rapprochement réussis.
Le contrôle navigateur et la vérification du site public restent requis.
Typage, pourcentage de couverture, audit d'accessibilité complet et inférence
LLM réelle ne sont pas mesurés par ces commandes.
