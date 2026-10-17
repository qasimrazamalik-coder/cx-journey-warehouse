{{
    config(
        materialized='incremental',
        unique_key='attempt_id',
        incremental_strategy='delete+insert',
        on_schema_change='fail'
    )
}}
-- Grain: one row per outbound dial attempt.
-- Incremental: each run reprocesses rows loaded in the last N days (var
-- incremental_lookback_days) so late-arriving dialer rows are picked up.
with attempts as (
    select *
    from {{ ref('stg_dialer__call_attempts') }}
    {% if is_incremental() %}
    where loaded_at > (select max(loaded_at) from {{ this }}) - interval '{{ var("incremental_lookback_days") }} days'
    {% endif %}
)

select
    a.attempt_id,
    a.lead_id,
    a.agent_id,
    ag.agent_version_key,
    ag.site                                             as agent_site,
    ag.tier                                             as agent_tier,
    a.campaign_name,
    a.attempt_number,
    a.started_at_utc,
    {{ utc_to_center('a.started_at_utc') }}             as started_at_local,
    cast({{ utc_to_center('a.started_at_utc') }} as date) as attempt_date,
    a.ring_seconds,
    a.talk_seconds,
    a.hold_seconds,
    a.wrap_seconds,
    a.talk_seconds + a.hold_seconds + a.wrap_seconds    as handle_seconds,
    a.source_disposition_code,
    a.outcome,
    a.is_connected,
    a.is_sale,
    a.loaded_at
from attempts as a
left join {{ ref('dim_agent') }} as ag
    on ag.agent_id = a.agent_id
   and cast(a.started_at_utc as date) >= ag.valid_from
   and (ag.valid_to is null or cast(a.started_at_utc as date) < ag.valid_to)
