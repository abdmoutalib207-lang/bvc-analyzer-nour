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
CONTROL_SLOTS = {'15 17 * * 1-5': ('refresh', '17:15', 'Contrôle de clôture entre fournisseurs')}
HOURLY_SLOTS = {f'45 {hour} * * 1-5': ('refresh', f'{hour:02d}:45', 'Actualisation horaire')
                for hour in (10, 11, 13, 14, 15, 16, 17)}
# Morning and midday editions already cover 09:45 and 12:45.
MANUAL_ONLY = {
    "refresh": ("refresh", None, "Actualisation manuelle"),
    "preclose": ("preclose", None, "Point provisoire manuel"),
}


def source_commit(environment):
    """Report checked-out code identity, not a possibly stale queued event SHA."""
    return environment.get('NOUR_CODE_COMMIT') or environment.get('GITHUB_SHA', '')


def run_context(now=None, schedule="", event="local", slot="auto", started_at=None,
                run_id="", commit="", scheduled_for=None):
    now = (now or datetime.now(ZONE)).astimezone(ZONE)
    started = datetime.fromisoformat(started_at).astimezone(ZONE) if started_at else now
    target = None
    if event == "schedule":
        planned = {**SLOTS, **CONTROL_SLOTS, **HOURLY_SLOTS}
        if schedule not in planned:
            raise ValueError(f"Créneau planifié inconnu : {schedule}")
        selected, clock, label = planned[schedule]
        hour, minute = map(int, clock.split(":"))
        target = started.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target > started:
            target -= timedelta(days=1)
        while target.weekday() >= 5:
            target -= timedelta(days=1)
    elif slot != "auto":
        choices = {value[0]: value for value in SLOTS.values()}
        choices.update(MANUAL_ONLY)
        if slot not in choices:
            raise ValueError(f"Créneau manuel inconnu : {slot}")
        selected, clock, label = choices[slot]
    else:
        selected, clock, label = "adhoc", None, "Point de marché à la demande"
    if scheduled_for:
        if event != 'workflow_dispatch' or slot not in (*EDITIONS, 'refresh'):
            raise ValueError('Rattrapage réservé aux éditions explicites')
        planned_target = datetime.fromisoformat(scheduled_for)
        if planned_target.tzinfo is None:
            raise ValueError('Fuseau de rattrapage requis')
        planned_target = planned_target.astimezone(ZONE)
        allowed = {value[1] for value in SLOTS.values()} if slot != 'refresh' else {v[1] for v in (*CONTROL_SLOTS.values(), *HOURLY_SLOTS.values())}
        expected_clock = {v[0]:v[1] for v in SLOTS.values()}.get(slot)
        if (planned_target > started or planned_target.weekday() >= 5
                or planned_target.strftime('%H:%M') not in allowed
                or expected_clock and planned_target.strftime('%H:%M') != expected_clock
                or started-planned_target > timedelta(days=3)):
            raise ValueError('Cible de rattrapage incompatible')
        target = planned_target
        clock = target.strftime('%H:%M')
    delay = round(max(0, (started-target).total_seconds()/60), 1) if target else None
    return {"timezone": "Africa/Casablanca", "event": event, "slot": selected,
            "label": label, "target_time": clock, "schedule": schedule or None,
            "scheduled_at": target.isoformat() if target else None,
            "scheduled_at_basis": "watchdog_requested_occurrence" if scheduled_for else "most_recent_weekday_cron_occurrence" if target else None,
            "edition_for": (target or now).date().isoformat(),
            "started_at": started.isoformat(), "built_at": now.isoformat(),
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
               and now.weekday() < 5 and now.hour < 16 and 0 <= age <= 30)
    return {**snapshot, "status": "provisional" if current else "stale",
            "quotes": snapshot.get("quotes", {}) if current else {},
            "notice": ("Observation CDG provisoire, pas un flux temps réel ni une clôture."
                       if current else "Point de séance archivé ou trop ancien ; aucun cours intrajournalier frais présenté.")}
