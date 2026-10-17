"""Generate the raw source data.

    python -m cxgen --db warehouse.duckdb [--scale 1.0] [--dialer-format classic|events]
"""

from __future__ import annotations

import argparse
import time

from .config import SEED, GeneratorOptions
from .simulate import simulate
from .writer import write_duckdb


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Simulate Northwind Connect source-system extracts.")
    parser.add_argument("--db", default="warehouse.duckdb", help="DuckDB file to write raw_* schemas into")
    parser.add_argument("--scale", type=float, default=1.0, help="volume multiplier (0.1 for fast runs)")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--dialer-format", choices=["classic", "events"], default="classic",
                        help="classic = client A dialer export, events = client B dialer export")
    args = parser.parse_args(argv)

    t0 = time.time()
    frames = simulate(GeneratorOptions(seed=args.seed, scale=args.scale, dialer_format=args.dialer_format))
    counts = write_duckdb(frames, args.db, args.dialer_format)
    width = max(len(k) for k in counts)
    for name, n in counts.items():
        print(f"{name:<{width}}  {n:>9,}")
    print(f"done in {time.time() - t0:.1f}s -> {args.db}")


if __name__ == "__main__":
    main()
