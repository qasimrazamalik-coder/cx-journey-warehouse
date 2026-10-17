-- Grain: one row per agent per version (SCD type 2). valid_to is exclusive; null means current.
-- Join facts on agent_id and event date between valid_from and valid_to to get the
-- agent's tier, supervisor and status as they were at the time.
with changes as (
    select *
    from {{ ref('stg_hr__agent_roster_changes') }}
    -- Two changes on the same day: keep the terminating one.
    qualify row_number() over (partition by agent_id, effective_date order by status desc) = 1
)

select
    md5(agent_id || '|' || cast(effective_date as varchar))     as agent_version_key,
    agent_id,
    agent_name,
    site,
    role,
    tier,
    supervisor_id,
    status,
    hire_date,
    effective_date                                              as valid_from,
    lead(effective_date) over (partition by agent_id order by effective_date) as valid_to,
    lead(effective_date) over (partition by agent_id order by effective_date) is null as is_current
from changes
