# Dette : rapprochement primaire du 13 octobre 2026

Nour uniquement ; moteur principal non modifié. Reprise après la PR #3.
Rejeu : `python tools/reconcile_debt_oct13.py`. Semestres et autres titres préservés.

## Managem

Rapport AMMC : https://www.ammc.ma/sites/default/files/Managem_RFA_2025.pdf
SHA-256 : `c55a5149908f04488db23af43ff3e952dbeb72126a7ec00836f7b7452f648506`.
Pages PDF 10, 68, 86 rendues et contrôlées. Elles correspondent aux pages
imprimées 18–19, 134–135, 170–171 (deux pages imprimées par page PDF).

La p.68 définit l'indicateur société comme incluant MtM, locations et comptes
courants envers les sociétés hors intégration globale. Le graphique montre
**33 MMAD** de CCA ; il ne s'agit pas d'un solde inventé pour fermer l'écart.
La p.86 permet le calcul hors dérivés, mais locations déjà incluses :

- dette : 6 751,2 + 2 000 + 85,1 + 6 487,2 = 15 323,5 MMAD ;
- cash : 4 390,3 MMAD ; nette financière calculée : 10 933,2 MMAD ;
- dérivés de couverture passifs : 1 707,9 MMAD ; CCA : 33 MMAD ;
- pont : 10 933,2 + 1 707,9 + 33 = 12 674,1 MMAD ;
- indicateur société : **12 674,4 MMAD** dans le commentaire, 12 674 arrondis au graphique ;
- résidu : −0,3 MMAD, compatible avec les arrondis. Aucun ajustement de 0,3
  n'est ajouté à une composante. Tolérance absolue du pont : 1 MMAD maximum,
  jamais les 2 % du contrôle préliminaire.

Les deux définitions restent distinctes. Dette nette financière / EBE annuel
2025 : **1,83**. EBE publié 5 982 MMAD, PDF p.10/imprimée p.19 ; ce n'est pas
un EBITDA IFRS recalculé. Aucun effet sur le score, aucune annualisation du S1.
Les sources du pont doivent avoir unités, période, base, hash, URL et statut de
contrôle primaire cohérents. Sans ce contrat ou si le pont échoue, suspension.

ROE moyen séparé : RNPG 3 002 / moyenne fonds propres groupe 10 687,8 et
11 478,3 = **27,09 %**. La note garde le ROE de clôture.

## Mutandis

Rapport AMMC : https://www.ammc.ma/sites/default/files/Mutandis_RFA_2025.pdf
SHA-256 : `3bf8f03a9f054642164ac8c2b1eead5ef4729411b6e3fd89dfa2bc963e46f342`.
Pages PDF 40, 54, 62 contrôlées : imprimées 78–79, 106–107, 122–123.
Dette bilan 1 248,950 MMAD, note 1 248,949 (arrondi de 1 KMAD). Cash incluant
VMP 259,728. Nette calculée 989,222 versus « dette nette bancaire » 828 :
pas de pont complet trouvé. Les locations, obligations et intérêts ne sont
pas retirés arbitrairement. Dette et multiple restent suspendus.
ROE moyen ajouté séparément : 126,161 / moyenne 1 562,845 et 1 551,387 = **8,10 %**.
Les colonnes 2024/2025 sont à nouveau vérifiées ; fonds propres part groupe
distincts du total consolidé. La note garde le ROE de clôture.

## Alliances

Rapport AMMC : https://www.ammc.ma/sites/default/files/ADI_RFA_2025.pdf
SHA-256 : `0d076ef448b6228ec8ff2ad60c2368044382d545ef84f51afb133636e4c538bc`.
Pages PDF/imprimées 17, 21, 27 vérifiées. 2 114,079 − 752,590 = 1 361,489
MMAD contre 1 303 publiés. Le crédit-bail vaut 60,916 ; sa simple soustraction
ne prouve pas la définition retenue par la société. Aucun pont confirmé :
suspension conservée. Les anciennes notes affirmant que la valeur calculée
était publiée sont rectifiées.

## Limites

Pages sélectionnées seulement, pas certification des rapports complets ni des
comptes semestriels. Comptes annuels 2025 étiquetés comme tels, pas indicateurs
de dette actuelle 2026. Couverture documentaire inchangée. Le pont est une
règle de validation générale, sans exception codée pour le symbole MNG.
