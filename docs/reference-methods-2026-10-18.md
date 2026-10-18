# Références spécialisées et consolidation Nour — 18 octobre 2026

Le lot utilise quatre références pour améliorer la consultation et les méthodes de Nour.
Il ne remplace pas les contrôles documentaires par les valeurs affichées chez un fournisseur.
Le moteur principal n'est pas modifié.

## Ce qui a été effectivement observé

| Référence | Preuve | Conclusion et limite |
|---|---|---|
| IDBourse | [REA 39094926861](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/39094926861) : ADI, ATW, DATA+, comparateur, simulateur | Les cinq pages demandent une connexion. L'accueil montre les destinations ; aucune donnée membre ni formule interne n'est validée. Le simulateur était capturé comme document mais montre lui aussi une invitation à se connecter ; le détecteur est corrigé. |
| TradingView | Même exécution, puis [REA 39095134593](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/39095134593) | Graphique ADI accessible. REA a réellement ouvert le sélecteur d'indicateurs : recherche, indicateurs intégrés, réglages et panneaux constituent des références fonctionnelles. Cela ne prouve pas les calculs d'un serveur distant. |
| Yuna | Pages publiques de présentation, politique et exemple comparatif ; [REA 39095607340](https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/39095607340) | Le discours public met en avant niveau d'explication, spécialisation marocaine et citations. La capture REA montre une vérification Vercel échouée (Code 21), pas une conversation Yuna. Le statut d'accès reste limité. |
| EcoFinance / EcoIA | Accueil capturé dans 39095134593 et page officielle EcoIA consultée | Le parcours déclaré est recherche documentaire, vérification, calcul dédié, réponse sourcée. L'accueil promotionnel n'est pas un essai de l'application mobile ou du modèle. La mention « bientôt disponible » du site ne réfute pas le test réel transmis par l'utilisateur. |

Les observations complètes, leurs limites et les URL sont indexées dans
`knowledge/reference-review-2026-10-18.json`. Les artefacts REA conservent les
images et les observations pendant sept jours ; les empreintes des ZIP ont été
contrôlées au téléchargement. Les documents externes ne sont pas copiés dans le
corpus de chiffres canoniques ni utilisés comme instructions pour le modèle.

## Améliorations de données réellement apportées

L'accueil contient un explorateur repliable des 80 titres. Recherche, secteur,
présence ou absence de ratios, PER maximum et ROE minimum filtrent les résultats
déjà calculés. Le CSV `fondamentaux.csv` reprend les dates de cours, exercice,
période, devise, périmètre, ratios, validation, réserves et document source.
Une cellule absente reste vide en CSV et « Indisponible » à l'écran ; zéro et
résultat négatif restent des observations. Les semestres ne sont pas annualisés.

Le lot n'ajoute aucun chiffre comptable extérieur. Au 18 octobre : 50 BPA et
54 ROE disponibles. Les pièces annuelles DIS, DLM et IBM et les autres
rapprochements de l'[inventaire complet](fundamental-coverage-2026-10-18.md)
restent à traiter. Les comptes ne deviennent pas certifiés par cet explorateur.

## Contrat technique

Le graphique ajoute MM200, EMA20, EMA50 et ATR Wilder dans un panneau séparé.
Les méthodes sont lisibles sous le graphique. Le MACD, le RSI, Bollinger et les
moyennes existantes conservent leur définition.

| Mesure | Définition Nour |
|---|---|
| MM20/50/200 | Moyenne des dernières clôtures disponibles sur la période entière requise |
| EMA20/50 | Amorce moyenne simple ; alpha = 2 / (période + 1) |
| RSI14 | Moyennes des 14 premières variations puis lissage Wilder ; convention historique 50 pour une série plate |
| MACD12/26/9 | EMA12 − EMA26 ; signal EMA9 amorcé sur les neuf premiers MACD disponibles ; histogramme = MACD − signal |
| Bollinger20/2 | MM20 ± deux écarts-types de population, dénominateur 20 |
| ATR14 historique | `atr14` reste la moyenne simple des 14 amplitudes vraies avec clôture précédente |
| ATR14 Wilder | Nouveau champ `atr14_wilder` : première amplitude haut−bas, moyenne initiale de 14 amplitudes puis (13 × précédent + amplitude) / 14 |

Les valeurs sont calculées avant découpe de la fenêtre de zoom. Aucun trou n'est
interpolé. Une reprise documentée réinitialise la série. Les cours sont non
ajustés : profondeur, amorce, ajustements, horaires, séances et fournisseur doivent
être rapprochés avant de comparer à TradingView. Une identité numérique avec sa
série n'est pas revendiquée.

Références techniques officielles consultées :

- [RSI](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/).
- [ATR et lissage RMA par défaut](https://www.tradingview.com/support/solutions/43000501823-average-true-range-atr/).
- [Moyennes et amorce EMA](https://www.tradingview.com/support/solutions/43000502589-moving-averages/).
- [Bollinger](https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/).
- [MACD](https://www.tradingview.com/support/solutions/43000502344-moving-average-convergence-divergence-macd-indicator/).

Les implémentations Python et navigateur restent distinctes pour leurs deux
environnements ; un contrat commun est vérifié sur les 80 historiques, les seuils
de démarrage, les reprises et l'absence de fuite de valeurs futures. Le score et
toutes les valeurs techniques antérieures ont été comparés au relevé précédent
sur les mêmes données : aucun changement. L'ATR Wilder ne remplace pas
silencieusement l'ancien ATR simple et n'entre pas dans le score.

## Assistant

Une demande de synthèse complète d'un titre est traitée avant le routeur de
briefing. Elle présente marché, technique, comptes annuels, dernière publication,
risques historiques, lecture métier, réserves et liens vers les pages PDF. Les
réserves sont intégrales ; un total consolidé n'est pas substitué au RNPG.

Le mode déterministe répond sans fournisseur IA. Le contexte transmis au modèle
facultatif contient les nouvelles valeurs calculées et les règles enrichies ;
aucune écriture ni capacité de calcul libre ne lui est ajoutée. Une demande TTM
ou prévisionnelle ne reçoit pas un ratio annuel à sa place. Les EMA20/50 et les
deux ATR sont interrogeables explicitement. Les dates historiques continuent de
refuser la substitution d'une valeur actuelle à un indicateur absent.

Les références Yuna et EcoIA inspirent la lisibilité et la structure, pas une
prétendue copie de leur modèle ou de leur base. Leur conversation authentifiée,
ainsi qu'une nouvelle réponse réelle du fournisseur Nour, ne sont pas mesurées
par les tests de ce lot.

## Validation

- `python tools/verify_nour.py --build --asof 2026-10-18` : 265 tests Python,
  contrôles JS/Worker, 425 contrôles arithmétiques sans échec.
- Tests spécifiques : parité de 11 métriques sur 80 historiques, absence de fuite
  future, amorce et distinction ATR simple/Wilder, CSV fidèle et non mutabilité.
- Tests assistant : 80 dossiers complets conservant toutes les réserves,
  EMA20/EMA50, ATR distincts et refus de substitution TTM/prévisionnel.
- Le contrôle Chromium de la PR et de la publication doit réussir avec les
  nouveaux filtres, commandes graphiques et tailles mobile/desktop. Une
  construction locale ne prouve pas le déploiement.

## Suite nécessitant un accès supplémentaire

Pour étudier les données membres et les méthodes internes exposées par IDBourse,
ouvrir une session utilisateur autorisée et examiner quelques cas rapprochés :
ADI/ADH (immobilier), ATW/CFG (banques), un assureur et un industriel.
Faire correspondre les émetteurs par ISIN et référentiel contrôlé : les codes courts des plateformes peuvent différer. Relever
période, date de cours, RNPG ou total, dénominateur du BPA, capital, norme et
document source avant tout rapprochement. Aucun mot de passe n'a sa place dans
un dépôt ou un workflow d'observation public.
