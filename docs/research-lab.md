# Laboratoire Nour v1

Le laboratoire décrit les archives disponibles et les coûts hypothétiques. Il ne reconstruit pas le score canonique dans le passé, ne règle aucun coefficient sur les rendements et ne certifie aucune rentabilité.

![Laboratoire publié, ATW sur 5 séances, frais achat et vente 1 %, capture du 6 octobre 2026](research-lab-preview.jpg)

Version déployée et vérifiée : commit `ae23b2ab352c8a63a03a96cb83edf300efc48c4c`, workflow `37391634686` réussi. 107 tests Python, 2 400 scénarios graphiques, 108 scénarios de filtres du laboratoire et contrôles de rendu. Au 6 octobre : 917 observations MASI, 3 311 observations de tendances (titres et horizons distincts, à ne pas agréger en échantillon indépendant), risque calculable sur 72 titres, comparaison sectorielle sur 10 titres, première archive prospective quotidienne. Les scores et fondamentaux courants sont inchangés par ce lot.

## Protocole historique

Le calendrier est celui du MASI daté, sans cours futurs. Chaque horizon (5, 20, 60 séances) possède une grille fixe commune aux titres : un signal tous les horizon + 1 jours, après 200 observations MASI. La règle préalable est clôture supérieure aux moyennes mobiles 20 et 50 calculées au signal, avec leurs seules observations antérieures ou courantes. L'entrée est la clôture suivante, jamais la clôture du signal. La sortie est la clôture horizon séances MASI après l'entrée. Ce sont des observations de prix, pas des ordres exécutés.

Toutes les séances de la fenêtre de tendance et de suivi doivent exister et satisfaire les contrôles OHLCV. Doublons, nombres non finis, booléens et cours invalides créent des trous. Les sorties absentes ne sont pas remplacées. Les fenêtres d'un même titre/horizon ne chevauchent pas leurs rendements. Les horizons différents partagent des observations et ne doivent pas être agrégés pour prétendre multiplier les échantillons.

Le régime MASI utilise sa MM200 au signal. Les périodes 2023–2024 et depuis 2025 sont des séparations chronologiques descriptives, **pas** un test hors échantillon intact. Les exclusions se réconcilient avec les candidats dans l'export JSON.

Net = sortie × (1 − frais vente − glissement) / [entrée × (1 + frais achat + glissement)] − 1. Valeurs initiales : achat 1 %, vente 1 %, glissement 0 %. Le MASI de référence est brut. Sans dividendes, fiscalité ni simulation de carnet d'ordres. Fréquences sous 30 observations signalées insuffisantes ; même au-dessus, aucune probabilité prédictive ni inférence de significativité.

## Capital, suspension et survie

Frontières conservatrices : MNG 27 juillet 2026, SOT 5 mai 2026, CMT 16 septembre 2026. Copiées lors d'une consultation en lecture seule de `bvc_config.py` du principal, commit `eb744940faf3ddc27064819b41a190bfa7c69dfc`. Aucune seconde correction de split. Toute fenêtre traversant une frontière depuis le début des moyennes jusqu'à la sortie est exclue. Les titres actuellement suspendus sont exclus du replay entier : cela ajoute un biais de sélection explicitement reconnu, pas un portefeuille historique reconstitué.

L'univers courant de 80 titres introduit un biais de survie. Le MASI comprend un historique importé, initialement issu d'exports Investing.com puis complété par les archives du principal et les dernières séances CDG. Ces sources sont conservées dans `data/masi_history.json`, sans prétendre à trois années de données opérateur recertifiées. Les ajustements historiques des titres ne sont pas tous recertifiés. Aucun résultat n'est présenté comme une performance commercialisable.

## Risque et comparables

Risque : 253 dernières séances MASI, rendements de jours adjacents appariés exactement, minimum 60 observations. Volatilité annualisée sur 252 séances, covariance échantillonnale pour le bêta, corrélation de Pearson. Les trous ne sont jamais interpolés. La baisse maximale et l'écart de rendement exigent la fenêtre intégrale. Reprise récente : seulement les observations postérieures connues, avec garde minimale inchangée.

Comparables : même secteur, exercice, MAD, périmètre social/consolidé et norme identifiée IFRS/Maroc-CGNC/établissements de crédit ; état observable et au moins trois **autres** titres avec ratio calculable. Les normes non identifiées ne sont pas regroupées. PER et P/B non positifs exclus. La médiane exclut le titre observé ; le percentile croissant utilise la demi-pondération des égalités et ne constitue pas une recommandation. Le ROE conserve le dénominateur vérifié de clôture.

## Score prospectif

`data/score_archive/YYYY-MM-DD.json` contient la première observation réelle du jour de construction, heure avec fuseau, version du score, date du cours, entrées, empreinte SHA-256 et commits de provenance. Création exclusive : aucune réécriture lors des reconstructions ultérieures et aucun remplissage rétroactif. C'est une politique du générateur ; Git conserve l'historique, sans prétention à un stockage juridiquement inaltérable. Les journées historiques ne créent pas de fausses observations. Le suivi commence ici et ne fournit pas encore de validation prédictive.

Les constructions historiques excluent les bougies futures et les fondamentaux du snapshot courant si sa date est postérieure à l'analyse. Le principal reste entièrement indépendant et n'est jamais modifié.

Validation : tests de formules et d'appariement, trous et doublons, fuite temporelle, frontières, cohortes, immutabilité quotidienne, échappement HTML/JSON et interactions DOM. Les contrôles existants sur les comptes et les graphiques restent requis avant publication.
