# Reprise de publication du 19 octobre 2026

- Run horaire `39279228441` : 330 tests Python et 27 parcours Chromium locaux réussis ; déploiement effectué, puis échec du contrôle public des logos (attente de naturalWidth).
- Artefact public observé : publication `28c76ed7ae057f8a3b879921f48881be6ce1a172`, collecte à `2026-10-19T15:54:42.108655+00:00`, 61 observations provisoires du 19 octobre, dernière clôture validée du 16 octobre.
- Les 78 fichiers de logos publics ont été retéléchargés et leurs SHA-256 correspondent au catalogue ; ce contrôle ne prouve pas leur décodage par Chromium pendant le run échoué.
- Correction locale préparée : attendre la fin du chargement, puis identifier précisément les images non décodées. Le contrôle continue de refuser une image cassée.
- Vérifications locales de cette correction : syntaxe Node et `git diff --check` réussies. Pas de nouveau test navigateur revendiqué.
- Run programmé `39281298253` : statut `waiting`, environnement `github-pages` dans `pending_deployments`, `current_user_can_approve=false`, aucun reviewer retourné.
- Vérification suivante : l'attente s'est levée sans intervention et le run a échoué sur `test_new_conflicts_keep_both_values_without_mutating_history` : horloge figée au 17 octobre alors que la bougie utilisée est du 19. Aucun déploiement n'est maintenant en attente de validation. Ne pas interpréter une attente transitoire comme une validation humaine obligatoire.
- Correction : dater l'horloge du test après la clôture de la séance utilisée, sans modifier le refus des cotations futures ni les contrôles de conflit.
- Clôture du 19 octobre : les deux listes détaillées concordent exactement sur 61 titres, 113 956 939,12 MAD et 876 345 actions. L'agrégat annonce 62 titres, 113 956 983,12 MAD et 876 356 actions : écart de 44 MAD, 11 actions et un titre, non expliqué.
- Nouveau périmètre explicite `validated_title_lines` : publication des seules lignes recoupées, sans certifier ni modifier le total annoncé. Aucun titre manquant n'est inventé. Deux fournisseurs, leurs empreintes, la séance, le snapshot et chaque prix, montant et quantité doivent correspondre au rapport final.
- Une quantité absente, un prix divergent, une correction de volume en attente, une source indisponible ou une preuve incomplète continuent de bloquer ce périmètre. Les corrections automatiques restent soumises au rapprochement complet des agrégats.
- Les indicateurs globaux, le briefing et l'assistant conservent la réserve sur le total annoncé. Le journal conserve l'incident ouvert ; seule une réconciliation complète peut le résoudre.
- Tests ciblés : 4 cas de portée détaillée, dont 12 preuves altérées et 5 dégradations ; 19 cas du garde-volume et 24 cas JS de consultation des volumes réussis.
- Vérification complète locale : 334 tests Python réussis, contrôles JavaScript et Worker réussis, audits des exports et du rapprochement réussis avec réserve globale explicite. Typage statique, pourcentage de couverture, audit complet d'accessibilité et inférence LLM réelle non mesurés. Le contrôle navigateur après publication reste requis. Aucune modification du moteur principal.
