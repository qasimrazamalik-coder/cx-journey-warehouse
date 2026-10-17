# ADR 0005: New clients onboard through configuration, not new models

**Status:** accepted

## Context
Each client sends the same kinds of data from different vendors. Client B's dialer
export uses different column names, epoch timestamps and millisecond durations.

## Decision
Vendor differences are absorbed in staging only. `stg_dialer__call_attempts` has one
branch per dialer layout, selected by `var('dialer_format')`, and the `disposition_map`
seed maps every vendor's codes to one standard outcome. Nothing downstream changes.

## Consequences
Onboarding client B's dialer took one staging branch and seven seed rows. CI builds and
tests both layouts on every push, so a change that breaks either client fails the build.
