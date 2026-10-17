-- Grain: one row per unique lead (lead group). A group is the first lead for a person
-- plus any duplicates that arrived within the duplicate window. Dial attempts on any
-- lead in the group count toward the group, because the dialer works duplicates too.
with leads as (
    select * from {{ ref('int_leads__deduplicated') }}
),

attempts as (
    select
        l.lead_group_id,
        a.started_at_utc,
        a.agent_id,
        a.is_connected,
        a.is_sale
    from {{ ref('fct_dial_attempts') }} as a
    inner join leads as l on l.lead_id = a.lead_id
),

attempt_agg as (
    select
        lead_group_id,
        min(started_at_utc)                                 as first_attempt_at_utc,
        arg_min(agent_id, started_at_utc)                   as first_attempt_agent_id,
        count(*)                                            as attempt_count,
        min(started_at_utc) filter (where is_connected)     as first_contact_at_utc,
        bool_or(is_connected)                               as is_contacted,
        min(started_at_utc) filter (where is_sale)          as sale_attempt_at_utc
    from attempts
    group by lead_group_id
),

groups as (
    select
        lead_group_id,
        count(*) - 1                                        as duplicate_lead_count,
        list(distinct vendor_name) filter (where is_duplicate) as duplicate_vendor_names
    from leads
    group by lead_group_id
)

select
    l.lead_id                                               as lead_group_id,
    l.customer_key,
    l.vendor_name,
    l.campaign_name,
    l.state,
    l.created_at_utc,
    g.duplicate_lead_count,
    g.duplicate_vendor_names,
    a.first_attempt_at_utc,
    a.first_attempt_agent_id,
    coalesce(a.attempt_count, 0)                            as attempt_count,
    a.first_contact_at_utc,
    coalesce(a.is_contacted, false)                         as is_contacted,
    a.sale_attempt_at_utc
from leads as l
inner join groups as g on g.lead_group_id = l.lead_id
left join attempt_agg as a on a.lead_group_id = l.lead_id
where not l.is_duplicate
