"""The client's existing BI numbers, reproduced with the bugs such reports usually have.

This export is what the client's leadership currently believes. The warehouse's
calibration models reconcile against it, step by step, before go-live.

Bugs reproduced on purpose:
1. Lead counts include test leads and vendor resubmissions.
2. Contact rate is calculated per dial attempt, and only recognises the old
   disposition codes, so it collapses when the dialer renamed them in April.
3. Conversion divides won opportunities by every lead row.
4. AHT averages talk + hold per agent leg: wrap time is dropped and a
   transferred call counts as two contacts.
5. FCR is the share of legs the agent marked "resolved" (agents mark generously).
6. Months are bucketed on UTC dates instead of the contact center's local date.
"""

from __future__ import annotations

import pandas as pd

OLD_CONNECTED = {"SALE", "CT", "CB", "DNC"}


def legacy_monthly_kpis(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    leads = frames["crm__leads"].copy()
    leads["month"] = pd.to_datetime(leads["created_at_local"]).dt.to_period("M").dt.to_timestamp()
    lead_counts = leads.groupby("month").size().rename("leads")

    attempts = frames["dialer__call_attempts"].copy()
    attempts["month"] = pd.to_datetime(attempts["started_at_utc"]).dt.to_period("M").dt.to_timestamp()
    attempts["connected_legacy"] = attempts["disposition_code"].isin(OLD_CONNECTED)
    contact_rate = attempts.groupby("month")["connected_legacy"].mean().rename("contact_rate")

    opps = frames["crm__opportunities"].copy()
    opps["month"] = pd.to_datetime(opps["close_date"]).dt.to_period("M").dt.to_timestamp()
    wins = opps[opps["stage_name"] == "Closed Won"].groupby("month").size().rename("won")
    conversion = (wins / lead_counts).rename("conversion_rate")

    legs = frames["ccaas__interaction_legs"].copy()
    legs["month"] = pd.to_datetime(legs["started_at"]).dt.to_period("M").dt.to_timestamp()
    agent_legs = legs[legs["agent_id"].notna()]
    aht = agent_legs.assign(h=agent_legs["talk_seconds"] + agent_legs["hold_seconds"]).groupby("month")["h"].mean().rename("aht_seconds")
    flagged = agent_legs[agent_legs["agent_marked_resolved"].notna()]
    fcr = flagged["agent_marked_resolved"].astype(bool).groupby(flagged["month"]).mean().rename("fcr_rate")
    bot = legs[legs["channel"] == "chat_bot"]
    containment = bot["bot_contained"].astype(bool).groupby(bot["month"]).mean().rename("bot_containment_rate")
    handled = agent_legs.groupby("month").size().rename("handled_contacts")

    out = pd.concat([lead_counts, contact_rate, conversion, handled, aht, fcr, containment], axis=1).reset_index()
    out = out.rename(columns={"index": "month"})
    out["month"] = pd.to_datetime(out["month"]).dt.date
    out = out[(out["month"] >= pd.Timestamp("2025-01-01").date()) & (out["month"] <= pd.Timestamp("2025-06-01").date())]
    for col in ["contact_rate", "conversion_rate", "fcr_rate", "bot_containment_rate"]:
        out[col] = out[col].astype(float).round(4)
    out["aht_seconds"] = out["aht_seconds"].astype(float).round(1)
    out["report_name"] = "Executive KPI Pack (legacy BI)"
    return out.reset_index(drop=True)
