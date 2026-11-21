# Reprise de publication Nour — 21 novembre 2026

## Panne mesurée

Le fichier public `runtime.json` conservait l’édition du 13 novembre à 19:00,
run `43487973557`. Les réveils Actions continuaient mais les collectes de clôture
échouaient avant publication. Run vérifié : `44800704067`, job `136511927475`,
étape Build dashboard and briefing, exception `GlobalIntegrityError` dans run.py.

Le journal `data/market_integrity_log.json` enregistre les 16, 17, 19 et 20 novembre
le refus « Titre échangé CDG absent du référentiel Nour », symbole source `NRJ`.
Le contrôle strict et le repli par société refusaient tous deux un titre source
inconnu. Aucun code ni réglage du moteur principal n’a été modifié.

## Correction

Le contrôle strict de marché complet conserve son refus. La voie explicitement
partielle `isolated_issuer_lines` exclut les symboles sources non enregistrés,
les journalise avec leur séance et affiche une réserve de couverture. Elle ne
crée aucune société, aucun historique ou ratio pour un code inconnu et ne
certifie ni les agrégats ni une validation multisource globale. Les contrôles
par titre, seuil minimal, schémas et quarantaine des conflits sont conservés.
La liste `excluded_source_symbols` est exportée dans la synthèse d’intégrité.

## Preuves avant/après et contrôles

- Le test `test_unregistered_source_title_does_not_freeze_registered_titles`
  échouait avant correction sur `publication_safe=False`; il passe après.
- Le même test impose que le mode strict continue à refuser le titre inconnu,
  que les 80 enregistrements fictifs restent inchangés et que la preuve finale
  refuse une exclusion portant sur un titre effectivement publié.
- Un second scénario conserve les refus pour schéma invalide et moins de
  20 lignes saines, et couvre une source secondaire indisponible.
- Rejeu réel local : 67 observations CDG du 20 novembre intégrées ; 62 lignes
  contrôlées ; ADI, MNG, MSA, SMI et TGCC conservés en quarantaine selon les
  preuves et conflits existants. NRJ hors référentiel, explicitement exclu.
- Suite Python : 552 tests de la découverte initiale réussis ; les deux tests
  ajoutés ont également été exécutés séparément avec succès (553 cas uniques).
- La vérification JS a détecté un oracle trop rigide : l’assistant affichait
  correctement un « Cours publié » documenté sous réserve mais le test exigeait
  « Clôture : indisponible ». L’oracle distingue maintenant clôture validée,
  prix documenté sous réserve et absence de prix ; aucun calcul produit modifié.
- Construction locale complète réussie. Publication distante : résultat à
  compléter après exécution ; le contenu local ne prouve pas la mise en ligne.

## Limites

La correction restaure la continuité des publications partielles. Elle ne
constitue pas l’intégration documentaire de NRJ et ne remplit pas artificiellement
les séances manquantes pendant la panne. Les anciens incidents sont conservés.

Preuves publiques :
- https://abdmoutalib207-lang.github.io/bvc-analyzer-nour/runtime.json
- https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/44800704067
- https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/blob/main/data/market_integrity_log.json

## Contrôle navigateur de la première reprise

Le run 44907081075 a franchi construction et vérifications Python/JS puis
a refusé la publication : débordement de la page Sources à 375 pixels.
Les textes des panneaux autorisent désormais une coupure des longues chaînes,
sans masquer le contenu ni supprimer le défilement horizontal des tableaux.
L’assertion navigateur reste inchangée dans sa tolérance et inclut désormais
les éléments qui débordent pour rendre un prochain échec diagnosticable.
Le Chromium local ne pouvait pas démarrer dans cet environnement (socket
refusée) ; validation du rendu déléguée au workflow Chromium existant.
