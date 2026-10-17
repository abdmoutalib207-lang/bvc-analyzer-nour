# Consolidation après audit externe — 17 octobre 2026

Base vérifiée : `8121c17e2f5a049f6d980c7cd6992f2d4a1d94e3`.
Branche : `nour-consolidation-audit-oct17`. Périmètre exclusif : Nour.

## Objectif et critère de réussite

Nour est un centre de consultation financière BVC : chiffres, calculs,
documents, actualités et explications sourcés au même endroit. La prédiction
n'est pas son objectif. La cible de qualité 9,5/10 ne constitue pas une note
acquise ni une garantie de couverture documentaire complète.

## Réalisé dans ce lot

| Constat de l'audit | Correction vérifiable |
| --- | --- |
| Contexte IA volumineux | Index compact dérivé du rapport, sélection par intentions, budget de 40 000 octets UTF-8, aucune série brute ni ligne de laboratoire envoyée |
| Réserves raccourcies côté serveur | Suppression de la troncature des avertissements et notes de preuve ; refus explicite si leur conservation dépasse le budget |
| PER et éléments exceptionnels | Règles contrôlées : le BPA publié peut intégrer des exceptionnels ; un PER normalisé nécessite des retraitements documentés ; ne pas recalculer le PER avec le BPA arrondi affiché |
| Citations imprécises | Références par poste, période, unité, statut et page PDF conservées ; liens `#page=` disponibles dans la réponse |
| Questions transversales | Intentions fondamentaux, technique, risque, secteur, score, actualités, macro, qualité, laboratoire, briefing et synthèse ; sélection de deux titres maximum |
| Banque traitée comme industrie | Guides sectoriels déjà contrôlés dans Nour transmis avec les faits ; ne pas inventer les KPI dont le guide demande la vérification |
| Date passée confondue avec état actuel | Les questions datées ne reçoivent pas les ratios/indicateurs actuels à la place d'un historique non récupéré ; MASI daté conservé ; dates invalides refusées |
| Source mise à jour pendant la conversation | Identifiant SHA-256 du contexte ; refus 409 en cas de changement, vérification par le navigateur |
| Dépendance LLM | Consultation locale affichée explicitement en cas d'échec IA, sans se présenter comme une réponse générée |
| Statut global de collecte trop sommaire | Résultats distingués et tableau par titre ; les nouvelles divergences archivent champ, valeur conservée, observation, heure, source et motif du refus |
| Anciens dix conflits sans chiffres d'observation archivés | Titres et champs exposés ; valeurs manquantes dites non archivées, jamais reconstruites ni arbitrées |
| Profondeur historique | État existant conservé + nombre de séances, profondeur courte/profonde (seuil descriptif 252), âge et fenêtre post-reprise séparée |
| Provenance ambiguë | `source_snapshot_commit`, `generator_commit`, empreinte du snapshot et manifeste d'artefact distinct avec `publication_commit` et empreintes des exports |
| Succès du processus confondu avec succès des données | Synthèse Actions des vrais statuts `conflict`, `partial`, `updated`, etc., en plus du résultat du processus |
| Documentation périmée | Correction des trois créneaux réels et distinction local / IA facultative configurée |

Le manifeste de publication est écrit **après** le commit des données, dans
l'artefact Pages, sans être commité dans son propre contenu. Il décrit un
artefact préparé : seul le workflow de déploiement et le site réellement servi
confirment sa publication. Une reconstruction locale ne prouve rien en ligne.

## Backend IA reproductible, activation distincte

`backend/worker.mjs`, `backend/context.mjs` et `backend/wrangler.toml`
fournissent une version revue et testable du backend, auparavant absent du dépôt.
Ils ne décrivent pas le code effectivement déployé tant qu'une activation
Cloudflare et un test réel n'ont pas été réalisés.

Le Worker relit exclusivement l'index public Nour à une URL fixe. Aucun fait,
URL fournisseur, modèle, outil ou fichier fourni par le navigateur ne commande
ses lectures. Il ne possède aucun jeton GitHub ni fonction d'écriture métier.
Les seules écritures internes sont les compteurs de quota.

Protection prévue : origine exacte, code secret vérifié par empreinte SHA-256,
identité stable par accès, consentement, JSON et taille limités, désactivation
administrateur, quota mensuel global, quota mensuel par accès, limite par minute,
réservation transactionnelle dans un Durable Object, erreurs minimales sans
question/code/contenu de réponse dans les journaux applicatifs. Les quotas
survivent au redémarrage et aux appels concurrents ; les appels échoués après
réservation consomment le quota. Un timeout navigateur ne rembourse pas un appel.

Ce sont des **plafonds d'appels**, pas une garantie de facture en dollars.
La tarification fournisseur, les coûts de stockage/requêtes et les alertes
budgétaires du compte restent à contrôler séparément. Pas de compte client,
facturation ou authentification commerciale revendiqués.

Activation administrateur, après revue et validation des coûts :

1. Conserver le code déployé et ses paramètres pour pouvoir revenir en arrière.
2. Configurer la liaison AI et le Durable Object selon `backend/wrangler.toml`.
3. Créer un nouveau code hors conversation et enregistrer seulement son
   empreinte dans le secret `NOUR_ACCESS_KEYS` : objet JSON dont chaque clé est
   le SHA-256 d'un code, chaque valeur `{ "id": "identite_stable", "enabled": true }`.
   Garder la même identité lors d'une rotation conserve le quota de l'accès.
4. Déployer et vérifier la version avec `NOUR_AI_ENABLED=false`.
5. Après publication de l'index Nour, activer explicitement
   `NOUR_AI_ENABLED=true`, vérifier un vrai cas PER et une synthèse ADI, puis
   contrôler les réponses et réserves. Revenir à `false` coupe immédiatement
   les nouveaux appels à l'entrée du Worker.
6. Retirer l'ancienne empreinte lors de la rotation. Ne placer aucun code,
   secret ou fichier `.dev.vars` dans Git, une PR ou une conversation.

Références techniques officielles :
[modèle Mistral Workers AI](https://developers.cloudflare.com/workers-ai/models/mistral-small-3.1-24b-instruct/),
[transactions Durable Objects](https://developers.cloudflare.com/durable-objects/best-practices/rules-of-durable-objects/).

## Reproductibilité numérique

La publication est construite sous Python 3.11. Python 3.12 a changé
l'addition des flottants dans `sum()`. Avec les mêmes entrées du 16 octobre,
cela déplaçait trois arrondis : MM200 ADI 433,78/433,77 ; MM20 CDM
938,67/938,66 ; MM50 SRM 460,92/460,93. L'addition ordonnée explicite
préserve désormais l'arithmétique publiée pour les indicateurs concernés,
sans migration silencieuse du calcul. Un cas fixe contrôle cette limite
d'arrondi ; les scores et fondamentaux sont contrôlés séparément.

## Validation et limites

La commande de livraison est `python tools/verify_nour.py --build --asof 2026-10-17`.
Elle inclut les tests Python, contrôles JS existants, tests unitaires Worker,
parité stricte de l'index avec les faits canoniques et audit arithmétique.
La sélection Python et JavaScript est comparée sur des cas identiques.
Les 80 synthèses individuelles doivent tenir sous le budget avec toutes
leurs réserves. Les deux titres restent soumis au même budget ; aucune
promesse de synthèse illimitée.

La QA navigateur locale requiert Chromium. Si son téléchargement est bloqué,
les parcours exécutés dans Actions restent nécessaires avant de déclarer le
lot prêt à fusionner. Les doubles de stockage/IA ne remplacent pas un test
dans le runtime Cloudflare. Ni couverture de tests chiffrée, audit WCAG
exhaustif, sécurité commerciale, ni qualité réelle du LLM ne sont certifiés.

## Travail restant pour une cible de qualité 9,5/10

- Résoudre les conflits de volume par preuve indépendante compatible, sans
  écrasement automatique ; la visibilité ne signifie pas résolution.
- Étendre la revue primaire des publications : une référence AMMC ou un
  contrôle arithmétique n'est pas une certification des 80 dossiers.
- Compléter l'index documentaire par passages contrôlés et dates de
  disponibilité ; ce lot exploite les preuves et méthodes déjà présentes,
  pas une recherche sémantique exhaustive dans tous les PDF.
- Déployer et tester réellement la nouvelle version du Worker, la rotation,
  les quotas et les réponses françaises, puis arabes selon des cas approuvés.
- Élargir le jeu de questions et vérifier les citations phrase par phrase,
  l'absence de causalités inventées, les comparaisons et les limites datées.
- Hiérarchiser ensuite l'accueil : comprendre la séance, explorer un titre,
  vérifier sources et calculs. L'amélioration esthétique ne précède pas les
  contrôles de fiabilité.

L'issue #11 reste la spécification du chantier documentaire plus large.
Elle n'est pas close par ce lot. Aucun accès ni modification au moteur
principal n'est nécessaire à cette livraison.
