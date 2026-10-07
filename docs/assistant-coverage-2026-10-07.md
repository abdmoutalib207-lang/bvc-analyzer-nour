# Assistant Nour : couverture des fonctions, 7 octobre 2026

L’assistant public lit les données publiées et explique les fonctions de Nour.
Il reste déterministe. La passerelle générative reste désactivée et aucune
modification n’est apportée au dépôt principal `-bvc-analyzer`.

## Fonctions accessibles

| Domaine | Exemple de question | Données et méthode |
|---|---|---|
| Pages et exports | Comment télécharger les données ADI ? | Fiches, CSV OHLCV, rapport et études JSON/CSV |
| MASI et séance | Combien de valeurs montent et baissent ? | Clôture, variation, amplitude, flux, largeur et secteurs de la séance publiée |
| Graphiques | Comment zoomer et lire les bougies ? | Plages, déplacement, clavier, overlays et limites |
| Technique | MM50 ADI ; activité ADI sur 20 séances | Indicateurs déjà présents dans le rapport, sans recalcul du score |
| Fondamentaux | RNPG JET S1 2025 et 2026 | Périodes, sources, réserves, dénominateurs ; total et groupe séparés |
| Score | Comment est calculé le score ADI ? | Valeur, contributions, poids, couverture et archive prospective |
| Statistiques | Statistiques ADI sur 5 séances et Wilson | Fréquence, médiane, percentiles et taille d’échantillon publiés |
| Liquidité | Liquidité ADI | Médianes, scénario de 1 000 titres et capacité hypothétique publiée |
| Risque | Risques ADI face au MASI | Bêta, corrélation, volatilité, drawdown, rendement relatif et fenêtre exacte |
| Comparables | Compare ADI aux titres du même secteur | Pairs de même exercice, périmètre et norme ; médianes absentes si insuffisants |
| Laboratoire | Laboratoire ADI 20 séances achat 1 %, vente 1 % | Mêmes observations, filtres et formules que la page interactive |
| Actualités | Actualités officielles JET le 06/10/2026 | Titres, dates, source officielle ou presse ; filtrage par titre et thème |
| Macro/international | Prix et source du Brent ? | Dernières observations internationales publiées, datées |
| Briefings | Résume le briefing de clôture | Lecture des éditions déjà générées, statut et séance de référence |
| Qualité/collecte | Pourquoi CMT est limité ? Quand a lieu la collecte ? | Âge, anomalies, réserves, états des collecteurs, horaires et retard réel |
| Assistant/ECC | À quoi sert ECC ? Est-ce génératif ? | Explication de la couche conversationnelle, des outils de développement et limites |

« Toutes les fonctions » affiche les 16 domaines avec leurs exemples.
Le titre choisi reste le contexte de la conversation. Après une question au
laboratoire, « Et sur 60 séances avec glissement 0,2 % ? » conserve le titre,
la période, le régime et les autres frais.

## Exactitude et disponibilités

- Les données supplémentaires sont copiées du rapport et des éditions déjà
  générées. Les scores et ratios financiers ne sont pas recalculés par l’assistant.
- Le laboratoire réutilise directement `NourResearch.select`, `summary` et `net`.
  Horizon, période, régime et frais non implémentés ou ambigus sont refusés.
- Les questions datées sur les titres peuvent charger leur CSV OHLCV complet,
  à la demande. Son empreinte SHA-256 doit correspondre à l’export courant.
  Dates invalides, futures, doublons et OHLC incohérents ne donnent aucun chiffre.
- Les ratios annuels ne remplacent pas un ratio semestriel. Un résultat total ne
  remplace pas le RNPG, ni des capitaux propres totaux la part du groupe. Les
  étiquettes d’activité financière douteuses restent signalées ; PNB et CA sont distincts.
- Les publications du radar restent des références datées, sans résumé inventé
  du corps des articles. Une absence dans un flux partiel n’est pas une absence de publication.
- Une cotation provisoire archivée ne devient pas un cours en direct. Les
  réponses indiquent la séance du titre, qui peut différer de la date d’analyse.
- L’export reste chargé à l’ouverture de la fenêtre. Les historiques complets
  ne sont téléchargés que pour les questions datées qui en ont besoin.

## Limites qui restent visibles

La reconnaissance suit des intentions et un vocabulaire explicites : elle ne
garantit pas la compréhension de toute formulation libre. Une question non
reconnue demande une reformulation. Elle n’active pas un fournisseur génératif.

Les bandes de Bollinger sont expliquées ; leurs valeurs calculées dans le
graphique ne sont pas incluses dans cet export. Les autres indicateurs à une
date ancienne ne sont pas reconstruits. Le MASI conserve son historique de
clôtures, sans OHLC fictifs. Le PER global/historique du marché, ROIC, carnet,
spread réel, stratégies personnalisées et probabilité de prochaine séance
ne sont pas intégrés. Les observations macro ne constituent pas un historique
de taux ou d’inflation validé. Aucun délai d’exécution personnalisé n’est inventé.

Les cours sur trois ans ne prouvent aucune efficacité prospective du score.
Les fréquences et backtests exploratoires gardent leurs biais et limites.

## Vérification

Vérification locale : 132 tests Python réussis ; 320 scénarios titre/thème et
29 réponses précises conservés ; 419 réponses supplémentaires contrôlées,
dont 108 combinaisons laboratoire/horizon/période/régime/frais. Contrôle des
89 pages et parité exacte des données de l’assistant avec les exports sources.

Le parcours Chromium du workflow vérifie aussi le guide complet, la parité du
laboratoire, les suivis de frais/horizon et une ancienne bougie lue dans le CSV
complet, à 375, 768 et 1 440 pixels, avant et après déploiement. Le résultat de
publication doit être contrôlé dans le workflow et sur les ressources réellement servies.


## Publication effectivement vérifiée

- Version du code : `d26d92e292321d2ed8d24b1f2bdcab9f3daf9026` (après
  `41d03581d97247ab504febd57d8a14a6616ea2d5`).
- Workflow [37553486744](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/37553486744)
  terminé avec succès le 7 octobre 2026 : 132 tests Python, 320 scénarios de base,
  29 réponses précises et 419 réponses de domaines réussis ; 89 pages auditées.
- Chromium : 12 parcours page/largeur avant publication et 12 sur le site
  effectivement publié, à 375, 768 et 1 440 pixels ; aide sans JavaScript vérifiée.
  Contrôle publié terminé à 00:46:38 UTC.
- Relecture indépendante des ressources du site publié : les trois fichiers JS
  correspondent exactement aux fichiers validés ; l’export de l’assistant est
  identique à la projection du rapport publié. Les cinq briefings correspondent
  à leurs JSON sources. 16 domaines et 80 titres sont présents ; IA publique désactivée.
- SHA-256 de `assistant.js` :
  `2a9dbde8e9f9ebcf4b36a6b4e4611cf208566c06e3ee8044187ac5d285a8d5ad`.
- SHA-256 de `assistant-domains.js` :
  `606aaab1155bc15eaa04f09032f6d85cf50e611222a11ce3dde48aed974a6de2`.
