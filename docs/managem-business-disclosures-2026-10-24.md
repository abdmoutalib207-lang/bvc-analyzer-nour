# Managem : chiffres métier vérifiés le 24 octobre 2026

Le dossier externe est une liste de pistes, pas une preuve suffisante pour importer ses interprétations. Ce lot relève 74 chiffres primaires dans quatre documents : RFA 2024, RFA 2025, RFS S1 2025 et RFS S1 2026. Les PDF ont été téléchargés, hachés et les pages utilisées rendues puis lues visuellement. Le catalogue versionné est `knowledge/business_disclosures/MNG.json` : unités originales, valeurs signées, périodes, périmètres, pages PDF et imprimées, définitions et réserves.

## Sources lues

| Document | Pages PDF retenues | Pages imprimées |
| --- | --- | --- |
| RFA 2025 (site Managem) | 66, 67, 88, 96 | 130, 132, 175, 190–191 |
| RFA 2024 (AMMC) | 62, 84 | 122, 167 |
| RFS S1 2025 (site Managem) | 15 | 15 |
| RFS S1 2026 (site Managem) | 15 | 15 |

Les RFA sont des doubles pages : « page 65 » du dossier externe ne localise pas correctement le tableau de production dans le PDF téléchargé. Le lien généré cible la vraie page PDF 66. Les empreintes complètes et URL sont dans le catalogue ; le RFA 2025 porte le même hash que les faits financiers préexistants (`c55a5149…48506`).

## Différences corrigées ou conservées comme réserves

- S1 2025 : acquisition d'immobilisations −2 885,5 MDH, flux d'investissement −2 976,4 MDH, variation totale de trésorerie −567,5 MDH. Les trois lignes sont distinctes et lisibles page 15.
- S1 2026 : acquisition d'immobilisations −1 731 MDH, flux opérationnel +4 827 MDH, flux d'investissement −2 136 MDH, variation de trésorerie +2 259 MDH. Précision au million conservée.
- RFA 2025 : TFT −5 950 MDH ; le chiffre de gestion est 5 878,2 MDH. RFA 2024 : TFT −7 254,4 MDH ; gestion 7 224,2 MDH. Pas d'explication causale inventée de l'écart.
- Production cuivre 2025 : 110 721 TC, soit +20 % dans le tableau, tandis que le commentaire de la même page dit +41 %. Quantités conservées, contradiction visible.
- Or : total publié 6 717 kg en 2025 contre 6 716 kg en additionnant les filiales affichées ; 5 326 contre 5 327 en 2024. Pas d'ajustement du total publié.
- Les cellules vides (CMO 2025, Tizert/Boto 2024) ne deviennent pas zéro.
- Note 6 du RFA 2025 : matières 2024 −4 301,0 MDH et total achats −4 301,1 MDH. Ces deux lignes sont conservées séparément.
- Charges IFRS : valeurs négatives publiées conservées, jamais étiquetées AISC ou coût unitaire minier.
- Quantités vendues : le seul libellé « t » ne prouve pas qu'il s'agit de métal contenu. Les affirmations du dossier externe restent non intégrées.
- LAMIKAL : en-tête ambigu dans le tableau 2024, non intégré dans ce lot. AISC d'une filiale ou d'un projet : ne pas affecter au groupe.

## Intégration et temporalité

`attach_business_facts` ajoute les pièces métier en mémoire de construction, sans modifier `faits_reference.json` ni les faits financiers du score. Une seule ligne annuelle du TFT fournit le CAPEX positif descriptif de 2025, avec normalisation explicite du signe et montant original −5 950. Aucun coût minier unitaire n'est fabriqué.

Chaque rubrique possède ses propres périodes : dernier annuel de production 2025, flux semestriels jusqu'au S1 2026. Les anciennes périodes sont dans des panneaux dépliables. Les liens pointent vers la page PDF réelle. Le relevé est disponible dans Nour à compter du 24/10/2026 ; aucun historique point-in-time antérieur n'est revendiqué ni rempli rétroactivement.

L'assistant local copie ces chiffres du rapport et répond aux questions de production, CAPEX, charges et investissements avec leurs réserves. La couche IA externe n'est pas modifiée dans ce lot : ne pas revendiquer une extension de son contexte documentaire sans déploiement séparé.

## Vérification

Cinq tests dédiés couvrent les valeurs, dimensions, cellules vides, preuves invalides, temporalité, immutabilité, séparation de coût et rendu sûr. Des questions locales vérifient notamment cuivre 2025, CAPEX S1 2025, CAPEX 2024, AISC non vérifié et année absente. Le parcours navigateur MNG contrôle les 74 lignes, l'ouverture des périodes et des sources, la divergence +20/+41 et le débordement à 375, 768 et 1440 px.

Comparaison locale initiale au rapport publié du même 24/10 : scores, techniques et fondamentaux identiques sur 80/80 titres. La validation finale CI, la publication et la vérification des pages servies restent à confirmer avant de les annoncer.
