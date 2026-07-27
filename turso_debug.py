#!/usr/bin/env python3
"""Run this from the project root to debug the Turso connection and booking query.

  python turso_debug.py [room_slug]

Prints the raw HTTP response so you can spot schema mismatches.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ── Load .env the same way main.py does ──────────────────────────────────────
def _load_dotenv() -> None:
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("WARNING: no .env file found next to this script")
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# ── Resolve credentials ───────────────────────────────────────────────────────
URL = os.environ.get("TURSO_DATABASE_URL", "").replace("libsql://", "https://").rstrip("/")
TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
SLUG = sys.argv[1] if len(sys.argv) > 1 else None

print("=" * 60)
print(f"TURSO_DATABASE_URL : {URL or '(not set)'}")
print(f"TURSO_AUTH_TOKEN   : {'(set, hidden)' if TOKEN else '(not set)'}")
print(f"Room slug          : {SLUG or '(none provided — pass as arg)'}")
print("=" * 60)

if not URL or not TOKEN:
    print("\nERROR: credentials missing — check your .env file")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("\nERROR: httpx not installed — run: pip install httpx")
    sys.exit(1)


def _raw(sql: str, args: list) -> dict:
    payload = {
        "requests": [
            {
                "type": "execute",
                "stmt": {
                    "sql": sql,
                    "args": [
                        {"type": "text", "value": str(a)} if a is not None else {"type": "null"}
                        for a in args
                    ],
                },
            },
            {"type": "close"},
        ]
    }
    resp = httpx.post(
        f"{URL}/v2/pipeline",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json=payload,
        timeout=10.0,
    )
    print(f"HTTP {resp.status_code}")
    return resp.json()


def pretty(data: dict) -> None:
    print(json.dumps(data, indent=2))


# ── 1. List all tables ────────────────────────────────────────────────────────
print("\n[1] Tables in database:")
data = _raw("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY name", [])
result = data.get("results", [{}])[0]
if result.get("type") == "ok":
    rows = result["response"]["result"]["rows"]
    for r in rows:
        print(f"  {r[0]['value']:30s}  ({r[1]['value']})")
else:
    print("  ERROR:")
    pretty(result)

# ── 2. Check Booking table columns ───────────────────────────────────────────
print('\n[2] Columns of "Booking" table (PRAGMA):')
data = _raw('PRAGMA table_info("Booking")', [])
result = data.get("results", [{}])[0]
if result.get("type") == "ok":
    cols_meta = result["response"]["result"]["cols"]
    col_names = [c["name"] for c in cols_meta]
    rows = result["response"]["result"]["rows"]
    if rows:
        for r in rows:
            row_dict = {col_names[i]: (v.get("value") if isinstance(v, dict) else v) for i, v in enumerate(r)}
            print(f"  {row_dict}")
    else:
        print('  (no rows — table "Booking" does not exist or has no columns)')
else:
    print("  ERROR:")
    pretty(result)

# ── 3. Sample 3 rows from Booking ─────────────────────────────────────────────
print('\n[3] First 3 rows of "Booking" (no filter):')
data = _raw('SELECT * FROM "Booking" LIMIT 3', [])
result = data.get("results", [{}])[0]
if result.get("type") == "ok":
    cols_meta = result["response"]["result"]["cols"]
    col_names = [c["name"] for c in cols_meta]
    rows = result["response"]["result"]["rows"]
    if rows:
        print(f"  columns: {col_names}")
        for r in rows:
            vals = [(v.get("value") if isinstance(v, dict) else v) for v in r]
            print(f"  {dict(zip(col_names, vals))}")
    else:
        print('  (table is empty)')
else:
    print("  ERROR:")
    pretty(result)

# ── 4. Check Room table ────────────────────────────────────────────────────────
print('\n[4] Columns of "Room" table:')
data = _raw('PRAGMA table_info("Room")', [])
result = data.get("results", [{}])[0]
if result.get("type") == "ok":
    cols_meta = result["response"]["result"]["cols"]
    col_names = [c["name"] for c in cols_meta]
    rows = result["response"]["result"]["rows"]
    if rows:
        for r in rows:
            row_dict = {col_names[i]: (v.get("value") if isinstance(v, dict) else v) for i, v in enumerate(r)}
            print(f"  {row_dict}")
    else:
        print('  (no rows — table "Room" does not exist)')
else:
    print("  ERROR:")
    pretty(result)

# ── 5. List rooms ──────────────────────────────────────────────────────────────
print('\n[5] All rows in "Room":')
data = _raw('SELECT * FROM "Room" LIMIT 10', [])
result = data.get("results", [{}])[0]
if result.get("type") == "ok":
    cols_meta = result["response"]["result"]["cols"]
    col_names = [c["name"] for c in cols_meta]
    rows = result["response"]["result"]["rows"]
    if rows:
        for r in rows:
            vals = [(v.get("value") if isinstance(v, dict) else v) for v in r]
            print(f"  {dict(zip(col_names, vals))}")
    else:
        print("  (no rooms in database)")
else:
    print("  ERROR:")
    pretty(result)

# ── 6. Run actual fetch_bookings query ─────────────────────────────────────────
if SLUG:
    today = datetime.now().strftime("%Y-%m-%d")
    print(f'\n[6] fetch_bookings query  (slug={SLUG!r}, date={today}):')
    sql = (
        'SELECT b.id, b.customerName, b.partySize, b.startTime, b.endTime, b.status '
        'FROM "Booking" b '
        'JOIN "Room" r ON b."roomId" = r.id '
        'WHERE r.slug = ? AND LOWER(b.status) = ? '
        'AND DATE(b.startTime) = ? '
        'ORDER BY b.startTime ASC '
        'LIMIT 20'
    )
    data = _raw(sql, [SLUG, "confirmed", today])
    result = data.get("results", [{}])[0]
    if result.get("type") == "ok":
        cols_meta = result["response"]["result"]["cols"]
        col_names = [c["name"] for c in cols_meta]
        rows = result["response"]["result"]["rows"]
        print(f"  → {len(rows)} rows returned")
        for r in rows:
            vals = [(v.get("value") if isinstance(v, dict) else v) for v in r]
            print(f"  {dict(zip(col_names, vals))}")
    else:
        print("  ERROR from Turso:")
        pretty(result)
else:
    print("\n[6] Skipped — pass room slug as argument: python turso_debug.py annabelle")
