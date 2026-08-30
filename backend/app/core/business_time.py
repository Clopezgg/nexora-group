from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


BUSINESS_TZ = ZoneInfo("America/Tegucigalpa")


def business_today(now: datetime | None = None) -> date:
    """Return the current Nexora business date in Honduras.

    Azure and CI normally run in UTC. Using ``date.today()`` therefore moves
    date-only business events to the next day between 18:00 and 23:59 in
    Honduras. Accepting an explicit aware datetime keeps the boundary
    deterministic and directly testable.
    """
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("business_today requires a timezone-aware datetime")
    return instant.astimezone(BUSINESS_TZ).date()
