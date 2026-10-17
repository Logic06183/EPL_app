"""
Subscribable calendar of FPL deadlines (iCalendar), with reminders 24h and
2h before each one. Retention without email: subscribe once, get nudged every
gameweek. ?team=<id> makes each event link straight to that team's briefing.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from ..services.data_service import FPLDataService, get_data_service

router = APIRouter()

SITE = "https://epl-prediction-app.web.app"


def _ics_time(iso: str) -> str:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(events: list, team: Optional[int] = None, now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    link = f"{SITE}/?team={team}" if team else SITE
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//FPL AI Pro//Deadlines//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "X-WR-CALNAME:FPL deadlines", "X-PUBLISHED-TTL:PT12H", "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
    ]
    for e in events:
        if not e.get("deadline_time") or e.get("finished"):
            continue
        start = _ics_time(e["deadline_time"])
        desc = _escape(f"Transfers and captain lock at the deadline. Your briefing: {link}")
        lines += [
            "BEGIN:VEVENT",
            f"UID:fpl-deadline-gw{e['id']}@epl-prediction-app",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{start}",
            f"DTEND:{start}",
            f"SUMMARY:{_escape(e.get('name', 'Gameweek ' + str(e['id'])))} deadline",
            f"DESCRIPTION:{desc}",
            f"URL:{link}",
            "TRANSP:TRANSPARENT",
        ]
        for trigger in ("-PT24H", "-PT2H"):
            lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"TRIGGER:{trigger}",
                      f"DESCRIPTION:{_escape(e.get('name', 'FPL'))} deadline soon", "END:VALARM"]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


@router.get("/deadlines.ics")
async def deadlines_calendar(
    team: Optional[int] = Query(None, ge=1),
    data_service: FPLDataService = Depends(get_data_service),
):
    bootstrap = await data_service.get_bootstrap_data()
    return Response(
        content=build_ics(bootstrap.get("events", []), team),
        media_type="text/calendar; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600",
                 "Content-Disposition": 'inline; filename="fpl-deadlines.ics"'},
    )
