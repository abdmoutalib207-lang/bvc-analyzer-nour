# Mémoire de projet vérifiable

Date : 2026-10-06. État de reprise observé : commit Nour
`ca350006e738bdb6e48820ebcd5d9f1b52b19c92`, publication Actions
`37391634686` réussie. Revalider ces références lors d'une prochaine reprise.

- Principal : lecture seule. Nour : développement et publication autorisés.
- Source de vérité des réponses : rapport Nour daté, pas le score du principal.
- JET S1 2026 : RNPG rapproché avec réserves, voir
  `docs/financial-reconciliation-2026-10-05.md` et `docs/batches/2026-10-05-JET.md`.
  Ne pas réintroduire l'ancien blocage ni convertir le RNPG S1 en PER annuel.
- CASH : les changements de capital non rapprochés bloquent les ratios concernés.
- M2M : les réserves d'examen limité ne sont pas une contradiction arithmétique.
- AGMA, Salafin, Eqdom : unités, provisions et capitaux propres contrôlés
  séparément; références documentaires et ratios disponibles sont deux compteurs.
- MASI : l'historique de cours commence au 02/01/2023; le score prospectif
  n'est archivé que depuis octobre 2026. Pas d'historique de scores reconstitué.
- Code canonique du score : `nour-quant-v1`; aucune validation prédictive.
- Questions au LLM : explication seule, aucune modification de calcul ni ordre.

- Lot comptable du 26 octobre 2026 : voir `docs/accounting-methods-2026-10-26.md`
  et `knowledge/accounting_methods.json`. Les comptes consolidés ne sont pas
  tous IFRS. HPS 2025 comptabilise sa R&D en charges ; ADI est en normes
  marocaines ; RDS et Wafa Assurance décrivent des changements de méthode et
  des comparatifs à distinguer. Les preuves portent sur des pages et périodes
  sélectionnées, pas sur une certification de tout le dossier.
- Après chaque tâche : appliquer `docs/agent-learning.md`, conserver les preuves
  et les régressions dans Git, puis relire ces leçons à la prochaine reprise.

Cette mémoire est un aide-mémoire, jamais une preuve autonome. Lire les tests,
sources et réserves actuels avant d'utiliser un chiffre. Ne pas y stocker des
conversations privées, identifiants ou clés API.

Préférence d’interface confirmée le 19 octobre 2026 : alléger les mentions des
fournisseurs de marché et centraliser les attributions dans Sources ; conserver
les collecteurs, la provenance exacte et les réserves dans les données. Les
logos servent à identifier les sociétés, sans partenariat implicite. Ne jamais
utiliser le logo d’une société étrangère simplement parce qu’un fournisseur le
relie au ticker local. Une image non confirmée laisse le sigle affiché.
Les miniatures TradingView de 18 px peuvent être des pictogrammes génériques :
utiliser les variantes détaillées explicitement déclarées et vérifier leur rendu.

Le 19 octobre 2026, la collecte Nour passe à chaque heure de 09:45 à 17:45
en jours ouvrés (Africa/Casablanca), avec les éditions 09:45, 12:45, 16:00
et le contrôle 17:15 conservés. Une actualisation horaire ne remplace pas les
briefings archivés ; un relevé provisoire ne devient pas une clôture.
