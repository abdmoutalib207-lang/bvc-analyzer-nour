# Macro et international Nour

Implémentation autonome, après consultation en lecture seule du moteur principal
au commit `f97b4679da8b836f15857a5b1c8a8873da1db278` :
`pipeline/marches_mondiaux.py`, `pipeline/fetch_news.py` et `terminal.src.html`.
Aucune écriture dans le moteur principal et aucun appel de son moteur de score.

## Marchés mondiaux

Les 12 mêmes identifiants sont interrogés directement sur le scanner public
TradingView : S&P 500, Dow Jones, CAC 40, Nikkei 225, USD/MAD, EUR/MAD, VIX,
indice dollar, futures or, Brent, cuivre et charbon API2.
Nour valide l'identifiant, la valeur finie, la devise attendue et la date source.
La variation vient du champ `change`, sans calcul entre deux collectes Nour.
Les cotations ne sont pas simultanées. Le mode de diffusion déclaré par la source
est affiché ; « streaming » ne rend pas le site statique temps réel.
Les échecs conservent les observations et leurs dates originales, avec mention
d'archive. Les contradictions au même horodatage et régressions sont écartées.

Unités des futures : or USD/once troy, Brent USD/baril, cuivre USD/livre,
charbon USD/tonne. Références de contrats :

- https://www.cmegroup.com/markets/metals/precious/gold.html
- https://www.ice.com/products/219/Brent-Crude-Futures
- https://www.cmegroup.com/trading/metals/files/copper-futures-and-options.pdf
- https://www.ice.com/products/243/Rotterdam-Coal-Futures

Ce ne sont pas des prix spot ; les devises ne sont pas des fixings BAM.

## Radar

AMMC et Le Matin sont préservés. Quinze flux macro/international sont ajoutés :
relais Google News BAM/Finances Maroc, HCP, Fed et BCE (institutionnels directs),
presse francophone Fed/BCE, inflation US/Europe, Proche-Orient, partenaires
européens, OilPrice, Mining.com, RFI, France 24 et Financial Afrik.
On stocke uniquement titre, URL et métadonnées datées, pas les corps d'articles.
Fenêtre macro : 7 jours pour la presse, 30 pour les institutions ; collecte
limitée à 12 liens par flux. Les publications d'émetteurs ont une réserve dans
le radar global, plafonné à 300. Les références financières restent intactes.
Flux HCP direct documenté : https://www.hcp.ma/feeds/ ; Fed :
https://www.federalreserve.gov/feeds/feeds.htm ; BCE :
https://www.ecb.europa.eu/home/html/rss.en.html .

Le thème est celui du flux, le périmètre géographique est distinct. Une mention
explicite du Maroc ou un émetteur identifié établit MAROC ; sinon le périmètre
du flux est utilisé, ou UNKNOWN. Cette recherche lexicale est une aide de
navigation, jamais un NLP décisionnel, sentiment ou recommandation.
S1 signifie présence officielle (AMMC/HCP/Fed/BCE), non validation chiffrée. Un relais Google News
reste S2 même s'il concerne une institution. Dates de publication obligatoires,
pas de date de collecte substituée. Chaque flux expose son état et ses erreurs.

## Point dans le temps et limites

Les briefings ne retiennent aucune observation internationale du lendemain de
leur date de référence. Les cotations après la clôture BVC du même jour sont
identifiées par leur horodatage et ne sont jamais présentées comme sa cause.
Les anciennes éditions archivées restent telles quelles ; pas de reconstruction
fictive d'un contexte international non archivé.
Les nouvelles données n'entrent pas dans `build_report` comme facteurs :
les résultats techniques/fondamentaux et scores sont identiques avec ou sans
ce radar (test de non-régression). Aucun chiffre de PIB, inflation ou taux
directeur n'est extrait automatiquement des titres ; aucune prévision du marché.
