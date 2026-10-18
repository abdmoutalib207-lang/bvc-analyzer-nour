# Fiches et espace graphique Nour — 18 octobre 2026

## Références examinées

Les cinq captures transmises par l'utilisateur montrent la place du graphique,
les annotations personnelles, les rubriques d'une fiche, les graphiques de
comptes et les informations d'identité. Les chiffres visibles sur ces captures
ne sont pas importés comme faits Nour. Les objectifs d'analystes et les jauges
d'achat/vente ne sont pas reproduits sans jeu de données et méthode établis.

Le site public CDG Capital Bourse a été ouvert dans le navigateur le 18 octobre :
accueil puis `/Bourse/palmares`. Ont été observés le bandeau de séance, le cours
et le symbole, les rubriques Marché/Palmarès/Indices/Agenda, le choix de période,
la distinction central/blocs, les quantités et les montants. Le tableau du
palmarès a affiché « Aucun Résultat trouvé » dans cette session ; cette partie
n'est pas considérée comme un contrôle exhaustif des données CDG. La recherche
ALLIANCES n'a pas donné de résultat. Aucun accès client ni ordre n'a été utilisé.

La [page historique MASI d'Investing.com](https://www.investing.com/indices/masi-historical-data)
est accessible pour consultation. Elle comporte dates et OHLC et propose un
téléchargement, mais les volumes MASI observés sont vides. Sa notice exige
une autorisation écrite préalable pour l'usage, le stockage et la redistribution
de ses données. Aucun collecteur Investing, archivage de sa série ou ajout à
l'historique public n'est activé par ce lot.

L'extension d'historique reste donc à obtenir auprès d'une source autorisée.
Avant fusion : identifier l'instrument (ISIN), la devise, le calendrier, la base
ajustée/non ajustée, l'unité du volume, les opérations sur titres et les dates.
Rapprocher une période commune, conserver les divergences et ne jamais remplacer
un volume manquant par zéro. L'historique existant n'est pas plus profond du
seul fait que le nouveau graphique affiche une période supplémentaire.

## Comportement livré

- En-tête de valeur : cours, séance, fournisseur, profondeur et variation depuis
  la précédente clôture **disponible**, dont la date est affichée.
- Navigation par ancres : graphique, technique, comptes/ratios, risques,
  historique/sources. Le contenu reste lisible avec JavaScript désactivé.
- Graphique plus haut, axe des prix à droite, bougies par défaut, dates
  intermédiaires ; périodes 1M, 3M, 6M, 1A, 3A, Tout. Ces périodes utilisent
  les seules séances disponibles (21/63/126/252/756), sans interpolation.
- Présélections Prix, Tendance et Momentum ; indicateurs individuels dans
  « Indicateurs & réglages » ; thèmes clair/sombre pour l'espace graphique.
- Niveaux horizontaux et droites à deux points personnels, par clic/toucher ou
  au clavier (Entrée sur la séance sélectionnée). Échap annule l'outil en cours.
  Retirer le dernier tracé est immédiat. Au maximum 40 tracés par valeur.
- Type, indicateurs et thème conservés dans le stockage local de l'appareil ;
  tracés séparés par symbole, ancrés à des dates et prix. Le stockage bloqué ou
  malformé n'empêche pas l'affichage. Aucune synchronisation entre appareils.
- Export SVG du graphique et des panneaux visibles, styles et tracés inclus,
  avec métadonnées de période. Aucun script ni appel à une plateforme externe.
- Bouton « Lire le dossier avec Nour » : ouverture de l'assistant existant avec
  une question de synthèse complète sur la valeur.
- Graphiques financiers de comparatifs annuels uniquement si deux observations
  sont explicitement datées, de même périmètre, source, devise et unité avec
  pages PDF. L'absence de série est expliquée. Les semestres et leurs réserves
  restent dans leur propre section ; aucune histoire sur cinq ans n'est inventée.

Le module d'interface ne change ni les indicateurs canoniques, ni le score, ni
les chiffres comptables. Les tracés ne sont pas des observations du marché.
Le moteur principal reste inchangé.

## Validation

Contrôle local : 268 tests Python, contrôles JS/Worker et 425 contrôles
arithmétiques sans échec. Les nouveaux tests vérifient notamment les refus de
comparaison financière, les montants négatifs/nuls et les dates de l'en-tête.
Les essais Chromium de PR puis de publication doivent également vérifier les
présélections, thèmes, tracés par pointage, restauration après rafraîchissement,
export réel, navigation et absence de débordement aux trois largeurs.
Les captures de navigateur doivent être examinées avant intégration. Un audit
WCAG complet, des mesures INP et un appel réel au fournisseur LLM ne sont pas
effectués par ces contrôles.
