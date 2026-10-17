-- Grain: one row per dial attempt. Both dialer layouts land in this one shape, so
-- everything downstream is vendor-independent. Onboarding a new dialer means adding
-- one branch here plus its codes in the disposition_map seed.
with attempts as (
{% if var('dialer_format') == 'classic' %}
    select
        attempt_id,
        lead_id,
        agent_id,
        campaign_name,
        attempt_number,
        started_at_utc,
        ring_seconds,
        talk_seconds,
        hold_seconds,
        wrap_seconds,
        disposition_code                as source_disposition_code,
        dialed_number,
        _loaded_at                      as loaded_at
    from {{ source('dialer', 'call_attempts') }}
{% elif var('dialer_format') == 'events' %}
    select
        call_id                         as attempt_id,
        crm_lead_ref                    as lead_id,
        user_id                         as agent_id,
        list_name                       as campaign_name,
        seq                             as attempt_number,
        make_timestamp(start_epoch * 1000000) as started_at_utc,
        ring_ms // 1000                 as ring_seconds,
        talk_ms // 1000                 as talk_seconds,
        hold_ms // 1000                 as hold_seconds,
        acw_ms // 1000                  as wrap_seconds,
        result                          as source_disposition_code,
        to_number                       as dialed_number,
        _loaded_at                      as loaded_at
    from {{ source('dialer', 'call_events') }}
{% else %}
    {{ exceptions.raise_compiler_error("Unknown dialer_format: " ~ var('dialer_format')) }}
{% endif %}
)

select
    a.attempt_id,
    a.lead_id,
    a.agent_id,
    a.campaign_name,
    a.attempt_number,
    a.started_at_utc,
    a.ring_seconds,
    a.talk_seconds,
    a.hold_seconds,
    a.wrap_seconds,
    a.source_disposition_code,
    m.outcome,
    coalesce(m.is_connected, false)     as is_connected,
    coalesce(m.is_sale, false)          as is_sale,
    {{ normalize_phone('a.dialed_number') }} as dialed_phone,
    a.loaded_at
from attempts as a
left join {{ ref('disposition_map') }} as m
    on a.source_disposition_code = m.source_code
