# Metric catalog

Generated from `dbt/models/marts/_semantic_layer.yml` by `scripts/metric_catalog.py`. Do not edit by hand.

| Metric | Type | Definition | Built from |
|---|---|---|---|
| **Activations** (`activated_leads`) | simple | Sales whose customer started a subscription within 45 days. | sum(`activated_count`) on `lead_journey` |
| **Activation rate** (`activation_rate`) | ratio | Activations / sales. | `activated_leads` / `sold_leads` |
| **adherent_minutes_total** (`adherent_minutes_total`) | simple | Metric created from measure adherent_minutes_total | sum(`adherent_minutes`) on `agent_days` |
| **agent_handle_seconds_total** (`agent_handle_seconds_total`) | simple | Metric created from measure agent_handle_seconds_total | sum(`case when is_agent_handled then agent_handle_seconds else 0 end`) on `contacts` |
| **Agent-handled contacts** (`agent_handled_contacts`) | simple |  | sum(`agent_handled_count`) on `contacts` |
| **agent_sales_total** (`agent_sales_total`) | simple | Metric created from measure agent_sales_total | sum(`sales`) on `agent_days` |
| **Average handle time (seconds)** (`aht_seconds`) | ratio | Talk + hold + wrap across all agent legs of a contact, per agent-handled contact. | `agent_handle_seconds_total` / `agent_handled_contacts` |
| **attempted_leads** (`attempted_leads`) | simple | Metric created from measure attempted_leads | sum(`case when first_attempt_at_utc is not null then 1 else 0 end`) on `lead_journey` |
| **Average speed to lead (business minutes)** (`avg_speed_to_lead_minutes`) | ratio | Average open minutes from lead arrival (or next opening) to first dial attempt, over attempted leads. | `speed_to_lead_minutes_total` / `attempted_leads` |
| **Booked annual value (USD)** (`booked_annual_value_usd`) | simple | Sum of won opportunity amounts (12 months of subscription value). | sum(`won_amount_usd`) on `lead_journey` |
| **bot_contained_resolved_sessions** (`bot_contained_resolved_sessions`) | simple | Metric created from measure bot_contained_resolved_sessions | sum(`bot_contained_resolved_count`) on `contacts` |
| **bot_contained_sessions** (`bot_contained_sessions`) | simple | Metric created from measure bot_contained_sessions | sum(`bot_contained_count`) on `contacts` |
| **Bot containment (vendor definition)** (`bot_containment_rate`) | ratio | Bot sessions that never reached an agent / bot sessions. Says nothing about whether the problem was solved. | `bot_contained_sessions` / `bot_sessions` |
| **Bot sessions** (`bot_sessions`) | simple |  | sum(`bot_session_count`) on `contacts` |
| **bot_sessions_observable** (`bot_sessions_observable`) | simple | Metric created from measure bot_sessions_observable | sum(`bot_session_observable_count`) on `contacts` |
| **Bot true resolution** (`bot_true_resolution_rate`) | ratio | Bot sessions that were contained AND had no repeat contact or ticket on the same driver within 7 days / observable bot sessions. | `bot_contained_resolved_sessions` / `bot_sessions_observable` |
| **30-day churn after contact** (`churn_after_contact_rate`) | ratio | Share of contacts whose customer cancelled within 30 days (contacts at least 30 days old). | `churned_after_contact` / `churn_observable_contacts` |
| **churn_observable_contacts** (`churn_observable_contacts`) | simple | Metric created from measure churn_observable_contacts | sum(`case when is_churn_observable and not is_abandoned then 1 else 0 end`) on `contacts` |
| **churned_after_contact** (`churned_after_contact`) | simple | Metric created from measure churned_after_contact | sum(`case when is_churn_observable and not is_abandoned and cancelled_within_30d then 1 else 0 end`) on `contacts` |
| **Contact rate** (`contact_rate`) | ratio | Contacted leads / unique leads. Per lead, not per dial attempt. | `contacted_leads` / `unique_leads` |
| **Contacted leads** (`contacted_leads`) | simple | Unique leads reached by a live conversation on at least one dial attempt. | sum(`contacted_count`) on `lead_journey` |
| **Contacts** (`contacts`) | simple | Customer contacts (sessions) across all channels, including abandoned calls. | count(`session_id`) on `contacts` |
| **Conversion rate** (`conversion_rate`) | ratio | Sales / unique leads, by lead creation date (cohort view). | `sold_leads` / `unique_leads` |
| **Lead cost per activation (USD)** (`cost_per_activation_usd`) | ratio | Lead spend / activations. Acquisition cost on lead spend only (excludes selling labor). | `lead_spend_usd` / `activated_leads` |
| **Cost per contact (USD)** (`cost_per_contact_usd`) | ratio |  | `cost_to_serve_usd_total` / `contacts` |
| **Cost per unique lead (USD)** (`cost_per_lead_usd`) | ratio |  | `lead_spend_usd` / `unique_leads` |
| **Lead cost per sale (USD)** (`cost_per_sale_usd`) | ratio | Lead spend / sales. A vendor that is cheap per lead can be the most expensive per sale. | `lead_spend_usd` / `sold_leads` |
| **Cost to serve (USD)** (`cost_to_serve_usd`) | simple | Agent labor (handle time x loaded hourly rate) plus bot session cost. | sum(`cost_to_serve_usd`) on `contacts` |
| **cost_to_serve_usd_total** (`cost_to_serve_usd_total`) | simple | Metric created from measure cost_to_serve_usd_total | sum(`cost_to_serve_usd`) on `contacts` |
| **Duplicate lead rate** (`duplicate_lead_rate`) | derived | Duplicate lead records / all non-test lead records. | `duplicate_leads / (duplicate_leads + unique_leads)` |
| **Duplicate leads** (`duplicate_leads`) | simple | Later lead records for a person who already had a lead within 30 days. | sum(`duplicate_lead_count`) on `lead_journey` |
| **fcr_eligible_contacts** (`fcr_eligible_contacts`) | simple | Metric created from measure fcr_eligible_contacts | sum(`fcr_eligible_count`) on `contacts` |
| **First-contact resolution** (`fcr_rate`) | ratio | Agent-handled contacts with no repeat contact or ticket on the same driver within 7 days. Only contacts at least 7 days old count. | `fcr_resolved_contacts` / `fcr_eligible_contacts` |
| **fcr_resolved_contacts** (`fcr_resolved_contacts`) | simple | Metric created from measure fcr_resolved_contacts | sum(`fcr_resolved_count`) on `contacts` |
| **Labor cost (USD)** (`labor_cost_usd`) | simple |  | sum(`labor_cost_usd`) on `agent_days` |
| **Lead spend (USD)** (`lead_spend_usd`) | simple | Amount billed by lead vendors. | sum(`spend_usd`) on `marketing_spend` |
| **paid_hours_total** (`paid_hours_total`) | simple | Metric created from measure paid_hours_total | sum(`paid_hours`) on `agent_days` |
| **Qualification rate** (`qualification_rate`) | ratio | Qualified leads (an opportunity was created) / contacted leads. | `qualified_leads` / `contacted_leads` |
| **qualified_leads** (`qualified_leads`) | simple | Metric created from measure qualified_leads | sum(`qualified_count`) on `lead_journey` |
| **Repeat contact rate** (`repeat_contact_rate`) | ratio |  | `repeat_contacts` / `resolution_eligible_contacts` |
| **repeat_contacts** (`repeat_contacts`) | simple | Metric created from measure repeat_contacts | sum(`repeat_contact_count`) on `contacts` |
| **resolution_eligible_contacts** (`resolution_eligible_contacts`) | simple | Metric created from measure resolution_eligible_contacts | sum(`resolution_eligible_count`) on `contacts` |
| **Resolution rate (all channels)** (`resolution_rate`) | ratio | Contacts with no repeat contact or ticket on the same driver within 7 days, across bot and agents. | `resolved_contacts` / `resolution_eligible_contacts` |
| **resolved_contacts** (`resolved_contacts`) | simple | Metric created from measure resolved_contacts | sum(`resolved_count`) on `contacts` |
| **Sales per paid hour** (`sales_per_paid_hour`) | ratio |  | `agent_sales_total` / `paid_hours_total` |
| **Schedule adherence** (`schedule_adherence`) | ratio |  | `adherent_minutes_total` / `scheduled_minutes_total` |
| **scheduled_minutes_total** (`scheduled_minutes_total`) | simple | Metric created from measure scheduled_minutes_total | sum(`scheduled_minutes`) on `agent_days` |
| **Sales** (`sold_leads`) | simple | Unique leads with a won opportunity. | sum(`sold_count`) on `lead_journey` |
| **sold_not_activated_leads** (`sold_not_activated_leads`) | simple | Metric created from measure sold_not_activated_leads | sum(`case when is_sold_not_activated then 1 else 0 end`) on `lead_journey` |
| **Sold but not activated** (`sold_not_activated_rate`) | ratio | Share of sales that never became an active subscription (revenue leakage after the sale). | `sold_not_activated_leads` / `sold_leads` |
| **speed_to_lead_minutes_total** (`speed_to_lead_minutes_total`) | simple | Metric created from measure speed_to_lead_minutes_total | sum(`speed_to_lead_business_minutes`) on `lead_journey` |
| **Unique leads** (`unique_leads`) | simple | First lead per person within a 30-day window. Test leads and vendor resubmissions excluded. | count(`lead_id`) on `lead_journey` |
