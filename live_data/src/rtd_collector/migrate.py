from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

TABLES = [
    "feed_ingestions",
    "vehicle_positions",
    "trip_updates",
    "stop_time_updates",
    "alerts",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export/import RTD collector PostgreSQL tables for migration"
    )
    parser.add_argument("--dsn", required=True, help="PostgreSQL DSN")

    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export tables to CSV files")
    export_parser.add_argument("--output-dir", required=True, help="Directory to write export files")

    import_parser = subparsers.add_parser("import", help="Import tables from CSV files")
    import_parser.add_argument("--input-dir", required=True, help="Directory containing export files")
    import_parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate destination tables before import",
    )

    return parser.parse_args()


def export_tables(dsn: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "tables": {},
    }

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            for table in TABLES:
                csv_path = output_dir / f"{table}.csv"
                with csv_path.open("w", encoding="utf-8") as handle:
                    copy_sql = f"COPY (SELECT * FROM {table} ORDER BY id) TO STDOUT WITH CSV HEADER"
                    cur.copy_expert(copy_sql, handle)

                cur.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cur.fetchone()[0]
                manifest["tables"][table] = {
                    "file": csv_path.name,
                    "rows": row_count,
                }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Export complete: {manifest_path}")


def _sync_id_sequences(cur: psycopg2.extensions.cursor) -> None:
    for table in TABLES:
        cur.execute(
            """
            SELECT setval(
                pg_get_serial_sequence(%s, 'id'),
                COALESCE((SELECT MAX(id) FROM {}), 1),
                (SELECT COALESCE(MAX(id), 0) > 0 FROM {})
            )
            """.format(table, table),
            (table,),
        )


def import_tables(dsn: str, input_dir: Path, truncate: bool) -> None:
    missing = [table for table in TABLES if not (input_dir / f"{table}.csv").exists()]
    if missing:
        raise FileNotFoundError(f"Missing CSV files: {', '.join(missing)}")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            if truncate:
                cur.execute(
                    "TRUNCATE TABLE feed_ingestions, vehicle_positions, trip_updates, stop_time_updates, alerts RESTART IDENTITY CASCADE"
                )

            for table in TABLES:
                csv_path = input_dir / f"{table}.csv"
                with csv_path.open("r", encoding="utf-8") as handle:
                    copy_sql = f"COPY {table} FROM STDIN WITH CSV HEADER"
                    cur.copy_expert(copy_sql, handle)

            _sync_id_sequences(cur)

    print(f"Import complete from {input_dir}")


def main() -> None:
    load_dotenv()
    args = parse_args()

    if args.command == "export":
        export_tables(args.dsn, Path(args.output_dir))
        return

    if args.command == "import":
        import_tables(args.dsn, Path(args.input_dir), args.truncate)
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
