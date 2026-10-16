# Présentation BI des explications financières

Lot limité à Nour. Le moteur principal reste en lecture seule.

Les fiches remplacent leurs anciennes cartes financières par une vue interactive :
filtre par thème, sélection d'un indicateur, lecture courte, formule et document
annuel. Les chiffres sont ceux du rapport Nour, sans recalcul JavaScript des
ratios ou du score. Les absences, pertes et suspensions de dette sont distinctes.
Les informations documentaires et réserves existantes restent accessibles.

Cette interface HTML s'inspire de la présentation de Power BI. Elle n'est pas
un rapport Microsoft Power BI, ne contient pas de fichier PBIX, ne demande pas
de compte Microsoft et n'ajoute ni service payant ni fournisseur d'IA.
L'intégration d'un véritable rapport reste possible à partir d'un lien
Microsoft autorisé ; aucun lien n'a été fourni pour ce lot.

Un graphique semestriel compare uniquement deux RNPG explicitement datés au
30 juin de deux années consécutives, en MAD, avec périmètre comptable renseigné.
Les signes et montants sont conservés ; les barres partagent un axe à zéro.
L'absence de métadonnées explicites laisse le graphique absent. Au jeu de
données du lot, JET seul remplit ces conditions. Aucun semestre n'est annualisé.

Sans JavaScript, les chiffres et explications restent dans le HTML ; les
explications s'ouvrent par leurs résumés natifs. Avec JavaScript, un seul
commentaire est présenté à la fois. Les boutons sont utilisables au clavier et
les filtres conservent la sélection lorsqu'elle reste visible.

Vérification : `python tools/verify_nour.py --build --asof 2026-10-16`, puis
`node tools/test_assistant_browser.cjs` sur serveur local et URL réellement
publiée. Les parcours contrôlent filtres, clavier, absence de débordement à
375/768/1440 px et conservation des chiffres affichés.
