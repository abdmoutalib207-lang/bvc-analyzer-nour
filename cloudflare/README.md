# Assistant Cloudflare : premier essai personnel

Ce code est un candidat a coller dans le Worker `bvc-nour-assistant`.
Il n'active pas le mode IA du site GitHub Pages et ne modifie aucun calcul,
donnee, workflow, secret ou fichier du moteur principal.

## Installation depuis le tableau de bord, y compris sur iPhone

1. Ouvrir `worker.js` dans ce dossier, copier tout le contenu et remplacer
   le programme Hello World dans « Modifier le code ». Appuyer sur « Deployer ».
2. Revenir au Worker. Dans « Liaisons / Bindings », ajouter une liaison
   **Workers AI**, nommee exactement `AI`, puis enregistrer/deployer.
3. Dans « Parametres / Settings » > « Variables et secrets », ajouter un
   **Secret**, nomme exactement `NOUR_ACCESS_TOKEN`. Choisir un code prive,
   aleatoire et unique de 20 a 200 caracteres. Ne pas le publier dans GitHub,
   le code, une URL, une capture ou une conversation. Enregistrer/deployer.
4. Ouvrir l'adresse publique du Worker. La fenetre demande ce code, un
   contexte (`MASI`, `ADI`, `ADI,RDS`...) et l'accord explicite avant l'envoi
   de la question et des donnees publiques selectionnees a Cloudflare.

Ne pas activer Workers Paid ou acheter des credits pour cet essai.
Sur Workers Free, Workers AI inclut 10 000 Neurons par jour et bloque les
operations au-dela. Le nombre de questions varie selon les entrees/sorties,
les autres usages du compte et le modele : ce n'est pas un service illimite.
Modele fixe : `@cf/mistralai/mistral-small-3.1-24b-instruct`. Aucun modele
premium, changement de forfait, substitution ou nouvel essai automatique.
Le code ne peut pas verifier votre forfait : verifier Free dans le compte.

## Ce qui est fourni au modele

Le Worker relit uniquement l'export public fixe `assistant-data.json` de Nour,
jamais une URL, un prix ou un contexte transmis par le navigateur. Cache de
30 secondes par isolate. Deux titres maximum, connaissance des fonctions,
definitions, notes comptables, dates, reserves, qualite des donnees et contexte
macro/actualites/briefing selon la question. Les montants sont copies.
Les consignes interdisent calculs nouveaux, semestres annualises, previsions,
ordres et chiffres absents. Un prompt ne garantit pas l'exactitude d'un LLM.
Verifier le texte genere avec les fiches et sources Nour.

Cet essai ne lit pas les PDF complets, ne charge pas les CSV historiques,
ne recalcule pas les scenarios du laboratoire, ne stocke pas les echanges et
ne fournit pas encore de suivi conversationnel. Il explique ces fonctions
et leurs limites ; leurs sorties chiffrees se consultent sur Nour.
Le raccordement au dialogue existant (avec code prive et reference chiffree
distincte), ses tests navigateur et l'evaluation de vraies reponses restent
a faire apres validation du Worker. Pas encore d'ouverture a un groupe.

## Controles et limites techniques

Authentification par code prive dans l'en-tete Authorization, jamais dans
l'URL. Comparaison de condensats, consentement, origines limitees (origine
du Worker et origine GitHub de l'utilisateur), JSON borne a 8 Ko, question
limitee a 1 200 caracteres, contexte a 48 Ko, sortie demandee a 700 tokens.
Nonce CSP, rendu textContent et liens HTTPS. Aucun console.log ni secret
dans la page ; aucune ecriture vers Nour. Les journaux de plateforme et les
politiques de conservation de Cloudflare restent independants de ce code.

Deux appels simultanes, quatre par minute et 40 par jour UTC **par isolate**.
Ces compteurs sont volatils et peuvent se reinitialiser ; ils ne constituent
pas un plafond global de facture. Le plafond gratuit du fournisseur ne vaut
que tant que le compte reste Free. Un appel peut continuer apres fermeture
ou expiration du delai du navigateur. Un quota/erreur ne produit pas de texte
IA fictif. Pour un groupe, il faudra un controle d'acces et de quotas durable.

`GET /api/assistant/status` indique les liaisons configurees, sans appeler le
modele ni reveler le secret. `configured: true` ne prouve pas la qualite ou le
succes d'une inference. `node cloudflare/test-worker.mjs` utilise un modele
simule et l'export du depot : aucun compte Cloudflare ni vrai modele appele.
Ne pas annoncer ce candidat comme deploye avant controle de l'adresse reelle.

## Documentation officielle consultee le 8 octobre 2026

- [Quota et facturation](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Modele Mistral Small 3.1](https://developers.cloudflare.com/workers-ai/models/mistral-small-3.1-24b-instruct/)
- [Liaison Workers AI](https://developers.cloudflare.com/workers-ai/configuration/bindings/)
- [Secrets](https://developers.cloudflare.com/workers/configuration/secrets/)
