# Nour : actualisation horaire et filet de sécurité

## Défauts constatés

Le run `39999385179`, job `120572257123`, a échoué dans la vérification : deux
constructions de tests héritaient de `GITHUB_EVENT_NAME=schedule` sans leur
créneau ; deux tests de volumes synthétiques héritaient de la date du snapshot
réel, devenue postérieure à leur séance fixe. Les contrôles n'ont pas été retirés.
Les fixtures isolent maintenant les dates, les quarantaines et le contexte CI.

La sauvegarde `always()` pouvait commiter `data/market_integrity.json` sans le
snapshot candidat correspondant après un échec. Constat : preuve liée au SHA
`a366bc0ddc2cdcaa42cf91e0501937679ee05d97feebbacad3fa8a2e593c3097`, alors que
le snapshot conservé porte `b2d07d5462041ad543863bfcce6709de6bdf7c5811e963ea2e68f2f96e823e02`.
La preuve active cohérente du dernier export a été restaurée, sans modifier
un prix. L'observation écartée reste dans `knowledge/incidents/2026-10-23-proof-transaction.json`
et le journal de contrôle. Désormais, une sauvegarde d'échec n'écrit que les
journaux ; la preuve active appartient à la transaction normale avec les données.

L'ancien rattrapage privilégiait des éditions du matin manquées et pouvait
considérer plusieurs heures antérieures comme exécutées après une seule
publication tardive. Un cron arrivé pendant la nuit pouvait construire une
édition de la veille. Ces comportements sont remplacés par une cible courante
sur la journée locale, avec historique des absences conservé.

## Horaires réellement configurés

Africa/Casablanca, lundi au vendredi : 09:45, 10:45, 11:45, 12:45, 13:45,
14:45, 15:45 ; les contrôles existants de 16:00, 16:45, 17:15 et 17:45 sont
préservés. Un réveil supplémentaire à 09:55 ne relance le créneau de
09:45 qu’en cas de première source vide ou inaccessible, et une seule fois
après 09:55 ; il ne crée pas une édition fictive de 09:55. Le filet de sécurité demandé est ajouté à 19:00. Les horaires
normaux officiels donnent le fixing de clôture vers 15:30 et la fin de
post-négociation vers 15:55 ; 16:00 reste une vérification, jamais une preuve
que chaque source a déjà confirmé la clôture.

Référence primaire : https://www.casablanca-bourse.com/market-data/horaires-cotation-comptant

Le watchdog se réveille à :05, :25 et :55 entre 09h et 19h, et après chaque
workflow de publication terminé. Il attend dix minutes de grâce, sélectionne
uniquement le dernier créneau dû, effectue au maximum trois demandes espacées
de trente minutes et s'arrête à 20:15. Un nouveau créneau ne reste pas bloqué
par une édition plus ancienne. Une demande acceptée ne prouve pas son exécution.
Le passage de 19h est donc également rattrapable à 19:25 et 19:55.

Une porte commune compare la cible à la publication réellement servie :
manifest, SHA-256 du runtime, même run GitHub et conclusion `success`.
Les réveils redondants ne reconstruisent pas un créneau déjà publié et vérifié.
Les reconstructions explicitement demandées et les changements de code restent possibles.
Les anciens événements `executed` de l'ancien algorithme sont conservés avec
leur statut historique, puis réévalués ; ils ne sont pas repris aveuglément.

Une observation de séance horodatée peut rester visible jusqu'au prochain
passage horaire, avec quinze minutes de tolérance, puis expire. Sa date et son
heure restent celles de la collecte réelle. Elle reste provisoire, séparée
des clôtures, historiques techniques et scores, sans annualisation ni prix inventé.

## Comparaison du principal — lecture seule

Consultés à partir du principal `3febf8d39bdf917bbde7180e10d0fe99a74d9bbc` :
`.github/workflows/update_bvc.yml`, `pipeline/porte_rattrapage.py`, `bvc_config.py`.
Le principal utilise des réveils redondants, une porte sur la séance portée
et indique un ordonnanceur externe cron-job.org. Son commentaire annonce un
auto-relais ; aucun step de self-dispatch n'apparaît dans le workflow lu.
Nour reprend la sélection de séance et les réveils redondants, sans copier
une garantie d'auto-relais non démontrée ni modifier le principal.

Limite : les crons GitHub peuvent être retardés ou omis. Le watchdog est un
workflow séparé mais utilise le même ordonnanceur GitHub : ce n'est pas un
service externe indépendant. L'accès à la configuration cron-job.org du
principal n'est pas disponible ici ; aucun réveil externe Nour n'est déclaré
configuré. Son raccordement peut appeler le workflow Nour `nour_daily.yml`
avec `slot=auto` à 09:55 puis chaque heure et à 19:00, sans toucher au principal
ni exposer de jeton dans le dépôt. Une minute d'exécution garantie exigerait
un tel ordonnanceur indépendant et la disponibilité des sources et runners.

## Validation et preuves

Les tests portent sur le retard de cron, le changement de journée, le week-end,
la conversion UTC/Casablanca, le créneau de 19h et ses reprises, la preuve
publique, la priorité à la collecte courante et la conservation des exécutions
réelles. Les injections ADI et les refus d'intégrité globale sont conservés.
Les identifiants CI, PR et déploiement sont renseignés dans la PR après exécution.
