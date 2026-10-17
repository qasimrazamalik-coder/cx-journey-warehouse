-- Grain: one row per customer contact (session), whatever channel it started in.
--
-- Resolution is judged by what the customer did next, not by what the bot or agent
-- reported: a contact counts as resolved when the same customer did not contact us
-- again about the same driver, or open a ticket about it, within the repeat window.
-- When the driver is unknown (the bot could not classify it), any next contact by the
-- same customer inside the window counts as a repeat, so unclassified sessions are not
-- silently counted as resolved.
-- Contacts too recent for that window to have passed are flagged as not yet observable
-- and excluded from resolution rates.
with sessions as (
    select * from {{ ref('int_ccaas__sessions') }}
),

tickets as (
    select m.customer_key, t.intent_code, t.created_at_utc
    from {{ ref('stg_ticketing__tickets') }} as t
    inner join {{ ref('int_identity__customer_map') }} as m
        on m.record_type = 'ticket' and m.record_id = t.ticket_id
),

data_end as (
    select max(started_at_utc) as max_started_at_utc from sessions
),

next_same_driver as (
    select
        session_id,
        lead(started_at_utc) over (
            partition by customer_key, intent_code order by started_at_utc, session_id
        ) as next_same_driver_contact_at_utc
    from sessions
    where customer_key is not null and intent_code is not null
),

next_any as (
    select
        session_id,
        lead(started_at_utc) over (
            partition by customer_key order by started_at_utc, session_id
        ) as next_any_contact_at_utc
    from sessions
    where customer_key is not null and not is_abandoned
),

ticket_follow_up as (
    select s.session_id, min(t.created_at_utc) as follow_up_ticket_at_utc
    from sessions as s
    inner join tickets as t
        on t.customer_key = s.customer_key
       and t.intent_code = s.intent_code
       and t.created_at_utc > s.started_at_utc
       and t.created_at_utc <= s.started_at_utc + interval '{{ var("repeat_window_days") }} days'
    group by s.session_id
),

agent_rate as (
    select agent_id, work_date, loaded_hourly_rate_usd from {{ ref('stg_wfm__agent_daily') }}
),

customers as (
    select customer_key, cancelled_at_utc from {{ ref('dim_customer') }}
),

enriched as (
    select
        s.*,
        n.next_same_driver_contact_at_utc,
        coalesce(
            case
                when s.intent_code is not null
                    then n.next_same_driver_contact_at_utc <= s.started_at_utc + interval '{{ var("repeat_window_days") }} days'
                else na.next_any_contact_at_utc <= s.started_at_utc + interval '{{ var("repeat_window_days") }} days'
            end,
            false
        )                                                               as has_repeat_contact,
        tf.follow_up_ticket_at_utc is not null                          as has_follow_up_ticket,
        s.started_at_utc <= d.max_started_at_utc - interval '{{ var("repeat_window_days") }} days' as is_outcome_observable,
        s.started_at_utc <= d.max_started_at_utc - interval 30 day     as is_churn_observable,
        coalesce(
            c.cancelled_at_utc > s.started_at_utc
            and c.cancelled_at_utc <= s.started_at_utc + interval 30 day,
            false
        )                                                               as cancelled_within_30d,
        r.loaded_hourly_rate_usd
    from sessions as s
    cross join data_end as d
    left join next_same_driver as n on n.session_id = s.session_id
    left join next_any as na on na.session_id = s.session_id
    left join ticket_follow_up as tf on tf.session_id = s.session_id
    left join customers as c on c.customer_key = s.customer_key
    left join agent_rate as r on r.agent_id = s.last_agent_id and r.work_date = s.contact_date
),

final as (
    select
        session_id,
        customer_key,
        started_at_utc,
        started_at_local,
        contact_date,
        entry_channel,
        case
            when is_abandoned then 'abandoned'
            when started_with_bot and agent_leg_count = 0 then 'bot only'
            when started_with_bot then 'bot then agent'
            else 'agent'
        end                                                             as handling_path,
        coalesce(intent_code, 'UNCLASSIFIED')                           as intent_code,
        leg_count,
        agent_leg_count,
        first_agent_id,
        last_agent_id,
        last_queue_name,
        started_with_bot,
        coalesce(is_bot_contained, false)                               as is_bot_contained,
        coalesce(is_bot_escalated, false)                               as is_bot_escalated,
        is_abandoned,
        is_transferred_between_agents,
        agent_handle_seconds,
        agent_talk_hold_seconds,
        coalesce(is_agent_marked_resolved, false)                       as is_agent_marked_resolved,
        has_repeat_contact,
        has_follow_up_ticket,
        next_same_driver_contact_at_utc,
        is_outcome_observable,
        is_churn_observable,
        cancelled_within_30d,
        (not is_abandoned and customer_key is not null)                 as is_resolution_eligible,
        (not is_abandoned and not has_repeat_contact and not has_follow_up_ticket)   as is_resolved,
        (agent_leg_count > 0 and not is_abandoned)                      as is_agent_handled,
        round(agent_handle_seconds / 3600.0 * coalesce(loaded_hourly_rate_usd, 0), 4) as agent_cost_usd,
        case when started_with_bot then {{ var('bot_cost_per_session_usd') }} else 0 end as bot_cost_usd
    from enriched
)

select
    *,
    agent_cost_usd + bot_cost_usd                                       as cost_to_serve_usd,
    -- 0/1 helper columns so the semantic layer can define rates as sums.
    case when is_agent_handled then 1 else 0 end                        as agent_handled_count,
    case when started_with_bot then 1 else 0 end                        as bot_session_count,
    case when is_bot_contained then 1 else 0 end                        as bot_contained_count,
    case when is_resolution_eligible and is_outcome_observable then 1 else 0 end as resolution_eligible_count,
    case when is_resolution_eligible and is_outcome_observable and is_resolved then 1 else 0 end as resolved_count,
    case when is_agent_handled and is_resolution_eligible and is_outcome_observable then 1 else 0 end as fcr_eligible_count,
    case when is_agent_handled and is_resolution_eligible and is_outcome_observable and is_resolved then 1 else 0 end as fcr_resolved_count,
    case when started_with_bot and is_resolution_eligible and is_outcome_observable then 1 else 0 end as bot_session_observable_count,
    case when is_bot_contained and is_resolution_eligible and is_outcome_observable and is_resolved then 1 else 0 end as bot_contained_resolved_count,
    case when is_resolution_eligible and is_outcome_observable and has_repeat_contact then 1 else 0 end as repeat_contact_count
from final
