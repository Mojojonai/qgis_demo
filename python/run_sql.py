from __future__ import annotations

import argparse

from config import load_config
from db import run_sql_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a SQL file against the project PostGIS database.")
    parser.add_argument("sql_file", help="SQL file path relative to the project root or absolute path.")
    parser.add_argument("--config", default="configs/project.toml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    run_sql_file(cfg, args.sql_file)
    print(f"Ran {args.sql_file}")


if __name__ == "__main__":
    main()
