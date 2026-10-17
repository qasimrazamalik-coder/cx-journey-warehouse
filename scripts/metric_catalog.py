"""Write docs/metric_catalog.md from the dbt semantic layer (target/semantic_manifest.json).

Run after `dbt parse` or `dbt build`. The catalog is generated, so it can never drift
from the definitions the warehouse actually uses.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    manifest = json.loads((ROOT / "dbt" / "target" / "semantic_manifest.json").read_text(encoding="utf-8"))
    measures = {}
    for sm in manifest["semantic_models"]:
        for m in sm.get("measures", []):
            measures[m["name"]] = (sm["name"], m)
    lines = [
        "# Metric catalog",
        "",
        "Generated from `dbt/models/marts/_semantic_layer.yml` by `scripts/metric_catalog.py`. Do not edit by hand.",
        "",
        "| Metric | Type | Definition | Built from |",
        "|---|---|---|---|",
    ]
    for metric in sorted(manifest["metrics"], key=lambda m: m["name"]):
        tp = metric.get("type_params", {})
        if metric["type"] == "ratio":
            built = f"`{tp['numerator']['name']}` / `{tp['denominator']['name']}`"
        elif metric["type"] == "derived":
            built = f"`{tp['expr']}`"
        else:
            name = tp["measure"]["name"]
            sm, m = measures[name]
            built = f"{m['agg']}(`{m.get('expr') or name}`) on `{sm}`"
        desc = (metric.get("description") or "").replace("\n", " ").strip()
        lines.append(f"| **{metric.get('label') or metric['name']}** (`{metric['name']}`) | {metric['type']} | {desc} | {built} |")
    out = ROOT / "docs" / "metric_catalog.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(manifest['metrics'])} metrics)")


if __name__ == "__main__":
    main()
