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
                run_id="", commit=""):
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
    delay = round(max(0, (started-target).total_seconds()/60), 1) if target else None
    return {"timezone": "Africa/Casablanca", "event": event, "slot": selected,
            "label": label, "target_time": clock, "schedule": schedule or None,
            "scheduled_at": target.isoformat() if target else None,
            "scheduled_at_basis": "most_recent_weekday_cron_occurrence" if target else None,
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
