-- Grain: one row per month (contact-center local time). Governed definitions of the
-- KPIs in the client's executive pack. These are the numbers the calibration models
-- reconcile against the legacy report.
with leads as (
    select
        date_trunc('month', created_at_local)           as report_month,
        count(*)                                        as unique_leads,
        avg(case when is_contacted then 1.0 else 0 end) as contact_rate,
        avg(case when is_sold then 1.0 else 0 end)      as conversion_rate,
        median(speed_to_lead_business_minutes)          as median_speed_to_lead_minutes
    from {{ ref('fct_lead_journey') }}
    group by 1
),

contacts as (
    select
        date_trunc('month', started_at_local)           as report_month,
        sum(agent_handled_count)                        as handled_contacts,
        sum(agent_handle_seconds) filter (where is_agent_handled)
            / nullif(sum(agent_handled_count), 0)       as aht_seconds,
        sum(fcr_resolved_count) * 1.0 / nullif(sum(fcr_eligible_count), 0) as fcr_rate,
        sum(bot_contained_count) * 1.0 / nullif(sum(bot_session_count), 0) as bot_containment_rate,
        sum(bot_contained_resolved_count) * 1.0 / nullif(sum(bot_session_observable_count), 0) as bot_true_resolution_rate
    from {{ ref('fct_contacts') }}
    group by 1
)

select
    cast(coalesce(l.report_month, c.report_month) as date) as report_month,
    l.unique_leads,
    round(l.contact_rate, 4)                            as contact_rate,
    round(l.conversion_rate, 4)                         as conversion_rate,
    round(l.median_speed_to_lead_minutes, 1)            as median_speed_to_lead_minutes,
    c.handled_contacts,
    round(c.aht_seconds, 1)                             as aht_seconds,
    round(c.fcr_rate, 4)                                as fcr_rate,
    round(c.bot_containment_rate, 4)                    as bot_containment_rate,
    round(c.bot_true_resolution_rate, 4)                as bot_true_resolution_rate
from leads as l
full outer join contacts as c on c.report_month = l.report_month
where coalesce(l.report_month, c.report_month) between date '2025-01-01' and date '2025-06-01'
