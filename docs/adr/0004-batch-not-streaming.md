# ADR 0004: Daily batch with incremental late-data handling, not streaming

**Status:** accepted

## Context
The use cases are daily operational reviews, weekly coaching and monthly business
reviews. About 2% of dialer rows arrive one to five days late.

## Decision
Batch ELT with dbt. `fct_dial_attempts` is incremental (delete+insert on
`attempt_id`) and reprocesses rows loaded in the last 7 days
(`var('incremental_lookback_days')`), so late rows are picked up without duplicates.

## Consequences
Insights are at most a day old, which matches how decisions are made. Streaming would
add infrastructure without changing a single decision.
