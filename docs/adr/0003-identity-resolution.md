# ADR 0003: Deterministic identity resolution with a shared-phone guard

**Status:** accepted

## Context
The same person appears as CRM leads (several, from different vendors), a billing
account, voice sessions (phone only), chat sessions (email only) and tickets (email
only). Formats differ across systems; some customers have a newer phone in billing
than on their lead.

## Decision
Normalise emails (trim, lower-case) and phones (digits only, strip a leading 1), then
link records into connected components through any shared email or phone
(union-find, `int_identity__customer_map`). A phone seen with more than three distinct
emails is treated as shared and not used as a link.

## Consequences
- Accuracy is measured, not assumed: `assert_identity_resolution_accuracy` compares
  against the simulation's ground truth and fails below 99% purity or completeness.
- Transitive links can over-merge in real data (households, typos). The guard and the
  test are the controls; a probabilistic matcher is the next step if purity drops.

## Rejected
Fuzzy name matching as a primary key: names are the least reliable identifier here.
