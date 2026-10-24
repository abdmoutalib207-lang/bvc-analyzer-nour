# Réponse technique à l'audit externe du 23 octobre

Périmètre : Nour uniquement. Le rapport externe est une observation datée,
pas une mesure de la version publiée après la PR 29. Ses réserves sur la
continuité et la couverture documentaire sont retenues ; les formules ne
sont pas déclarées certifiées par le passage des tests.

| Point | Contrôle et traitement |
| --- | --- |
| C-1 Continuité | Les pannes observées sont réelles. Leur cause n'était pas uniquement la fraîcheur : les tests supposaient des titres toujours sains, y compris dans le navigateur. PR 28 et 29 fusionnées, publication 40039309745 réussie et contrôlée sur le site public. Le relais GitHub et le watchdog sont actifs ; un ordonnanceur externe indépendant n'a pas été déployé. La ponctualité des prochaines séances reste à constater. |
| C-2 Clôture | Le lien d'édition programmée pouvait rester au 20 octobre. Une synthèse `cloture.json/html` était pourtant déjà reconstruite à chaque passage avec `last_closed`. Les liens et le manifeste pointent désormais vers cette synthèse datée, sans réécrire les éditions historiques ni inventer une exécution de 16 h. |
| C-3 Incidents | Un incident historique ouvert n'est pas nécessairement un blocage du marché courant. Aucun incident n'est résolu par ancienneté ; le rapprochement de la même séance reste requis. La revue des incidents anciens reste à compléter. |
| C-4 Variation | Date de base affichée directement sous chaque pourcentage, même récent. La colonne de référence reprend le cours et la date réellement utilisés ; hors séance, elle affichait auparavant la dernière clôture au lieu de la précédente utilisée dans le calcul. Aucun rendement n'est changé. |
| C-5 Score | Les seuils descriptifs et leur absence de validation prédictive sont conservés. Aucune rampe ni calibration introduite pour améliorer une note d'audit. |
| C-6 Archive | Le hash ne prouve pas une lecture ni une certification. L'archivage prospectif des faits connus à chaque date reste un chantier ; aucune disponibilité historique n'est reconstruite artificiellement. |
| C-7 ROE | Les variantes clôture/moyenne restent distinctes. Aucun calcul modifié dans ce lot. |
| G-9 Navigateur | La QA existante couvre déjà accueil, fiches, graphiques, laboratoire, sources et interactions, à trois largeurs. Le workflow 40039309745 a passé 36 parcours normaux, 36 avec ADI en quarantaine et 36 publics ; elle ne se limite pas à l'assistant. |

Les 4 184 vérifications sont techniques/statistiques, séparées des 565
financières et des 59 sectorielles de cette publication. Ces nombres ne
mesurent pas l'exhaustivité de la collecte documentaire. Le chantier des
données métier Managem et des autres sociétés reste distinct et nécessaire.

Régressions ajoutées : variation PPM 1395 / 1480, base du 28 septembre
visible à côté du pourcentage ; référence de la précédente clôture hors
séance ; lien vers la dernière synthèse malgré une édition de clôture
ancienne ou absente ; archives inchangées. Les références de mise en service
de ce lot sont consignées dans sa PR après validation.
