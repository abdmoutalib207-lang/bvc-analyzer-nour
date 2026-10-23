"""Local-time run identity and briefing editions, independent of market scores."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Africa/Casablanca")
SLOTS = {
    "45 9 * * 1-5": ("morning", "09:45", "Briefing du matin"),
    "45 12 * * 1-5": ("midday", "12:45", "Briefing de mi-journée"),
    "0 16 * * 1-5": ("closing", "16:00", "Briefing de clôture (confirmation requise)"),
}
EDITIONS = {"morning": "matin", "midday": "midi", "closing": "cloture"}
CONTROL_SLOTS = {
    '15 17 * * 1-5': ('refresh', '17:15', 'Contrôle de clôture entre fournisseurs'),
    '0 19 * * 1-5': ('refresh', '19:00', 'Filet de sécurité de fin de journée'),
}
HOURLY_SLOTS = {f'45 {hour} * * 1-5': ('refresh', f'{hour:02d}:45', 'Actualisation horaire')
                for hour in (10, 11, 13, 14, 15, 16, 17)}
# A bounded opening retry accommodates the source's later first quotes.
EXTRA_WAKE_SCHEDULES = ('55 9 * * 1-5',)
# Morning and midday editions already cover 09:45 and 12:45.
MANUAL_ONLY = {
    "refresh": ("refresh", None, "Actualisation manuelle"),
    "preclose": ("preclose", None, "Point provisoire manuel"),
}


def source_commit(environment):
    """Report checked-out code identity, not a possibly stale queued event SHA."""
    return environment.get('NOUR_CODE_COMMIT') or environment.get('GITHUB_SHA', '')


def planned_runs(now):
    """Today's local targets only; never invent a previous-day occurrence."""
    now = now.astimezone(ZONE)
    if now.weekday() >= 5:
        return []
    return sorted((dict(slot=slot, label=label,
                        target=now.replace(hour=int(clock[:2]), minute=int(clock[3:]),
                                           second=0, microsecond=0))
                   for slot, clock, label in (*SLOTS.values(), *CONTROL_SLOTS.values(), *HOURLY_SLOTS.values())),
                  key=lambda value: value['target'])


def current_target(now):
    """Latest due target, with a bounded same-day post-19h retry window."""
    now = now.astimezone(ZONE)
    if (now.hour, now.minute) >= (20, 15):
        return None
    due = [item for item in planned_runs(now) if item['target'] <= now]
    return due[-1] if due else None


def opening_retry_due(now, runtime):
    """One additional opening collection if the early source had no quotes."""
    now=now.astimezone(ZONE)
    try:
        observed=datetime.fromisoformat(runtime['started_at']).astimezone(ZONE)
        return bool(observed.date()==now.date() and (observed.hour,observed.minute)<(9,55)
                    and (9,55)<=(now.hour,now.minute)<(10,45)
                    and (runtime.get('collection') or {}).get('result') in ('awaiting_quotes','error'))
    except (KeyError,TypeError,ValueError):return False


def run_context(now=None, schedule="", event="local", slot="auto", started_at=None,
                run_id="", commit="", scheduled_for=None):
    now = (now or datetime.now(ZONE)).astimezone(ZONE)
    started = datetime.fromisoformat(started_at).astimezone(ZONE) if started_at else now
    target = None
    basis = None
    if event == "schedule":
        if schedule not in (*SLOTS, *CONTROL_SLOTS, *HOURLY_SLOTS, *EXTRA_WAKE_SCHEDULES):
            raise ValueError(f"Créneau planifié inconnu : {schedule}")
        due = current_target(started)
        if due:
            selected, label, target = due['slot'], due['label'], due['target']
            clock = target.strftime('%H:%M')
            basis = 'current_day_latest_due_target'
        else:
            selected, clock, label = 'refresh', None, 'Réveil hors fenêtre de séance'
    elif slot != "auto":
        choices = {value[0]: value for value in SLOTS.values()}
        choices.update(MANUAL_ONLY)
        if slot not in choices:
            raise ValueError(f"Créneau manuel inconnu : {slot}")
        selected, clock, label = choices[slot]
    else:
        selected, clock, label = "adhoc", None, "Point de marché à la demande"
    if scheduled_for:
        if event not in ('workflow_dispatch', 'schedule', 'repository_dispatch') or slot not in (*EDITIONS, 'refresh'):
            raise ValueError('Rattrapage réservé aux éditions explicites')
        requested = datetime.fromisoformat(scheduled_for)
        if requested.tzinfo is None:
            raise ValueError('Fuseau de rattrapage requis')
        requested = requested.astimezone(ZONE)
        compatible = next((item for item in planned_runs(started)
                           if item['target'] == requested and item['slot'] == slot), None)
        if requested > started or not compatible:
            raise ValueError('Cible de rattrapage incompatible ou antérieure à la journée courante')
        # A request can wait in GitHub's queue. Rebase it to the current slot,
        # without claiming the old edition ran, or postponing today's collection.
        due = current_target(started)
        if not due:
            raise ValueError('Rattrapage hors fenêtre de séance')
        target, selected, label = due['target'], due['slot'], due['label']
        clock = target.strftime('%H:%M')
        basis = 'watchdog_requested_occurrence' if target == requested else 'current_day_latest_due_target'
    delay = round(max(0, (started-target).total_seconds()/60), 1) if target else None
    return {"timezone": "Africa/Casablanca", "event": event, "slot": selected,
            "label": label, "target_time": clock, "schedule": schedule or None,
            "scheduled_at": target.isoformat() if target else None,
            "scheduled_at_basis": basis, "requested_scheduled_at": scheduled_for or None,
            "edition_for": started.date().isoformat(),
            "started_at": started.isoformat(), "built_at": now.isoformat(),
            "utc_offset_minutes": int(started.utcoffset().total_seconds()/60),
            "delay_minutes": delay, "late": delay is not None and delay > 15,
            "run_id": str(run_id), "commit": commit,
            "run_url": (f"https://github.com/abdmoutalib207-lang/bvc-analyzer-nour/actions/runs/{run_id}"
                        if run_id else None)}


def visible_intraday(snapshot, now=None):
    """Never relabel a cached observation as a new quote or a closing candle."""
    now = (now or datetime.now(ZONE)).astimezone(ZONE)
    if not snapshot:
        return {"status": "unavailable", "quotes": {}, "notice": "Aucun point de séance collecté."}
    observed = datetime.fromisoformat(snapshot["observed_at"]).astimezone(ZONE)
    age = (now-observed).total_seconds()/60
    current = (snapshot.get("session") == now.date().isoformat()
               and now.weekday() < 5 and now.hour < 16 and 0 <= age < 75)
    return {**snapshot, "status": "provisional" if current else "stale",
            "quotes": snapshot.get("quotes", {}) if current else {}, "age_minutes": round(age, 1),
            "notice": ("Observation CDG provisoire ; actualisation horaire, pas un flux temps réel ni une clôture."
                       if current else "Point de séance archivé ou trop ancien ; aucun cours intrajournalier frais présenté.")}
