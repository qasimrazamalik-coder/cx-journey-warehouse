-- Grain: one row per month. Average handle time: from the legacy definition
-- (talk + hold per agent leg, UTC month) to the governed one (talk + hold + wrap per
-- handled contact, contact-center month), one change at a time.
with legs as (
    select
        l.*,
        cast(date_trunc('month', l.started_at_utc) as date) as utc_month
    from {{ ref('stg_ccaas__interaction_legs') }} as l
    where l.agent_id is not null
),

per_leg as (
    select
        utc_month                                                   as report_month,
        avg(talk_seconds + hold_seconds)                            as legacy_recomputed,
        avg(talk_seconds + hold_seconds + wrap_seconds)             as with_wrap_per_leg
    from legs
    group by 1
),

per_contact_utc as (
    select
        cast(date_trunc('month', started_at_utc) as date)           as report_month,
        sum(agent_handle_seconds) / count(*)                        as with_wrap_per_contact_utc_month
    from {{ ref('fct_contacts') }}
    where is_agent_handled
    group by 1
),

legacy as (
    select report_month, aht_seconds as legacy_reported from {{ ref('stg_legacy_bi__monthly_kpis') }}
),

governed as (
    select report_month, aht_seconds as governed from {{ ref('mart_monthly_kpis') }}
)

select
    l.report_month,
    l.legacy_reported,
    round(p.legacy_recomputed, 1)                                               as legacy_recomputed,
    round(p.with_wrap_per_leg - p.legacy_recomputed, 1)                         as step_add_wrap_time,
    round(c.with_wrap_per_contact_utc_month - p.with_wrap_per_leg, 1)           as step_count_contacts_not_legs,
    round(g.governed - c.with_wrap_per_contact_utc_month, 1)                    as step_rebucket_to_center_month,
    g.governed,
    round(l.legacy_reported - p.legacy_recomputed, 1)                           as check_recompute_matches_legacy
from legacy as l
left join per_leg as p on p.report_month = l.report_month
left join per_contact_utc as c on c.report_month = l.report_month
left join governed as g on g.report_month = l.report_month
