"""Local-time run identity and briefing editions, independent of market scores."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Africa/Casablanca")
SLOTS = {
    "45 9 * * 1-5": ("morning", "09:45", "Briefing du matin"),
    "46 11 * * 1-5": ("refresh", "11:46", "Actualisation de fin de matinée"),
    "45 13 * * 1-5": ("midday", "13:45", "Briefing de mi-journée"),
    "45 15 * * 1-5": ("preclose", "15:45", "Actualisation avant clôture"),
    "0 18 * * 1-5": ("closing", "18:00", "Briefing de fin de journée / filet de sécurité"),
}
EDITIONS = {"morning": "matin", "midday": "midi", "closing": "cloture"}


def run_context(now=None, schedule="", event="local", slot="auto", started_at=None,
                run_id="", commit=""):
    now = (now or datetime.now(ZONE)).astimezone(ZONE)
    started = datetime.fromisoformat(started_at).astimezone(ZONE) if started_at else now
    target = None
    if event == "schedule":
        if schedule not in SLOTS:
            raise ValueError(f"Créneau planifié inconnu : {schedule}")
        selected, clock, label = SLOTS[schedule]
        hour, minute = map(int, clock.split(":"))
        target = started.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target > started:
            target -= timedelta(days=1)
        while target.weekday() >= 5:
            target -= timedelta(days=1)
    elif slot != "auto":
        choices = {value[0]: value for value in SLOTS.values()}
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
