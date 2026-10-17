# Go-live calibration report

Generated 2026-10-18 from the warehouse build. Data: Northwind Connect, a **fictional** company simulated by `generator/` (January to June 2025). Every figure below is reproducible with `python scripts/build.py`.

Before go-live, every executive KPI is recalculated from raw source data and reconciled to the client's current report. Each gap is explained by a specific definition or data defect, and each bridge must close to zero; the dbt test `assert_calibration_bridges_close` fails the build if one does not.

## Summary: six-month averages

| KPI | Legacy report | Governed | Why they differ |
|---|---|---|---|
| Leads | 7,987 | 6,877 | Legacy counts test leads and vendor resubmissions; governed counts unique people within a 30-day window. |
| Contact rate | 9.9% | 66.3% | Legacy is per dial attempt and ignores disposition codes renamed on 2025-04-01; governed is the share of unique leads reached. |
| Conversion rate | 8.5% | 9.8% | Legacy divides wins closed in the month by every lead row; governed follows each unique lead to its own outcome. |
| Handled contacts | 2,218 | 1,859 | Legacy counts agent legs, so a transfer counts twice; governed counts customer contacts. |
| AHT (seconds) | 455s | 620s | Legacy drops wrap time and averages per leg; governed is talk + hold + wrap per handled contact. |
| FCR | 89.4% | 82.6% | Legacy is the share of legs agents marked resolved; governed checks for a repeat contact or ticket on the same driver within 7 days. |
| Bot containment | 85.3% | 85.2% | Definitions match (vendor flag); small gaps come from UTC vs local month bucketing. See bot true resolution for the outcome view. |

## Bridge 1: leads

From the legacy lead count to governed unique leads. `Check` columns must be zero.

| Month | Legacy | Test leads | Duplicates | Month bucketing | Governed | Check |
|---|---|---|---|---|---|---|
| Jan 2025 | 8,300 | -41 | -1,015 | -8 | 7,236 | 0 |
| Feb 2025 | 7,627 | -37 | -1,008 | -1 | 6,581 | 0 |
| Mar 2025 | 8,084 | -49 | -1,097 | -2 | 6,936 | 0 |
| Apr 2025 | 8,273 | -36 | -1,139 | -1 | 7,097 | 0 |
| May 2025 | 8,421 | -47 | -1,141 | +1 | 7,234 | 0 |
| Jun 2025 | 7,216 | -43 | -1,006 | +11 | 6,178 | 0 |

## Bridge 2: average handle time

Legacy averages talk + hold per agent leg. The governed AHT adds wrap time and divides by customer contacts, so a transferred call counts once.

| Month | Legacy | Add wrap | Per contact, not per leg | Month bucketing | Governed |
|---|---|---|---|---|---|
| Jan 2025 | 456s | +65s | +96s | 0s | 618s |
| Feb 2025 | 459s | +65s | +105s | -1s | 628s |
| Mar 2025 | 455s | +66s | +96s | 0s | 617s |
| Apr 2025 | 454s | +65s | +99s | +1s | 618s |
| May 2025 | 448s | +64s | +105s | 0s | 617s |
| Jun 2025 | 455s | +64s | +101s | 0s | 620s |

## Bridge 3: contact rate

The legacy report only recognises the dialer's original disposition codes. The vendor renamed them on 2025-04-01, so the legacy contact rate fell to zero and nobody was alerted. The governed metric maps both code versions and measures leads reached, not attempts connected.

| Month | Legacy | Map renamed codes | Per lead, not per attempt | Governed |
|---|---|---|---|---|
| Jan 2025 | 20.5% | 0.0 pts | +47.8 pts | 68.3% |
| Feb 2025 | 20.1% | 0.0 pts | +48.8 pts | 68.9% |
| Mar 2025 | 19.2% | 0.0 pts | +46.5 pts | 65.6% |
| Apr 2025 | 0.0% | +18.5 pts | +46.8 pts | 65.3% |
| May 2025 | 0.0% | +18.6 pts | +46.3 pts | 64.9% |
| Jun 2025 | 0.0% | +18.5 pts | +46.0 pts | 64.5% |

## Governed monthly KPIs

| Month | Unique leads | Contact rate | Conversion | Median speed to lead | AHT | FCR | Bot containment | Bot true resolution |
|---|---|---|---|---|---|---|---|---|
| Jan 2025 | 7,236 | 68.3% | 10.9% | 8 min | 618s | 82.8% | 85.2% | 59.9% |
| Feb 2025 | 6,581 | 68.9% | 11.7% | 8 min | 628s | 82.9% | 85.3% | 59.3% |
| Mar 2025 | 6,936 | 65.6% | 9.8% | 8 min | 617s | 81.2% | 85.8% | 59.3% |
| Apr 2025 | 7,097 | 65.3% | 8.9% | 8 min | 618s | 83.7% | 84.6% | 61.6% |
| May 2025 | 7,234 | 64.9% | 9.0% | 8 min | 617s | 81.4% | 86.2% | 61.7% |
| Jun 2025 | 6,178 | 64.5% | 8.7% | 8 min | 620s | 83.6% | 84.3% | 60.8% |

June FCR and bot resolution cover contacts up to 23 June: later contacts have not had their 7-day repeat window yet.

## Sign-off checklist

- [ ] Client operations lead agrees with the unique-lead definition (30-day window, test leads excluded)
- [ ] Client WFM lead agrees AHT includes wrap time
- [ ] Client CX lead agrees FCR is outcome-based (7-day repeat window on the same driver)
- [ ] Dialer vendor confirms the 2025-04-01 code change; legacy report owner informed
