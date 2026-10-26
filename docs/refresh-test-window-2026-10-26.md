# Publication bloquée par une injection hors fenêtre — 26 octobre 2026

## Incident observé

Le site réellement servi annonçait une collecte du 26 octobre à 15:03:16
(Africa/Casablanca), dernière clôture intégrée au 23 octobre. Des exécutions
ultérieures collectaient la clôture du 26, construisaient les pages, puis
échouaient avant sauvegarde et déploiement. Un déclenchement réussi ne prouve
donc ni une publication ni un rafraîchissement visible.

Deux journaux indépendants montrent la même assertion en échec :

- [Run 40366828443](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/40366828443), à 17:19 UTC.
- [Run 40371519986](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/40371519986), à 17:54 UTC.

`ResilienceTests.test_suspended_title_and_session_without_transaction_are_local`
attendait au moins une séance sans échange exclue. Il injectait un volume nul
dans `candles[-1]`, le 26 octobre, puis construisait un rapport au 23 octobre.
Le filtre temporel exclut légitimement le 26 : le compteur observé reste zéro.
Les 460 autres tests passaient dans ces exécutions. Cette observation ne permet
pas d'attribuer tous les anciens incidents de continuité à cette seule cause.

## Preuve source conservée

L'artefact d'échec `12673311868` contient le snapshot réellement collecté,
son contrôle de marché et les sorties non publiées. SHA-256 du snapshot :
`11f40f7d8f1aef3d67956589af7a4a9621cdc9b7cfa3cea2ba2bdac98b14ea5c`.

Son contrôle du 26 octobre à 17:49:45 UTC est `matched`,
`publication_safe: true`, avec 65 instruments actifs, 277 816 400,24 MAD et
1 681 081 actions concordant ligne par ligne entre CDG et Wafabourse. Il ne
s'agit pas d'une certification de l'indépendance de leurs données amont.

## Correction et anti-récidive

Le défaut est injecté dans la dernière bougie avec échange effectivement
incluse dans la date d'analyse. L'assertion exige désormais exactement une
exclusion supplémentaire par rapport au même état sain et une date finale
statistique inchangée. Un second sous-cas ajoute une bougie ultérieure à
l'analyse pour exercer explicitement le décalage qui provoquait l'incident.
Les 79 autres émetteurs doivent rester identiques au rapport de référence.

La reproduction utilise le test original du commit et le snapshot de
l'artefact : échec `0 not greater than or equal to 1` avant correction ;
réussite du même scénario et du sous-cas futur après correction. Le contrôle
complet est exécuté sur les entrées conservées de l'échec et une construction
au 26 octobre, avant relance de la publication.

Aucune formule, donnée source, règle de fraîcheur, quarantaine ou condition de
rapprochement n'est assouplie. La suite complète et les contrôles navigateur
restent bloquants. La preuve finale de disponibilité reste le workflow de
publication et les fichiers réellement servis après déploiement.

## Publication vérifiée

La [publication 40377767635](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/40377767635)
a terminé avec succès le 26 octobre à 18:42:53 UTC. Générateur :
`b0e6fe7765914f91c40b042561f4f2e95583ca75` ; commit des données publiées :
`6c20ad2d4962d61b4c452af325cb60e57e09ef14`.

Les 461 tests Python, la porte de validation complète et 135 parcours
navigateur (45 normaux, 45 avec ADI en quarantaine temporaire, 45 sur le site
public) passent. Le contrôle final des montants et quantités réellement servis
passe également.

Une lecture indépendante de `publication.json`, `runtime.json`, `report.json`,
`index.html`, `market-integrity.json` et `calculation-health.json` confirme :
collecte à 18:27:01 UTC, clôture du 26 intégrée, 80 émetteurs dont 65 cours datés
du 26, rapprochement `matched` des 65 instruments actifs et aucune défaillance
arithmétique bloquante. Les empreintes servies du runtime, du rapport et de
l'accueil correspondent exactement au manifeste. ADI affiche 364,90 DH au
26 octobre ; les anciennes dates des titres sans nouvel échange sont conservées.

Cette publication établit la résolution de ce blocage. Elle ne prouve pas que
tous les futurs créneaux seront ponctuels : leur exécution et leur publication
restent à contrôler séparément.
