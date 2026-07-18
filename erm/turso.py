"""Turso (libsql) integration via the HTTP pipeline API.

Reads TURSO_DATABASE_URL and TURSO_AUTH_TOKEN from the environment.
All public functions are fire-and-forget safe: they swallow exceptions
and log them so a network hiccup never blocks the operator's workflow.
"""

import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import httpx

log = logging.getLogger(__name__)

_URL = os.environ.get("TURSO_DATABASE_URL", "").replace("libsql://", "https://").rstrip("/")
_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")


def _configured() -> bool:
    return bool(_URL and _TOKEN)


def _arg(value: Any) -> dict:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": "1" if value else "0"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "real", "value": str(value)}
    return {"type": "text", "value": str(value)}


def _cell(val: Any) -> Any:
    if isinstance(val, dict):
        if val.get("type") == "null":
            return None
        return val.get("value")
    return val


def _execute(sql: str, args: list) -> list[dict]:
    """Run one SQL statement and return rows as list-of-dicts."""
    if not _configured():
        return []
    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": [_arg(a) for a in args]}},
            {"type": "close"},
        ]
    }
    resp = httpx.post(
        f"{_URL}/v2/pipeline",
        headers={"Authorization": f"Bearer {_TOKEN}", "Content-Type": "application/json"},
        json=payload,
        timeout=5.0,
    )
    resp.raise_for_status()
    data = resp.json()
    result = data["results"][0]
    if result.get("type") != "ok":
        raise RuntimeError(f"Turso error: {result}")
    execute_result = result["response"]["result"]
    cols = [c["name"] for c in execute_result["cols"]]
    return [{col: _cell(row[i]) for i, col in enumerate(cols)} for row in execute_result["rows"]]


def _bg(fn: Callable, *args) -> None:
    """Run fn(*args) in a daemon thread — fire and forget."""
    t = threading.Thread(target=fn, args=args, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def fetch_bookings(room_slug: str) -> list[dict]:
    """Return confirmed bookings for *room_slug* sorted nearest to now first.

    Each dict has: id, customerName, partySize, startTime, endTime, status.
    Returns [] on any error.
    """
    if not _configured() or not room_slug:
        return []
    try:
        return _execute(
            'SELECT b.id, b.customerName, b.partySize, b.startTime, b.endTime, b.status '
            'FROM "Booking" b '
            'JOIN "Room" r ON b."roomId" = r.id '
            'WHERE r.slug = ? AND b.status = "confirmed" '
            'ORDER BY ABS(JULIANDAY(b."startTime") - JULIANDAY("now")) ASC '
            'LIMIT 10',
            [room_slug],
        )
    except Exception:
        log.exception("turso: fetch_bookings failed")
        return []


def _do_push_success_rate(room_slug: str, wins: int, total: int) -> None:
    rate = round((wins / total * 100), 2) if total > 0 else 0.0
    try:
        _execute('UPDATE "Room" SET "successRate" = ? WHERE slug = ?', [rate, room_slug])
        log.info("turso: successRate for %s → %.1f%%", room_slug, rate)
    except Exception:
        log.exception("turso: push_success_rate failed")


def push_success_rate(room_slug: str, wins: int, total: int) -> None:
    """Push updated success rate to Turso in the background."""
    if _configured() and room_slug:
        _bg(_do_push_success_rate, room_slug, wins, total)


def _do_insert_leaderboard(room_slug: str, group_name: str, party_size: int, time_spent_sec: int) -> None:
    try:
        rows = _execute('SELECT id FROM "Room" WHERE slug = ?', [room_slug])
        if not rows:
            log.warning("turso: no Room found for slug %r — leaderboard entry skipped", room_slug)
            return
        room_id = rows[0]["id"]
        now = datetime.now(timezone.utc).isoformat()
        _execute(
            'INSERT INTO "LeaderboardEntry" '
            '(id, "roomId", "groupName", "partySize", "timeSpentSec", "completedAt", "createdAt") '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            [str(uuid.uuid4()), room_id, group_name, party_size, time_spent_sec, now, now],
        )
        log.info("turso: leaderboard entry added for %s (%s, %ds)", room_slug, group_name, time_spent_sec)
    except Exception:
        log.exception("turso: insert_leaderboard_entry failed")


def insert_leaderboard_entry(room_slug: str, group_name: str, party_size: int, time_spent_sec: int) -> None:
    """Insert a leaderboard entry in the background."""
    if _configured() and room_slug:
        _bg(_do_insert_leaderboard, room_slug, group_name, party_size, time_spent_sec)
