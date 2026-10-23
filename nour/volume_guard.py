"""Transactional, deterministic closing-volume reconciliation.

The second provider verifies monetary turnover and prices line by line. Its
quantity column is optional: absent quantities never become a claim of two
independent quantity sources. Neither totals alone nor the main BVC engine
authorize a correction.
"""
from __future__ import annotations

import copy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from .market import CASABLANCA, CANCELLED_SESSIONS, SOURCE_URL, normalized_quote, session_date

CENT = Decimal("0.01")


def _number(value, label, integer=False):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label}: nombre absent ou booléen")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label}: nombre invalide") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"{label}: nombre négatif ou non fini")
    if integer and result != result.to_integral_value():
        raise ValueError(f"{label}: quantité non entière")
    return result


def _day(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Date de séance ISO explicite requise")
    return value


def _same_amount(a, b):
    return abs(a - b) <= CENT


def _totals(rows):
    return {"turnover_mad": str(sum((r["amount"] for r in rows.values()), Decimal(0))),
            "shares": sum(int(r["shares"]) for r in rows.values()), "quoted": len(rows)}


def _strict_reconcile_volumes(fixture, cdg_lines, overview, secondary, code_map, now=None, minimum=20, allow_detail_only=False):
    """Return ``(deepcopy(fixture), audit)``; corrections are all-or-nothing.

    Inputs are observations, not instructions. ``overview`` is the current CDG
    closing snapshot; ``secondary`` follows the dated cash-equities schema. A
    source outage permits publication only if the retained snapshot already
    matches every validated CDG line and both CDG aggregate controls. Malformed
    or contradictory observations always remain visible in ``refusals``.
    """
    updated = copy.deepcopy(fixture)
    now = (now or datetime.now(CASABLANCA)).astimezone(CASABLANCA)
    audit = {"schema_version": 1, "observed_at": now.isoformat(), "session": None,
             "status": "incomplete", "publication_safe": False, "internal_match": False,
             "cross_source_verified": False, "quantities_cross_source_verified": False,
             "providers": [{"provider": "CDG Capital Bourse", "source_url": SOURCE_URL}],
             "totals": {}, "corrections": [], "refusals": [], "notices": [],
             "policy": "same_session_exact_universe_line_by_line_no_averaging_v1"}

    def refuse(reason, status="conflict", symbol=None):
        refusal = {"reason": reason}
        if symbol:
            refusal["symbol"] = symbol
        audit["refusals"].append(refusal)
        audit["status"] = status
        audit["publication_safe"] = False
        return copy.deepcopy(fixture), audit

    try:
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            return refuse("Seuil minimal de titres invalide", "incomplete")
        if not isinstance(overview, dict) or overview.get("status") != "closed":
            return refuse("Observation de clôture définitive requise ; intraday refusé", "incomplete")
        session = _day(overview.get("asof"))
        audit["session"] = session
        if session > now.date().isoformat() or session in CANCELLED_SESSIONS or date.fromisoformat(session).weekday() >= 5:
            return refuse("Séance future, annulée ou hors calendrier hebdomadaire")
        if session == now.date().isoformat() and now.hour < 16:
            return refuse("Clôture du jour non acquise avant 16h Casablanca", "incomplete")
        if overview.get("provisional") is True:
            return refuse("Observation provisoire refusée", "incomplete")
        if (fixture.get("market", {}).get("last_session") or "") > session:
            return refuse("Séance antérieure à la dernière séance du snapshot")
        codes = {str(k): str(v).strip().upper() for k, v in code_map.items()}
        if len(set(codes.values())) != len(codes) or any(not c for c in codes.values()):
            return refuse("Collision ou absence de codes officiels")
        inverse = {v: k for k, v in codes.items()}
        records = fixture["records"]
        if not isinstance(cdg_lines, list):
            return refuse("Collecte CDG indisponible", "unavailable")
        candidates, seen = {}, set()
        for line in cdg_lines:
            if not isinstance(line, dict):
                return refuse("Ligne CDG mal formée", "incomplete")
            code = str(line.get("Symbol") or "").strip().upper()
            if not code or code in seen:
                return refuse("Code CDG absent ou dupliqué")
            seen.add(code)
            if all(line.get(k) in (None, "") for k in ("Cours", "DateDernierCours", "Volumes", "QteEchangee")):
                continue  # CDG uses entirely empty placeholders for non-traded issuers.
            raw_day = session_date(line.get("DateDernierCours"))
            raw_shares = _number(line.get("QteEchangee", 0), f"{code} quantité CDG", True)
            if raw_day and raw_day > session and raw_shares > 0:
                return refuse("Observation CDG postérieure à la séance annoncée", symbol=code)
            if raw_shares == 0:
                if line.get("Volumes") not in (None, "") and _number(line["Volumes"], "montant sans échange") > 0:
                    return refuse("Montant CDG positif sans quantité échangée", symbol=code)
                continue
            if not raw_day:
                return refuse("Transaction CDG sans séance explicite", symbol=code)
            if raw_day != session:
                continue  # Illiquid reference quotes retain their genuine older date.
            ticker = inverse.get(code)
            if ticker not in records:
                return refuse("Titre échangé CDG absent du référentiel Nour", symbol=code)
            if line.get("provisional") is True:
                return refuse("Ligne CDG provisoire", symbol=ticker)
            quote = normalized_quote(line, ticker)
            if quote is None:
                return refuse("Transaction CDG non normalisable", symbol=ticker)
            amount = _number(line.get("Volumes"), f"{ticker} montant CDG")
            candidates[ticker] = {"code": code, "bar": quote["bar"], "shares": raw_shares,
                                  "amount": amount, "price": _number(line.get("Cours"), "cours CDG")}
        if len(candidates) < minimum:
            return refuse(f"Couverture CDG inférieure à {minimum} titres", "incomplete")
        expected_count = int(_number(overview.get("breadth", {}).get("quoted"), "Nombre attendu", True))
        expected_amount = _number(overview.get("turnover_mad"), "Total monétaire CDG")
        expected_shares = _number(overview.get("shares"), "Quantité totale CDG", True)
        totals = _totals(candidates)
        audit["totals"]["cdg_lines"] = totals
        audit["totals"]["candidate"] = copy.deepcopy(totals)
        audit["totals"]["cdg_overview"] = {"turnover_mad": str(expected_amount),
                                                 "shares": int(expected_shares), "quoted": expected_count}
        audit["totals"]["overview"] = copy.deepcopy(audit["totals"]["cdg_overview"])
        aggregate_match = (expected_count == len(candidates)
                           and _same_amount(Decimal(totals['turnover_mad']), expected_amount)
                           and totals['shares'] == expected_shares)
        if expected_count != len(candidates) and not allow_detail_only:
            return refuse("Nombre de titres échangés différent de la largeur CDG", "incomplete")
        if not aggregate_match and not allow_detail_only:
            return refuse("Sommes détaillées CDG différentes des agrégats de séance")

        # Validate the retained universe, every candle and every day field before
        # authorizing even one volume-only revision.
        retained, proposed, local_errors = {}, [], []
        for ticker, rec in records.items():
            latest = max([b.get("d", "") for b in rec.get("candles", [])] + [rec.get("price_asof") or ""])
            if latest > session:
                local_errors.append({"symbol": ticker, "reason": "Historique plus récent que la séance contrôlée"})
            day_activity = rec.get("price_asof") == session and (
                _number(rec.get("day_shares", 0), "quantité retenue", True) > 0
                or _number(rec.get("day_turnover_mad", 0), "montant retenu") > 0)
            candle_activity = any(b.get("d") == session and _number(b.get("v"), "quantité bougie retenue", True) > 0
                                  for b in rec.get("candles", []))
            if (day_activity or candle_activity) and ticker not in candidates:
                local_errors.append({"symbol": ticker, "reason": "Titre retenu échangé absent de l'ensemble CDG"})
        for ticker, candidate in candidates.items():
            rec, bar = records[ticker], candidate["bar"]
            existing = [b for b in rec.get("candles", []) if b.get("d") == session]
            if len(existing) != 1:
                local_errors.append({"symbol": ticker, "reason": "Bougie retenue absente ou dupliquée ; aucune création par le filet de sécurité"})
                continue
            old = existing[0]
            if any(_number(old.get(k), f"{ticker} {k}") != _number(bar[k], k) for k in ("o", "h", "l", "c")):
                local_errors.append({"symbol": ticker, "reason": "OHLC divergents ; révision automatique interdite"})
                continue
            if rec.get("price_asof") != session or _number(rec.get("price"), "cours retenu") != candidate["price"]:
                local_errors.append({"symbol": ticker, "reason": "Cours/date retenus divergents ; correction hors volume interdite"})
                continue
            before = {"candle_shares": int(_number(old.get("v"), "quantité bougie", True)),
                      "day_shares": int(_number(rec.get("day_shares"), "quantité retenue", True)),
                      "day_turnover_mad": str(_number(rec.get("day_turnover_mad"), "montant retenu"))}
            if "turnover_mad" in old:
                before["candle_turnover_mad"] = str(_number(old["turnover_mad"], "montant bougie"))
            retained[ticker] = {"amount": Decimal(before["day_turnover_mad"]),
                                "shares": Decimal(before["day_shares"])}
            after = {"candle_shares": int(candidate["shares"]), "day_shares": int(candidate["shares"]),
                     "day_turnover_mad": str(candidate["amount"])}
            differs = (before["candle_shares"] != after["candle_shares"] or before["day_shares"] != after["day_shares"]
                       or not _same_amount(Decimal(before["day_turnover_mad"]), candidate["amount"])
                       or ("candle_turnover_mad" in before and not _same_amount(Decimal(before["candle_turnover_mad"]), candidate["amount"])))
            if differs:
                proposed.append({"symbol": ticker, "session": session, "before": before, "after": after,
                                 "fields": ["v", "day_shares", "day_turnover_mad", "turnover_mad"],
                                 "reason": "OHLC identiques ; montant et cours confirmés ligne par ligne par le second fournisseur"})
        audit["totals"]["retained_before"] = _totals(retained)
        audit["totals"]["retained"] = copy.deepcopy(audit["totals"]["retained_before"])
        audit["proposed_corrections"] = proposed
        audit["internal_match"] = not local_errors and not proposed and set(retained) == set(candidates)
        if local_errors:
            audit["refusals"].extend(local_errors)
            return refuse("Snapshot retenu non corrigeable automatiquement")

        if not isinstance(secondary, dict) or secondary.get("status") != "ok":
            audit["status"] = "unavailable" if not isinstance(secondary, dict) or secondary.get("status") in ("unavailable", "error", "timeout") else "incomplete"
            audit["publication_safe"] = audit["internal_match"] and aggregate_match
            audit["notices"].append("Second fournisseur indisponible : aucun rapprochement multisource validé ; aucune correction autorisée.")
            if isinstance(secondary, dict):
                audit["providers"].append({k: secondary.get(k) for k in ("provider", "status", "source_url")})
                audit['notices'].extend(n for n in secondary.get('notices', []) if isinstance(n, str))
            if proposed:
                audit["refusals"].append({"reason": "Écarts retenus non corrigés faute de seconde source"})
            if audit['publication_safe']:
                # This is NOT a multisource validation. Only unchanged primary
                # rows, already checked individually and against both totals,
                # may be published with an explicit degraded quality level.
                audit.update(status='primary_checked', publication_scope='primary_only', aggregate_match=True,
                    secondary_status=secondary.get('status') if isinstance(secondary, dict) else 'unavailable',
                    validated_symbols=sorted(candidates),
                    validated_lines={s:{'price':str(c['price']), 'shares':int(c['shares']),
                                       'turnover_mad':str(c['amount'])} for s,c in candidates.items()})
                audit['totals']['retained_after']=copy.deepcopy(totals)
                audit['notices'].append('Source principale contrôlée ligne par ligne et par ses agrégats ; recoupement externe indisponible. Aucun volume corrigé et aucun incident résolu.')
            return updated, audit
        provider = str(secondary.get("provider") or "").strip()
        source_url = str(secondary.get("source_url") or "")
        audit["providers"].append({"provider": provider, "source_url": source_url, "observed_at": secondary.get("observed_at")})
        upstream = str(secondary.get("original_provider") or secondary.get("provider_id") or provider).lower()
        if (not provider or "cdg" in provider.lower() or "cdg" in upstream
                or "cdgcapitalbourse" in urlsplit(source_url).netloc.lower()
                or urlsplit(source_url).scheme != "https" or not urlsplit(source_url).netloc):
            return refuse("Second fournisseur indépendant et URL HTTPS explicites requis", "incomplete")
        if (secondary.get("scope") != "cash_equities" or _day(secondary.get("session")) != session
                or secondary.get("provisional") is True or secondary.get("market_closed") is not True):
            return refuse("Périmètre, séance ou caractère définitif du second fournisseur incompatible")
        observed = datetime.fromisoformat(str(secondary.get("observed_at")))
        if observed.tzinfo is None or observed > now or observed.astimezone(CASABLANCA).date().isoformat() < session:
            return refuse("Horodatage du second fournisseur absent, futur ou antérieur à la séance")
        if observed.astimezone(CASABLANCA).date().isoformat() == session and observed.astimezone(CASABLANCA).hour < 16:
            return refuse("Second relevé capturé avant clôture")
        other, quantity_count = {}, 0
        rows = secondary.get("rows")
        if not isinstance(rows, list):
            return refuse("Détail du second fournisseur absent", "incomplete")
        for row in rows:
            if not isinstance(row, dict):
                return refuse("Ligne du second fournisseur invalide", "incomplete")
            code = str(row.get("symbol") or "").strip().upper()
            ticker = inverse.get(code)
            if ticker not in candidates or ticker in other:
                return refuse("Code du second fournisseur absent, supplémentaire ou dupliqué", symbol=code)
            if _day(row.get("session")) != session:
                return refuse("Date de ligne secondaire différente de la séance", symbol=ticker)
            amount, price = _number(row.get("amount_mad"), "montant secondaire"), _number(row.get("price"), "cours secondaire")
            candidate = candidates[ticker]
            if price != candidate["price"] or not _same_amount(amount, candidate["amount"]):
                return refuse("Montant ou cours contradictoire entre fournisseurs", symbol=ticker)
            quantity = row.get("shares")
            if quantity is not None:
                quantity = _number(quantity, "quantité secondaire", True)
                if quantity != candidate["shares"]:
                    return refuse("Quantité secondaire contradictoire ou montant monétaire copié dans la colonne quantité", symbol=ticker)
                quantity_count += 1
            other[ticker] = {"amount": amount, "shares": quantity or Decimal(0)}
        if set(other) != set(candidates):
            return refuse("Ensemble des titres secondaires incomplet", "incomplete")
        secondary_total = sum((r["amount"] for r in other.values()), Decimal(0))
        audit["totals"]["secondary"] = {"turnover_mad": str(secondary_total), "quoted": len(other),
                                                 "shares": sum(int(r["shares"]) for r in other.values()) if quantity_count == len(other) else None,
                                                 "quantity_rows": quantity_count}
        if not _same_amount(secondary_total, expected_amount) and not allow_detail_only:
            return refuse("Somme monétaire secondaire différente de l'agrégat de séance")
        if not aggregate_match and (quantity_count != len(candidates) or proposed):
            return refuse("Écart agrégé : toutes les quantités doivent être recoupées et aucune correction automatique n'est autorisée", "incomplete")
        for correction in proposed:
            before,after=correction['before'],correction['after']
            quantity_changed=(before['candle_shares']!=after['candle_shares'] or before['day_shares']!=after['day_shares'])
            if quantity_changed and not other[correction['symbol']]['shares']:
                return refuse("Quantité à corriger non attestée par le second fournisseur", symbol=correction['symbol'])
        audit["cross_source_verified"] = True
        audit["quantities_cross_source_verified"] = quantity_count == len(candidates)
        audit["validated_symbols"] = sorted(candidates)
        audit["validated_fields"] = ["v", "day_shares", "day_turnover_mad", "turnover_mad"]
        audit["notices"].append("Deux fournisseurs publics distincts contrôlés ; indépendance de leurs données amont non attestée.")
        audit["notices"].extend(str(n) for n in secondary.get("notices", []) if isinstance(n, str))
        if quantity_count != len(candidates):
            audit["notices"].append("Quantités attestées uniquement par CDG et son contrôle agrégat pour les lignes sans quantité secondaire ; pas de double validation des quantités.")
        for correction in proposed:
            ticker = correction["symbol"]
            candidate, rec = candidates[ticker], updated["records"][ticker]
            target = next(b for b in rec["candles"] if b["d"] == session)
            target.update(v=int(candidate["shares"]), turnover_mad=float(candidate["amount"]))
            rec.update(day_shares=int(candidate["shares"]), day_turnover_mad=float(candidate["amount"]))
        audit["corrections"] = proposed
        audit["totals"]["retained_after"] = copy.deepcopy(totals)
        audit.update(status="reconciled" if proposed else "matched", publication_safe=True, internal_match=True)
        if not aggregate_match:
            audit.update(status='detail_matched', publication_scope='validated_title_lines', aggregate_match=False,
                         validated_lines={s:{'price':str(c['price']), 'shares':int(c['shares']),
                                             'turnover_mad':str(c['amount'])} for s,c in candidates.items()})
            audit['refusals'].append({'code':'reported_aggregate_mismatch', 'reason':'Total annoncé non confirmé ; seules les lignes détaillées sont recoupées',
                                      'fields':['shares','turnover_mad','lines'],
                                      'before':{'shares':int(expected_shares),'turnover_mad':str(expected_amount),'lines':expected_count},
                                      'observed':{'shares':totals['shares'],'turnover_mad':totals['turnover_mad'],'lines':totals['quoted']}})
            audit['notices'].append('Total global annoncé non confirmé. Publication limitée aux titres recoupés ligne par ligne, sans modifier les agrégats annoncés ni inventer le titre manquant.')
        return updated, audit
    except (ValueError, TypeError, KeyError, InvalidOperation, OverflowError) as exc:
        return refuse(f"Contrôle incomplet ou invalide : {exc}", "incomplete")


def reconcile_volumes(fixture, cdg_lines, overview, secondary, code_map, now=None,
                      minimum=20, allow_detail_only=False, allow_local_isolation=False):
    candidate, audit = _strict_reconcile_volumes(fixture, cdg_lines, overview, secondary,
        code_map, now=now, minimum=minimum, allow_detail_only=allow_detail_only)
    pending=[]
    if audit.get('publication_safe'):
        for symbol,rec in candidate['records'].items():
            problem=rec.get('quarantined_market')
            if not problem:continue
            if (audit.get('cross_source_verified') and symbol in (audit.get('validated_symbols') or [])
                    and problem.get('session')==audit.get('session')):
                rec.pop('quarantined_market',None)
            else:pending.append(symbol)
        if not pending:return candidate,audit
    if not allow_local_isolation:return candidate,audit
    from .local_market import isolate_market_lines
    try:
        return isolate_market_lines(fixture, cdg_lines, overview, secondary, code_map,
                                    now or datetime.now(CASABLANCA), minimum)
    except (ValueError, TypeError, KeyError, ArithmeticError):
        # A failed partial proof never turns into a global green light.
        return candidate, audit
