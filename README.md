# CX Journey Warehouse

One governed warehouse for a telesales + customer-support operation: ten messy source
systems in, one trusted set of facts and 52 governed metrics out, with a go-live
calibration report that reconciles every executive KPI to the client's old numbers.

[![ci](https://github.com/qasimrazamalik-coder/cx-journey-warehouse/actions/workflows/ci.yml/badge.svg)](https://github.com/qasimrazamalik-coder/cx-journey-warehouse/actions/workflows/ci.yml)

> **The data is simulated.** Northwind Connect is a fictional broadband provider.
> `generator/` produces six months (Jan to Jun 2025) of realistic source extracts with
> the defects real extracts have, plus hidden ground truth so the warehouse logic can be
> measured against reality. No real company or customer data is used.

## What the warehouse found

The client's executive pack disagreed with the warehouse on six of seven KPIs. Every
gap traces to a specific cause, and each bridge closes to zero
([full report](reports/calibration_report.md)):

| KPI (6-month average) | Legacy report | Governed | Cause |
|---|---|---|---|
| Leads per month | 7,987 | 6,877 | Test leads and vendor resubmissions counted as leads |
| Contact rate | 9.9% | 66.3% | Dialer renamed its disposition codes on 1 April; the legacy report has shown 0% since, and nobody was alerted |
| AHT | 450s | 616s | Wrap time dropped, and each leg of a transferred call counted as a contact |
| FCR | 90.2% | 82.8% | Agents' own "resolved" flag vs. no repeat contact on the same driver within 7 days |
| Bot containment vs. true resolution | 85.5% | 59.1% | Containment only means the customer never reached an agent |

The same model surfaces where revenue leaks:

- **One lead vendor stopped converting.** After 15 March, Clickstream Media's conversion
  fell from 8.4% to 1.7%. It is the cheapest paid vendor per lead ($22) and the most
  expensive per sale ($1,264, against about $390 to $440 for the others).
- **Speed to lead has a staffing hole.** Median first dial is about 8 business minutes,
  except Phoenix-routed leads arriving between 14:00 and 16:00 ET (the site's lunch
  window): about 70 minutes. Conversion falls from 12.4% (dialed within 5 minutes) to
  5.2% (after 60 minutes).
- **The bot's worst drivers.** It reports 86% containment on charge disputes and
  proration questions, yet only 36 to 40% of those customers are actually done.

## Architecture

```
generator/ (Python)            dbt/ (DuckDB)                                         outputs
CRM leads + opportunities  ->  staging      one model per source, normalised        reports/calibration_report.md
Dialer (2 vendor layouts)      intermediate identity resolution, dedup, speed to lead docs/metric_catalog.md
CCaaS interaction legs         marts        facts + SCD2 dims + monthly KPIs         dbt docs + lineage
Ticketing, Billing, HR,        semantic     52 governed metrics (MetricFlow spec)
WFM, QA, Marketing spend       calibration  bridges to the legacy report
Legacy BI KPI pack
```

| Layer | Models | Notes |
|---|---|---|
| Staging | `stg_*` (11) | Normalised email/phone, UTC timestamps, both dialer layouts mapped to one shape |
| Intermediate | `int_identity__customer_map` (Python), `int_leads__deduplicated`, `int_lead_groups`, `int_leads__speed_to_lead`, `int_ccaas__sessions` | Identity resolution, duplicates, business-minute speed to lead |
| Marts | `fct_lead_journey`, `fct_contacts`, `fct_dial_attempts` (incremental), `fct_agent_day`, `fct_marketing_spend`, `dim_agent` (SCD2), `dim_customer`, `dim_contact_driver`, `mart_monthly_kpis` | Grain stated at the top of every model |
| Semantic layer | `_semantic_layer.yml` | 6 semantic models, 52 metrics; [catalog](docs/metric_catalog.md) generated from it |
| Calibration | `calibration__*` | Lead, AHT and contact-rate bridges plus a KPI comparison |

## The definitions that matter

| Metric | Definition | Detail that usually goes wrong |
|---|---|---|
| Unique lead | First lead per person within 30 days | Person = resolved identity across email and phone, not the lead ID |
| Speed to lead | Business minutes from arrival (or next opening) to first dial | A lead at 23:00 is not late until 08:00; Sundays skipped |
| Contact rate | Leads reached / unique leads | Per lead, not per dial attempt |
| AHT | Talk + hold + wrap per handled contact | A transfer is one contact, not two |
| FCR | Agent-handled contacts with no repeat or ticket on the same driver within 7 days | Contacts under 7 days old are excluded, not counted as resolved |
| Bot true resolution | Contained bot sessions with no repeat or ticket within 7 days | Unclassified sessions count any next contact as a repeat |
| Cost to serve | Handle time × the agent's loaded hourly rate that day, plus bot cost per session | Rate taken from WFM as of the contact date |

Decisions and the options rejected are in [`docs/adr/`](docs/adr).

## Data quality and tests

`dbt build` runs 114 checks; the build fails if any one fails:

- **Identity resolution accuracy** against ground truth: 99.6% purity, 99.99%
  completeness on 86,821 records (`assert_identity_resolution_accuracy`, gate 99%).
- **Calibration bridges close to zero** (`assert_calibration_bridges_close`).
- **No dial attempt lost or duplicated** between staging and the incremental fact.
- **Every disposition code mapped**: a vendor renaming codes again fails the build
  instead of silently zeroing a KPI.
- **Funnel order** holds for every lead (activated ⇒ sold ⇒ qualified ⇒ contacted).
- **Unit tests** for business-minute speed to lead (overnight, weekend, closing time)
  and for duplicate-lead grouping.
- Uniqueness, not-null, accepted values and relationships on every key.

The source defects are planted on purpose: the same person arriving as up to three leads in five phone formats,
mixed-case emails and typos, local vs UTC timestamps, transfers split into legs,
disposition codes renamed mid-period, late-arriving dialer rows, agents changing tier
and supervisor, shared household phones, and a legacy report with six definition bugs.

## Onboarding a second client (config, not code)

Client B's dialer sends a different export (other column names, epoch seconds,
millisecond durations, other codes). Onboarding it took one branch in
`stg_dialer__call_attempts` and seven rows in the `disposition_map` seed:

```bash
python scripts/build.py --dialer-format events
```

CI builds and tests both client layouts on every push.

## Run it

Needs Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python scripts/build.py                 # full scale, under a minute
python scripts/build.py --scale 0.15    # quick run
pytest -q                               # generator tests
```

This writes `warehouse.duckdb`, the calibration report and the metric catalog. Browse
the lineage with `cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .`
(set `CX_WAREHOUSE_PATH` to the warehouse file).

## Stack

Python (pandas, NumPy) · dbt-core 1.11 · DuckDB · dbt Semantic Layer (MetricFlow spec) ·
GitHub Actions. The SQL is written to port to Redshift, Snowflake or BigQuery; DuckDB keeps
the project free to run on a laptop.

## Related projects

- [ai-agent-outcome-audit](https://github.com/qasimrazamalik-coder/ai-agent-outcome-audit):
  what the support bot actually resolves, by driver, and what routing changes are worth.
- [governed-ai-analyst-benchmark](https://github.com/qasimrazamalik-coder/governed-ai-analyst-benchmark):
  an LLM writing raw SQL against this warehouse vs. an LLM limited to its governed metrics.
