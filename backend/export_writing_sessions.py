#!/usr/bin/env python3
"""Export every row from the remote `writing_sessions` table to a JSON file.

The remote Postgres connection string is supplied at run time (never stored in a
file): pass `--database-url` or set the `REMOTE_DATABASE_URL` env var. This keeps
the local `backend/.env` (which points at localhost) untouched.

Usage (run from the backend/ directory):
    REMOTE_DATABASE_URL='postgresql://...' python export_writing_sessions.py
    python export_writing_sessions.py --database-url 'postgresql://...'
    python export_writing_sessions.py --database-url 'postgresql://...' --output /tmp/dump.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import WritingSessionRecord

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "exports" / "writing_sessions.json"


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def record_to_dict(record: WritingSessionRecord) -> dict[str, Any]:
    return {
        column.name: getattr(record, column.name)
        for column in WritingSessionRecord.__table__.columns
    }


def export(database_url: str, output: Path) -> int:
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        records = (
            session.query(WritingSessionRecord)
            .order_by(WritingSessionRecord.completed_at.asc())
            .all()
        )
        rows = [record_to_dict(record) for record in records]
    finally:
        session.close()
        engine.dispose()

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False, default=_json_default)
        fh.write("\n")

    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("REMOTE_DATABASE_URL"),
        help="Remote Postgres connection string (falls back to REMOTE_DATABASE_URL env var).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Destination JSON file (default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args()

    if not args.database_url:
        parser.error(
            "No remote database URL provided. Pass --database-url or set REMOTE_DATABASE_URL."
        )

    count = export(args.database_url, args.output)
    print(f"Exported {count} row(s) from writing_sessions to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
