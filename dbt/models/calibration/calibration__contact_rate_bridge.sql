-- Grain: one row per month. Contact rate: the legacy report counts connected dial
-- attempts using only the dialer's original disposition codes, so it fell to zero
-- when the vendor renamed the codes on 2025-04-01. The governed metric is the share
-- of unique leads ever reached.
with attempts as (
    select
        cast(date_trunc('month', started_at_utc) as date)                   as report_month,
        avg(case when is_connected then 1.0 else 0 end)                     as attempt_level_all_codes
    from {{ ref('fct_dial_attempts') }}
    group by 1
),

legacy as (
    select report_month, contact_rate as legacy_reported from {{ ref('stg_legacy_bi__monthly_kpis') }}
),

governed as (
    select report_month, contact_rate as governed from {{ ref('mart_monthly_kpis') }}
)

select
    l.report_month,
    l.legacy_reported,
    round(a.attempt_level_all_codes, 4)                                     as attempt_level_with_full_code_map,
    round(a.attempt_level_all_codes - l.legacy_reported, 4)                 as step_map_renamed_codes,
    round(g.governed - a.attempt_level_all_codes, 4)                        as step_measure_per_lead_not_attempt,
    g.governed
from legacy as l
left join attempts as a on a.report_month = l.report_month
left join governed as g on g.report_month = l.report_month
