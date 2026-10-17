-- Grain: one row per agent per scheduled work day.
with wfm as (
    select * from {{ ref('stg_wfm__agent_daily') }}
),

dials as (
    select
        agent_id,
        attempt_date                                    as work_date,
        count(*)                                        as dial_attempts,
        count(*) filter (where is_connected)            as connected_dials,
        count(*) filter (where is_sale)                 as sales,
        sum(handle_seconds)                             as dialer_handle_seconds
    from {{ ref('fct_dial_attempts') }}
    group by 1, 2
),

contacts as (
    select
        last_agent_id                                   as agent_id,
        contact_date                                    as work_date,
        count(*)                                        as handled_contacts,
        sum(agent_handle_seconds)                       as support_handle_seconds,
        sum(fcr_eligible_count)                         as fcr_eligible_contacts,
        sum(fcr_resolved_count)                         as fcr_resolved_contacts
    from {{ ref('fct_contacts') }}
    where is_agent_handled
    group by 1, 2
),

qa as (
    select
        agent_id,
        cast(evaluated_at_utc as date)                  as work_date,
        count(*)                                        as qa_evaluations,
        sum(overall_score)                              as qa_score_total
    from {{ ref('stg_qa__evaluations') }}
    group by 1, 2
)

select
    w.agent_id,
    w.work_date,
    ag.agent_version_key,
    ag.site,
    ag.role,
    ag.tier,
    ag.supervisor_id,
    date_diff('day', ag.hire_date, w.work_date)         as tenure_days,
    w.scheduled_minutes,
    w.adherent_minutes,
    w.paid_hours,
    w.labor_cost_usd,
    coalesce(d.dial_attempts, 0)                        as dial_attempts,
    coalesce(d.connected_dials, 0)                      as connected_dials,
    coalesce(d.sales, 0)                                as sales,
    coalesce(d.dialer_handle_seconds, 0)                as dialer_handle_seconds,
    coalesce(c.handled_contacts, 0)                     as handled_contacts,
    coalesce(c.support_handle_seconds, 0)               as support_handle_seconds,
    coalesce(c.fcr_eligible_contacts, 0)                as fcr_eligible_contacts,
    coalesce(c.fcr_resolved_contacts, 0)                as fcr_resolved_contacts,
    coalesce(q.qa_evaluations, 0)                       as qa_evaluations,
    coalesce(q.qa_score_total, 0)                       as qa_score_total
from wfm as w
left join {{ ref('dim_agent') }} as ag
    on ag.agent_id = w.agent_id
   and w.work_date >= ag.valid_from
   and (ag.valid_to is null or w.work_date < ag.valid_to)
left join dials as d on d.agent_id = w.agent_id and d.work_date = w.work_date
left join contacts as c on c.agent_id = w.agent_id and c.work_date = w.work_date
left join qa as q on q.agent_id = w.agent_id and q.work_date = w.work_date
