"""One command to build everything, on any OS.

    python scripts/build.py                     # full scale, client A dialer
    python scripts/build.py --scale 0.15        # fast run
    python scripts/build.py --dialer-format events   # onboard client B's dialer export

Steps: generate raw sources -> dbt build (models + tests + unit tests) -> calibration
report -> metric catalog.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path, env: dict) -> None:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", default="1.0")
    parser.add_argument("--dialer-format", default="classic", choices=["classic", "events"])
    parser.add_argument("--db", default=str(ROOT / "warehouse.duckdb"))
    parser.add_argument("--skip-report", action="store_true")
    args = parser.parse_args()

    db = str(Path(args.db).resolve())
    env = dict(os.environ)
    env["CX_WAREHOUSE_PATH"] = db
    env["PYTHONPATH"] = str(ROOT / "generator") + os.pathsep + env.get("PYTHONPATH", "")
    py = sys.executable

    if Path(db).exists():
        Path(db).unlink()
    run([py, "-m", "cxgen", "--db", db, "--scale", args.scale, "--dialer-format", args.dialer_format], ROOT, env)
    dbt_vars = f"{{dialer_format: {args.dialer_format}}}"
    run([py, "-c", "from dbt.cli.main import cli; cli()", "build", "--profiles-dir", ".", "--vars", dbt_vars], ROOT / "dbt", env)
    if not args.skip_report:
        run([py, "scripts/calibration_report.py", "--db", db], ROOT, env)
        run([py, "scripts/metric_catalog.py"], ROOT, env)
    print("\nBuild complete:", db)


if __name__ == "__main__":
    main()
