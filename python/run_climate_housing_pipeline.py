from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from config import project_root


def run_step(label: str, script: str, args: list[str]) -> None:
    command = [sys.executable, str(project_root() / "python" / script), *args]
    print(f"\n[{label}]")
    subprocess.run(command, cwd=project_root(), check=True)


def cap_args(value: int | None) -> list[str]:
    return [] if value is None or value <= 0 else ["--max-features", str(value)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete Maine climate-safe housing screening release.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--asset-cap", type=int, default=250, help="Per-source cap for bridge/culvert/DEP assets; <=0 loads all.")
    parser.add_argument("--constraint-cap", type=int, default=1000, help="Per-source cap for hazard/environment polygons; <=0 loads all.")
    parser.add_argument("--skip-downloads", action="store_true", help="Rebuild outputs from the data already loaded in PostGIS.")
    parser.add_argument("--force-boundaries-download", action="store_true")
    args = parser.parse_args()
    config_args = ["--config", args.config]

    run_step("Town housing/vulnerability screen", "build_climate_housing_mvp.py", [*config_args, "--pdf"])

    if not args.skip_downloads:
        run_step(
            "Climate infrastructure and exposed assets",
            "load_climate_open_data.py",
            [*config_args, *cap_args(args.asset_cap)],
        )
        run_step(
            "Flood and environmental constraints",
            "load_climate_constraints.py",
            [*config_args, *cap_args(args.constraint_cap)],
        )
        boundary_args = list(config_args)
        if args.force_boundaries_download:
            boundary_args.append("--force-download")
        run_step("Official Maine town boundaries", "load_maine_town_boundaries.py", boundary_args)

    run_step("Policy decision matrix", "build_climate_policy_matrix.py", [*config_args, "--pdf"])
    run_step("Standalone town map", "build_climate_housing_map.py", config_args)
    run_step("Candidate grid suitability model", "build_climate_candidate_grid.py", [*config_args, "--pdf"])
    run_step("Synchronized intelligence app", "build_climate_housing_app.py", config_args)
    run_step("Technical validation", "validate_climate_housing_outputs.py", config_args)
    print("\nClimate-safe housing screening release completed.")


if __name__ == "__main__":
    main()
