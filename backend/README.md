# Backend IA Nour — exploitation

Ce Worker explique uniquement les faits publics du contexte Nour. Il ne modifie
ni les calculs, ni les scores, ni les données financières.

## Déploiement Git Cloudflare

- Dépôt : `abdmoutalib207-lang/bvc-analyzer-nour`, branche `main`.
- Répertoire : `/backend` ; chemins surveillés : `backend/*`.
- Commande : `npx --yes wrangler@4.148.0 deploy`.
- Les liaisons `AI` et `NOUR_QUOTA` et la migration SQLite sont déclarées dans
  `wrangler.toml`. Les secrets restent exclusivement dans Cloudflare.
- `keep_vars = true` conserve les variables administrées dans le tableau de bord.
  `NOUR_AI_ENABLED` n'est volontairement pas déclaré dans `[vars]` : sans valeur
  il reste désactivé, et un déploiement ne remplace pas un choix explicite `true`
  ou `false` fait par l'administrateur. Une version enregistrée doit aussi être
  promue pour recevoir le trafic. Ne pas confondre version prête et active.
- Le secret `NOUR_ACCESS_KEYS` contient les empreintes SHA-256 des codes et une
  identité stable par accès ; aucun code ne doit entrer dans Git ou les journaux.
- Les plafonds initiaux sont 300 appels/mois au total, 100 par accès et 8/minute.
  Ils ne constituent pas un plafond de facture fournisseur.

## Chargement du contexte et diagnostic

Le contexte vient uniquement de l'URL Pages fixe `assistant-context.json`.
La requête reprend le mode `redirect: manual` du pilote Cloudflare : aucune
redirection n'est suivie et aucun en-tête client ou code privé n'est transmis.
Le corps est limité à 2 000 000 octets avant décodage, puis son schéma et
l'identifiant du snapshot sont vérifiés. Le délai de la source est de dix secondes.

Un échec renvoie un diagnostic borné : `http_302`, `http_403`, `fetch_TypeError`,
`body_read`, `too_large`, `invalid_json` ou `invalid_schema`. Aucun texte d'erreur
du fournisseur, URL arbitraire, question ou secret n'est exposé. Cet échec
précède la réservation du quota et l'appel au modèle. Le frontend conserve la
consultation locale et ne la présente pas comme une réponse IA.

Les erreurs ultérieures distinguent `quota`, `provider`, `provider_response`
et `provider_timeout`, avec seulement le type d'erreur borné et, s'il existe,
un code numérique fournisseur. Aucun message brut d'exception n'est renvoyé.
Le délai du modèle est de 40 secondes, celui du navigateur de 55 secondes pour
laisser aussi terminer la lecture de la source. Aucun nouvel essai automatique
ne double les appels, et le plafond de sortie reste à 1 000 tokens.

## Vérification

`node tools/test_worker.mjs` vérifie notamment refus des redirections, limites
du corps, diagnostic sans fuite, absence de consommation du quota en cas
d'échec de source, contexte compact et désactivation si le réglage manque.
Ce test simule les services ; il ne prouve pas une réponse IA de production.
Après déploiement, tester réellement un PER et une synthèse avec le code privé
saisi directement par l'administrateur dans Nour. Vérifier sources et réserves.
