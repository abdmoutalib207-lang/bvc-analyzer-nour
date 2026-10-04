"""Accessible chart navigation shared by issuer pages and the MASI."""


def navigation():
    return ('<div class="chart-navigation" role="group" aria-label="Explorer le graphique">'
            '<button type="button" data-chart-nav="older" aria-label="Séances précédentes">←</button>'
            '<button type="button" data-chart-nav="newer" aria-label="Séances suivantes">→</button>'
            '<button type="button" data-chart-nav="zoom-in" aria-label="Zoom avant">+</button>'
            '<button type="button" data-chart-nav="zoom-out" aria-label="Zoom arrière">−</button>'
            '<button type="button" data-chart-nav="latest">Dernière séance</button>'
            '<button type="button" data-chart-nav="reset">Réinitialiser</button>'
            '<button type="button" data-chart-compare aria-pressed="false">Comparer deux dates</button>'
            '<button type="button" data-chart-fullscreen aria-pressed="false">Plein écran</button>'
            '<button type="button" data-chart-help-toggle aria-expanded="false">Aide</button></div>')


def explorer_footer():
    return ('<div class="chart-measure" data-chart-measure role="status" hidden></div>'
            '<div class="chart-overview" data-chart-overview aria-label="Vue d’ensemble de l’historique"></div>'
            '<div class="chart-range-controls" data-chart-range-controls hidden>'
            '<label>Début <input type="range" data-chart-range-start aria-label="Début de la période" step="1"></label>'
            '<label>Fin <input type="range" data-chart-range-end aria-label="Fin de la période" step="1"></label></div>'
            '<p class="chart-gesture-hint">Glisser pour parcourir · molette ou pincement pour zoomer · toucher une séance pour la fixer. 1M / 3M / 1A : 21 / 63 / 252 séances disponibles.</p>'
            '<div class="chart-help" data-chart-help hidden><p>La fenêtre dans la vue d’ensemble se déplace par glisser ; ses poignées changent la période. Les curseurs Début et Fin fonctionnent aussi au clavier.</p>'
            '<p>Sur le graphique : ← / → lisent les séances, Maj + ← / → déplacent la période, + / − zooment. Entrée fixe la séance ou choisit une date de comparaison. Échap libère le curseur et efface la comparaison. Maj + molette parcourt l’historique.</p>'
            '<p>Sur mobile, glissez horizontalement ou pincez à deux doigts. Le défilement vertical de la page reste disponible.</p></div>')
