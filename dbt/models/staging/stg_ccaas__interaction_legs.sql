-- Grain: one row per interaction leg. A session (customer contact) has one or more legs.
select
    leg_id,
    session_id,
    leg_sequence,
    channel,
    queue_name,
    agent_id,
    {{ normalize_phone('customer_phone') }}     as customer_phone,
    {{ normalize_email('customer_email') }}     as customer_email,
    started_at                                  as started_at_utc,
    ended_at                                    as ended_at_utc,
    talk_seconds,
    hold_seconds,
    wrap_seconds,
    case when agent_id is not null then talk_seconds + hold_seconds + wrap_seconds else 0 end as agent_handle_seconds,
    abandoned                                   as is_abandoned,
    transferred                                 as is_transferred,
    bot_contained                               as is_bot_contained,
    agent_marked_resolved                       as is_agent_marked_resolved,
    case when intent_code in ('UNKNOWN', 'OTHER') then null else intent_code end as intent_code,
    intent_code                                 as source_intent_code
from {{ source('ccaas', 'interaction_legs') }}
