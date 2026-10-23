# Validation des mises à jour avec titres en quarantaine

Le premier passage après la PR 28, run `40010039842`, a été refusé avant
publication : 5 échecs et 1 erreur dans la suite de 431 tests. Le site antérieur
est resté servi. La construction et ses audits avaient traité les 80 titres,
avec ADH, ADI, IAM, MNG et STK isolés ; aucun de leurs chiffres litigieux n'était
accepté comme valide.

Les échecs portaient sur les attentes des tests :

- Les injections d'erreurs numériques et de suspension supposaient qu'ADI
  n'était pas déjà en quarantaine. Leur base numérique contrôlée est maintenant
  isolée des quarantaines de source, uniquement dans la fixture des tests.
  Le fichier de production n'est jamais modifié par cette préparation.
- Le test indépendant des 80 titres exigeait tous les nombres malgré les
  suspensions. Il vérifie désormais les 80 identités, l'absence de chiffres
  pour les titres bloqués, l'arithmétique stricte des titres sains et la
  politique de mise en indisponibilité de la production. Un chiffre erroné
  réintroduit dans un indicateur bloqué reste rejeté par les tests existants.
- Les tests CSV/graphiques comparaient les exports à toute l'entrée brute,
  y compris la séance en conflit déjà exclue par le produit. Les attentes
  suivent maintenant le contrat : séances antérieures admissibles, séance
  litigieuse absente, avertissements cohérents avec les lignes exportées.

Un test supplémentaire injecte cinq quarantaines de source et exige une
arithmétique inchangée pour les titres sains ; un nombre erroné réintroduit
dans un indicateur suspendu doit toujours échouer. Un autre injecte une quarantaine ADI, vérifie son absence des
CSV et graphiques pour la séance litigieuse, conserve son cours/indicateur
indisponible, puis compare exactement les 79 autres CSV avec leur base saine.
Aucun test n'est supprimé et aucun oracle financier n'est affaibli. Cette PR
ne change pas les calculs, les scores ni les décisions de quarantaine.

Les artefacts d'échec incluent désormais le snapshot, le contexte de marché et
le cache de dernier état sain, en plus du rapport, pour reproduire exactement
un défaut sur les données collectées. Les références des validations et du
déploiement réel seront ajoutées à la PR.

## Préparation du navigateur

Le run 40006810299 a attendu plus de dix minutes des paquets APT de polices
complémentaires, tandis que ses bibliothèques Chromium, Liberation et Noto Emoji
étaient déjà installées. La revue et la publication installent maintenant
uniquement le headless shell associé à Playwright 1.62.1, moteur déjà utilisé
par les tests headless existants. Les 36 parcours et les contrôles sur le site
servi restent obligatoires ; une bibliothèque réellement manquante fait échouer
le lancement du navigateur. Aucun contrôle n'est placé en continue-on-error.
Référence : https://playwright.dev/docs/browsers (Chromium headless shell).

## Contrat navigateur en mode dégradé

La revue finale a également relevé des appels `null.toLocaleString` dans les
assertions de cours/PER/MM50/RSI/Bollinger/bêta du navigateur. Ces valeurs
canoniques peuvent légitimement être absentes. Les assertions exigent maintenant
exactement le tiret du cours et « indisponible » pour l'indicateur concerné ;
les nombres disponibles restent comparés à leur valeur canonique, sans zéro
substitué. Les réponses combinées sont contrôlées avec leur libellé propre.

`tools/test_quarantined_browser.py` fabrique deux sites exclusivement temporaires
à partir du même univers synthétique de tests : base saine, puis volume ADI
contradictoire. Il utilise les calculateurs et contrôles de publication réels,
exige 80 fiches, ADI sans cours/PER/MM50 valide et l'égalité exacte des techniques,
fondamentaux, scores et 79 CSV sains. Il exécute ensuite les 36 parcours Chromium
sur le site temporaire dégradé. Aucun fichier simulé ne rejoint `data/`, `web/`,
un commit de données ou GitHub Pages. La revue et chaque publication exécutent
ce stress test en plus des 36 parcours normaux ; leurs échecs restent bloquants.
