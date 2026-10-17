"""Render the go-live calibration report (Markdown) from the calibration models.

    python scripts/calibration_report.py --db warehouse.duckdb [--out reports/calibration_report.md]
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def fmt(value, kind: str) -> str:
    if value is None:
        return "n/a"
    if kind in ("signed_int", "signed_sec") and round(value) == 0:
        return "0" if kind == "signed_int" else "0s"
    if kind == "pp" and round(value * 1000) == 0:
        return "0.0 pts"
    if kind == "pct":
        return f"{value * 100:.1f}%"
    if kind == "pp":
        return f"{value * 100:+.1f} pts"
    if kind == "int":
        return f"{int(round(value)):,}"
    if kind == "signed_int":
        return f"{int(round(value)):+,}"
    if kind == "sec":
        return f"{value:,.0f}s"
    if kind == "signed_sec":
        return f"{value:+,.0f}s"
    return str(value)


def month_label(value) -> str:
    return value.strftime("%b %Y")


KPI_KIND = {
    "Leads": "int", "Contact rate": "pct", "Conversion rate": "pct", "Handled contacts": "int",
    "AHT (seconds)": "sec", "FCR": "pct", "Bot containment": "pct",
}


def table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(ROOT / "warehouse.duckdb"))
    parser.add_argument("--out", default=str(ROOT / "reports" / "calibration_report.md"))
    args = parser.parse_args()
    con = duckdb.connect(args.db, read_only=True)

    summary = con.execute("""
        select kpi, kpi_order, avg(legacy_value) as legacy, avg(governed_value) as governed, any_value(root_cause) as cause
        from calibration.calibration__kpi_comparison
        group by kpi, kpi_order order by kpi_order
    """).fetchall()
    leads = con.execute("select * from calibration.calibration__lead_count_bridge order by report_month").fetchdf()
    aht = con.execute("select * from calibration.calibration__aht_bridge order by report_month").fetchdf()
    contact = con.execute("select * from calibration.calibration__contact_rate_bridge order by report_month").fetchdf()
    monthly = con.execute("select * from marts.mart_monthly_kpis order by report_month").fetchdf()

    lines = [
        "# Go-live calibration report",
        "",
        f"Generated {date.today().isoformat()} from the warehouse build. Data: Northwind Connect, a **fictional** "
        "company simulated by `generator/` (January to June 2025). Every figure below is reproducible with "
        "`python scripts/build.py`.",
        "",
        "Before go-live, every executive KPI is recalculated from raw source data and reconciled to the client's "
        "current report. Each gap is explained by a specific definition or data defect, and each bridge must close "
        "to zero; the dbt test `assert_calibration_bridges_close` fails the build if one does not.",
        "",
        "## Summary: six-month averages",
        "",
    ]
    rows = []
    for kpi, _order, legacy, governed, cause in summary:
        kind = KPI_KIND[kpi]
        rows.append([kpi, fmt(legacy, kind), fmt(governed, kind), cause])
    lines += [table(["KPI", "Legacy report", "Governed", "Why they differ"], rows), ""]

    lines += [
        "## Bridge 1: leads",
        "",
        "From the legacy lead count to governed unique leads. `Check` columns must be zero.",
        "",
    ]
    rows = [[
        month_label(r.report_month), fmt(r.legacy_reported_leads, "int"), fmt(r.step_remove_test_leads, "signed_int"),
        fmt(r.step_remove_duplicate_leads, "signed_int"), fmt(r.step_rebucket_to_center_month, "signed_int"),
        fmt(r.governed_unique_leads, "int"), fmt(r.check_residual, "int"),
    ] for r in leads.itertuples()]
    lines += [table(["Month", "Legacy", "Test leads", "Duplicates", "Month bucketing", "Governed", "Check"], rows), ""]

    lines += [
        "## Bridge 2: average handle time",
        "",
        "Legacy averages talk + hold per agent leg. The governed AHT adds wrap time and divides by customer "
        "contacts, so a transferred call counts once.",
        "",
    ]
    rows = [[
        month_label(r.report_month), fmt(r.legacy_reported, "sec"), fmt(r.step_add_wrap_time, "signed_sec"),
        fmt(r.step_count_contacts_not_legs, "signed_sec"), fmt(r.step_rebucket_to_center_month, "signed_sec"),
        fmt(r.governed, "sec"),
    ] for r in aht.itertuples()]
    lines += [table(["Month", "Legacy", "Add wrap", "Per contact, not per leg", "Month bucketing", "Governed"], rows), ""]

    lines += [
        "## Bridge 3: contact rate",
        "",
        "The legacy report only recognises the dialer's original disposition codes. The vendor renamed them on "
        "2025-04-01, so the legacy contact rate fell to zero and nobody was alerted. The governed metric maps "
        "both code versions and measures leads reached, not attempts connected.",
        "",
    ]
    rows = [[
        month_label(r.report_month), fmt(r.legacy_reported, "pct"), fmt(r.step_map_renamed_codes, "pp"),
        fmt(r.step_measure_per_lead_not_attempt, "pp"), fmt(r.governed, "pct"),
    ] for r in contact.itertuples()]
    lines += [table(["Month", "Legacy", "Map renamed codes", "Per lead, not per attempt", "Governed"], rows), ""]

    lines += [
        "## Governed monthly KPIs",
        "",
    ]
    rows = [[
        month_label(r.report_month), fmt(r.unique_leads, "int"), fmt(r.contact_rate, "pct"), fmt(r.conversion_rate, "pct"),
        f"{r.median_speed_to_lead_minutes:.0f} min", fmt(r.aht_seconds, "sec"), fmt(r.fcr_rate, "pct"),
        fmt(r.bot_containment_rate, "pct"), fmt(r.bot_true_resolution_rate, "pct"),
    ] for r in monthly.itertuples()]
    lines += [table(["Month", "Unique leads", "Contact rate", "Conversion", "Median speed to lead", "AHT", "FCR",
                     "Bot containment", "Bot true resolution"], rows), ""]
    lines += [
        "June FCR and bot resolution cover contacts up to 23 June: later contacts have not had their 7-day "
        "repeat window yet.",
        "",
        "## Sign-off checklist",
        "",
        "- [ ] Client operations lead agrees with the unique-lead definition (30-day window, test leads excluded)",
        "- [ ] Client WFM lead agrees AHT includes wrap time",
        "- [ ] Client CX lead agrees FCR is outcome-based (7-day repeat window on the same driver)",
        "- [ ] Dialer vendor confirms the 2025-04-01 code change; legacy report owner informed",
        "",
    ]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
