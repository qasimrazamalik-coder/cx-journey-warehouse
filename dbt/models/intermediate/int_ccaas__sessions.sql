-- Grain: one row per customer contact (CCaaS session), across all its legs.
with legs as (
    select * from {{ ref('stg_ccaas__interaction_legs') }}
),

agg as (
    select
        session_id,
        min(started_at_utc)                                         as started_at_utc,
        max(ended_at_utc)                                           as ended_at_utc,
        count(*)                                                    as leg_count,
        count(agent_id)                                             as agent_leg_count,
        arg_min(channel, leg_sequence)                              as entry_channel,
        bool_or(channel = 'chat_bot')                               as started_with_bot,
        bool_or(channel = 'chat_bot' and is_bot_contained)          as is_bot_contained,
        bool_or(channel = 'chat_bot' and is_transferred)            as is_bot_escalated,
        bool_and(is_abandoned)                                      as is_abandoned,
        count(agent_id) > 1                                         as is_transferred_between_agents,
        sum(agent_handle_seconds)                                   as agent_handle_seconds,
        sum(case when agent_id is not null then talk_seconds + hold_seconds end) as agent_talk_hold_seconds,
        arg_max(agent_id, leg_sequence) filter (where agent_id is not null) as last_agent_id,
        arg_min(agent_id, leg_sequence) filter (where agent_id is not null) as first_agent_id,
        arg_max(queue_name, leg_sequence)                           as last_queue_name,
        -- Prefer the agent's wrap code (last agent leg) over the bot's NLU guess.
        coalesce(
            arg_max(intent_code, leg_sequence) filter (where agent_id is not null and intent_code is not null),
            arg_max(intent_code, leg_sequence) filter (where intent_code is not null)
        )                                                           as intent_code,
        bool_or(is_agent_marked_resolved)                           as is_agent_marked_resolved
    from legs
    group by session_id
)

select
    a.*,
    m.customer_key,
    {{ utc_to_center('a.started_at_utc') }}                         as started_at_local,
    cast({{ utc_to_center('a.started_at_utc') }} as date)           as contact_date
from agg as a
left join {{ ref('int_identity__customer_map') }} as m
    on m.record_type = 'session' and m.record_id = a.session_id
