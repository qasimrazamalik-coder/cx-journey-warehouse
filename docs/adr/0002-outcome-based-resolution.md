# ADR 0002: Resolution is judged by what the customer did next

**Status:** accepted

## Context
Two "resolved" signals exist in the sources: the agent's wrap flag
(`agent_marked_resolved`) and the bot vendor's containment flag. Both describe what
the system recorded, not what happened to the customer. In this data agents mark about
90% of contacts resolved and the bot reports about 86% containment, while outcome-based
FCR is about 83% and bot true resolution about 59%.

## Decision
A contact is resolved when the same customer does not contact us again about the same
driver, and does not open a ticket about it, within 7 days (`var('repeat_window_days')`).
Contacts younger than the window are flagged `is_outcome_observable = false` and left
out of rates instead of being counted as resolved.

## Consequences
- FCR drops versus the legacy report; the gap is the measurable cost of false closure.
- Customers who give up without contacting again look resolved. This is the known blind
  spot of every repeat-based measure; 30-day churn after contact is reported alongside
  it so silent failures still show up.
- Bot "containment" and "true resolution" are reported side by side.
- Depends on identity resolution: a repeat by the same person under a different phone
  number must still link, which is why ADR 0003 exists.

## Rejected
- 24-hour window: misses most voice callbacks in this data.
- 30-day window: attributes unrelated later problems to the first contact.
