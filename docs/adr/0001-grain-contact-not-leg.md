# ADR 0001: The contact, not the leg, is the unit of customer experience

**Status:** accepted

## Context
The CCaaS export has one row per interaction leg. A transferred call produces two or
more legs. The client's legacy report averaged handle time per leg and counted every leg
as a handled contact.

## Decision
`fct_contacts` has one row per session (customer contact). Handle time is the sum of
talk + hold + wrap across all agent legs of the contact. Leg-level detail stays in
staging for transfer analysis.

## Consequences
- AHT rises versus the legacy report (wrap time added, transfers no longer halve it).
  The calibration report quantifies this month by month.
- Transfer rate becomes a property of a contact (`is_transferred_between_agents`),
  which is what operations leaders mean by it.

## Rejected
Keeping leg grain and de-duplicating in each metric: every consumer would have to
remember the rule, and the AI layer would get it wrong.
