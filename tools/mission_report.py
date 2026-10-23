"""Generate a dated, reviewable 80-issuer inventory from the validated output."""
from collections import Counter
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nour.sector_view import coverage_report
from nour.sector_calculators import RULES,REFERENCES,VERSION,formula_text


def main():
    report=json.loads((ROOT/'web/report.json').read_text())
    coverage=coverage_report(report);day=coverage['analysis_date']
    states=Counter(r['verification_status'] for r in coverage['issuers'])
    available=sum(m['value'] is not None for r in report['results'] for m in r['sector_indicators']['metrics'].values())
    kpis=sum(m['value'] is not None for r in report['results'] for m in r['sector_indicators'].get('published_kpis',{}).values())
    text=f'''# Rapport d’exécution Nour — {day}

Périmètre exclusif : `abdmoutalib207-lang/bvc-analyzer-nour`. Le moteur principal est en lecture seule. Ce document décrit le code et l’inventaire calculé ; les références de PR, de CI et la preuve du déploiement sont fournies dans le compte rendu de livraison. Un fichier local ou un manifeste préparé n’atteste pas un déploiement.

## 1. Constats dans le code

- `run.py` levait une exception globale sur une divergence financière, statistique ou sectorielle et écrivait les pages directement dans `web/`.
- Les étapes d’analyse, de recherche et de rendu n’avaient pas toutes une frontière d’erreur par société. Les collisions de lignes source pouvaient interrompre la collecte globale.
- Les méthodes métier étaient principalement des grilles de recherche ; elles ne constituaient pas des calculateurs sectoriels.
- Les horloges de collecte et de cotation existaient, mais les contrôles et validations propres à chaque titre n’étaient pas tous exportés. Une heure inconnue ne doit pas être reconstruite.
- Les onze horaires Casablanca existaient ; aucun rattrapage borné des éditions manquées n’était exécuté par un watchdog indépendant.
- Le contrôle navigateur pouvait rendre toute une publication rouge pour un seul logo non décodé, bien que le sigle de secours fonctionne. Les contrôles de données et de sécurité SVG restent bloquants ; un problème de logo exige maintenant un sigle lisible et un journal de réserve.

La PR24 de correction statistique et la PR25 de rapprochement financier sont conservées. Les recalculs indépendants ne sont pas supprimés : ils restent les oracles numériques.

## 2. Changements effectifs

`resilience.py`, `local_market.py`, `transactions.py`, `diagnostics.py` et les étapes appelantes isolent les exceptions et divergences locales. Les valeurs concernées deviennent absentes avec une raison ; une valeur numérique erronée n’est jamais acceptée parce qu’un drapeau prétend la mettre en quarantaine. Les identités, la structure globale, les preuves de marché et la sécurité gardent un refus global.

Les générations HTML/JSON sont préparées hors du site courant, contrôlées puis échangées par `renameat2(RENAME_EXCHANGE)`. Une interruption avant cet échange conserve les anciens fichiers. Les archives d’édition, de scores et d’états sains sont enregistrées après la construction complète. GitHub ne sauvegarde/publie les nouvelles pages qu’après les vérifications Python, JavaScript et Chromium. Pages conserve l’ancien déploiement si le nouveau n’est pas accepté.

Une panne de source ne crée aucune nouvelle preuve. La dernière preuve positive peut être conservée uniquement pour le fichier exact (SHA-256), la même séance et les mêmes valeurs, après revalidation de son contrat. Un conflit historique non rapproché reste en investigation ; il n’est pas effacé par la réussite d’une collecte ultérieure.

## 3. Fondamentaux historiques opérationnels

Version `nour-fundamentals-v6`, inchangée : bénéfice groupe/social explicitement identifié ; PNB ; BPA ; valeur comptable par action ; PER ; P/B ; ROE sur capitaux propres de clôture ; ROE sur capitaux propres moyens lorsque les deux dates sont documentées ; croissance CA/PNB sur périodes compatibles ; rendement du dividende ; dette financière nette stricte ; dette nette/EBE selon définition historique conservée. Ce dernier ratio n’est pas un EBITDA IFRS universel et est exclu des banques/assureurs.

Formules : BPA = résultat attribuable / actions documentées pertinentes ; PER = cours valide / BPA positif ; P/B = cours valide / valeur comptable positive ; ROE de clôture = résultat attribuable / capitaux propres attribuables positifs ; ROE moyen = résultat / moyenne des capitaux propres d’ouverture et de clôture positifs ; dette nette = dette financière − trésorerie active rapprochée. Aucun RNPG n’est remplacé par le résultat consolidé total, aucun semestre n’est annualisé, aucune absence n’est changée en zéro.

## 4. Nouvelles méthodes réellement implémentées

Version `{VERSION}` : {len(RULES)} formules explicites ; {available} sorties numériques disponibles dans ce snapshot, plus {kpis} indicateurs métier directement documentés. La sélection dépend du métier ; les banques, assurances, crédits et holdings ne reçoivent pas la grille industrielle. Les définitions bancaires, non-vie, EPRA, ROIC, EBITDA publié et physiques exigent des contrats de définition supplémentaires. Les segments fournis sont calculés séparément, sans sommer automatiquement leurs revenus.

Les nouveaux faits sont dans `sector_faits`, ajoutés par un import rejouable ; les `faits` historiques et les paramètres des scores sont préservés. Les pages sélectionnées des neuf dossiers AKD, ARD, CTM, DSW, GAZ, IMI, LES, SNP et SRM ont été rendues et lues. `knowledge/financial_reviews/2026-10-23-sector.json` conserve les pages PDF, unités originales, montants, bases, dates d’exercice, URL, empreintes et réserves. La date de publication du document reste explicitement non documentée lorsqu’elle ne peut pas être vérifiée ; ce n’est jamais la date de revue ou de génération.

Le lot complémentaire `2026-10-23-followup.json` réexamine ADI, MUT, CFGB, CMGP, SGTM et ENK : les contradictions ou limites ne sont pas levées sans preuve nouvelle. Il ajoute douze calculs indépendants des blocages : six ratios Ennakl sur entrées MTND/TND homogènes (sans conversion de change), cinq marges/rotation Mutandis, un coefficient d’exploitation CFG incluant les amortissements. Aucun résultat en MAD ni multiple au cours MAD n’est déduit des TND. Les acquisitions nettes Mutandis ne deviennent pas un CAPEX brut. Les 80 résultats historiques, techniques et scores restent identiques à données égales ; voir `tests/test_finance_followup_oct23.py` et [rapprochement détaillé](financial-followup-2026-10-23.md).

| Méthode | Formule | Condition / limite |
|---|---|---|
'''
    for key,spec in RULES.items():
        text+=f"| {spec['label']} | `{formula_text(spec)}` | {spec['note'] or spec['definition_contract'] or 'Même période, unité et périmètre primaire contrôlé.'} |\n"
    text+='''
Les données d’entrée, versions, sources et motifs d’indisponibilité sont consultables sur chaque fiche et dans [l’export des 80 sociétés](../web/couverture.json). Une formule disponible n’est pas une certification comptable.

## 5. Indicateurs indisponibles et réserves

Les ratios combinés, solvabilités réglementaires, coût du risque, créances en souffrance, ARPU, ROIC, rotations sur moyennes, mesures EPRA, coût minier, capacité portuaire/électrique et indicateurs immobiliers ne sont pas remplis par extrapolation lorsque leurs entrées et définitions manquent. Les grilles métier indiquent les données à collecter. Les dénominations commerciales ne prouvent pas un modèle SaaS ou des revenus récurrents.

Aradei : la marge opérationnelle inclut la juste valeur immobilière ; elle ne mesure pas une marge locative récurrente. CTM : RNPG et résultat total restent distincts. Lesieur : montants en millions arrondis, résultat opérationnel final distinct du résultat courant. Disway : acquisitions d’immobilisations nettes d’impôts selon le tableau publié. FFO publié n’est pas automatiquement EPRA Earnings. Les dépenses d’acquisition ne sont pas confondues avec les acquisitions de sociétés. Les réserves de continuité et les capitaux propres négatifs de STR restent visibles.

'''
    text+=f"L’audit financier comporte {dict(states)}. Les 19 dossiers initialement bloqués ont été réévalués lors des lots successifs ; onze restent bloqués au moins partiellement. Les 63 états `review_required` sont des travaux documentaires ouverts, pas 63 validations primaires complètes.\n"
    text+='''
## 6. Tests d’anomalies reproductibles

| Injection | Test | Résultat exigé |
|---|---|---|
| Cours ADI absent | `test_resilience.test_missing_price_is_not_a_valid_quote_and_others_unchanged` | ADI indisponible ; autres 79 identiques |
| Volume ADI contradictoire | `test_local_market.test_adi_volume_conflict_publishes_exact_other_79` | Preuves des 79 lignes ; cours/volumes ADI absents ; contrat partiel valide |
| Séance sans transaction | `test_resilience.test_suspended_title_and_session_without_transaction_are_local` | Aucune transaction inventée ; séance exclue des statistiques concernées |
| PER documentaire bloqué | `test_resilience.test_financial_conflict_only_withholds_affected_per` | PER absent ; ROE et technique préservés |
| Source temporairement inaccessible | `test_resilience.test_retry_is_limited_and_never_retries_validation_failure`, `test_local_market.test_unavailable_source_reuses_only_original_matching_proof` | Reprises bornées ; ancienne preuve uniquement pour son snapshot exact |
| Titre suspendu | `test_resilience.test_suspended_title_and_session_without_transaction_are_local` | Suspension explicite ; aucun PER au cours courant |
| Exception imprévue ADI | `test_resilience.test_unknown_adi_technical_exception_preserves_all_other_79` | Sortie technique suspendue ; autres 79 strictement identiques |
| Plusieurs titres défaillants | `test_resilience.test_several_titles_fail_independently` | ADI/RDS/TGCC isolés ; 77 autres identiques |
| Publication interrompue | `test_resilience.test_interrupted_publication_and_global_check_preserve_last_site` | Ancien index intact ; échange seulement de génération complète |
| Intégrité globale corrompue | `test_resilience.test_registry_corruption_is_global_not_locally_hidden` | Refus global ; aucun contournement |
| Construction complète avec ADI en erreur | `test_resilience.test_full_atomic_build_publishes_all_80_with_adi_exception` | 80 fiches écrites ; données erronées ADI absentes ; mêmes technique/fondamentaux/scores pour les 79 |
| Faux résultat numérique marqué en quarantaine | `test_resilience.test_wrong_numeric_output_is_quarantined_not_counted_as_valid` | Rejet tant que la valeur erronée n’est pas réellement absente |

Les tests de reprise, d’historique du journal, d’absence de résolution lors d’une panne, d’unités/périodes/périmètres, de banques/non-vie et des horaires Casablanca complètent ces injections. Commande : `python tools/verify_nour.py --build --asof 2026-10-23`. Chromium est exécuté par la CI avant fusion puis contre le site public à 375, 768 et 1440 pixels. Les résultats effectifs et les liens des exécutions sont à joindre à la livraison, sans assimiler la présence de ces tests à leur réussite.

## 7. Continuité et automatisations

Les onze déclenchements existants sont conservés : éditions 09:45, 12:45 et 16:00 ; collectes 10:45, 11:45, 13:45, 14:45, 15:45, 16:45, 17:15 et 17:45. Fuseau IANA `Africa/Casablanca`. L’édition de 16:00 ne garantit pas une clôture confirmée.

`nour_watchdog.yml` observe les éditions et les exécutions GitHub réelles à 09:05/09:35 jusqu’à 18:35 les jours de semaine, et après un workflow de publication terminé. Retard de grâce de 20 minutes ; au plus trois demandes par occurrence, espacées de 30 minutes, une seule demande à la fois pour respecter la file GitHub. Les collectes intermédiaires dépassées restent notées manquées ; seule la dernière est rattrapée. Une demande acceptée n’est jamais appelée exécutée. Les collectes ne dépendent d’aucune session ChatGPT, Claude ou connexion personnelle.

Le watchdog compare les empreintes du manifeste avec `report.json`, `runtime.json`, `index.html`, le journal et la couverture effectivement servis ; repère une exécution publiée non entièrement vérifiée, un run réussi plus récent non visible et un changement de séance avec tous les cours identiques. Ce dernier est un signal d’investigation, pas une preuve de panne. La collecte sans donnée exploitable et les conflits conservent leur diagnostic. [Surveillance](../web/anomalies.html) : société, source, domaine, gravité, première/dernière détection, statut, conséquences et action ; filtres sans appel à un fournisseur IA.

## 8. Protection et validation

Aucun fichier, workflow, branche ou paramètre du moteur principal n’est modifié. Les écritures GitHub de cette mission doivent toutes viser le dépôt Nour. Contrôles : référentiel unique explicite, contrats financiers et statistiques indépendants, calculs sectoriels rationnels indépendants, sérialisation sans NaN/Infinity, cohérence des exports assistant/rapport, sécurité des logos/liens, Python et JavaScript ; contrôles navigateur et contrôle du marché sur le site effectivement servi après déploiement.

## 9. Couverture individuelle des 80 sociétés

« Disponible » signifie calcul exporté avec ses réserves, pas validation exhaustive des pièces. « Suspendu » signifie blocage explicite de l’indicateur. « Manquant » signifie absence/insuffisance de données. La source, la période, les faits et la version détaillés sont dans `couverture.json`. Les listes métier de cet export donnent tous les indicateurs manquants et leurs raisons, y compris lorsqu’aucun chiffre sectoriel n’est disponible.

| Code et société | Métier | Fondamentaux disponibles | Suspendus | Manquants | Calculs métier disponibles |
|---|---|---|---|---|---|
'''
    for r in coverage['issuers']:
        by={status:[k for k,v in r['fundamental'].items() if v['status']==status] for status in ('available','blocked','missing')}
        sm=[k for k,v in r['sector']['metrics'].items() if v['value'] is not None]
        fmt=lambda v:', '.join(v) or '—'
        text+=f"| {r['symbol']} — {r['name']} | {r['family']} | {fmt(by['available'])} | {fmt(by['blocked'])} | {fmt(by['missing'])} | {fmt(sm)} |\n"
    text+='''
## 10. Limites restantes

La collecte de documents candidats est automatique ; leur identification ne valide pas automatiquement les valeurs ni les définitions. Les informations opérationnelles manquantes exigent encore lecture et rapprochement de publications primaires. Les méthodes requérant une définition sectorielle contractuelle restent sans valeur jusqu’à cette étape. L’identifiant est le code officiel du référentiel explicite ; aucun ISIN n’est déduit d’un nom.

Les rattrapages automatiques surveillent les occurrences de la journée en cours ; une panne prolongée de GitHub/Pages ou une indisponibilité couvrant toute la nuit exige une revue des historiques. GitHub Actions peut retarder ou manquer un cron, et son service reste une dépendance externe. Un refus global n’actualise pas le site public : ses diagnostics sont conservés dans le dépôt et les artefacts de l’exécution échouée, puis deviennent consultables à la prochaine publication saine. L’échange atomique de répertoires dépend du runner Linux ; sur une plateforme sans cette primitive, le code refuse de remplacer l’ancien site. Les contrats de définition métier doivent être revus lorsque la présentation comptable change. Aucun accès de source alternatif non autorisé n’est ajouté.

### Références primaires de méthode

'''
    text+='\n'.join(f'- {key} : {url}' for key,url in REFERENCES.items())+'\n'
    (ROOT/f'docs/mission-{day}.md').write_text(text,encoding='utf-8')
    print(json.dumps({'report':f'docs/mission-{day}.md','universe':len(coverage['issuers']),'sector_values':available,'published_business_kpis':kpis,'review_states':dict(states)},ensure_ascii=False))

if __name__=='__main__':main()
