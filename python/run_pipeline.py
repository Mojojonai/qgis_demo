from __future__ import annotations

import argparse
from pathlib import Path

from acs import run_acs_load
from config import load_config
from db import run_sql_file
from etl import run_etl
from report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the first end-to-end PostGIS pipeline.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--synthetic-only", action="store_true", help="Skip live downloads and use synthetic data only.")
    args = parser.parse_args()

    cfg = load_config(args.config)
    root = Path(cfg["_project_root"])

    print("Enabling extensions...")
    run_sql_file(cfg, root / "sql" / "00_extensions.sql")

    print("Creating schema...")
    run_sql_file(cfg, root / "sql" / "01_schema.sql")

    print("Running ETL...")
    counts = run_etl(args.config, synthetic_only=args.synthetic_only)
    for key, count in counts.items():
        print(f"  {key}: {count}")

    print("Loading ACS demographics...")
    demographics = run_acs_load(args.config)
    print(f"  towns: {len(demographics)}")

    print("Running spatial analysis...")
    run_sql_file(cfg, root / "sql" / "02_analysis.sql")

    print("Writing executive summary...")
    report_path = write_report(args.config)
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
