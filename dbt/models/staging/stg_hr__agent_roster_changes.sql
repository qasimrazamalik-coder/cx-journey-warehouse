-- Grain: one row per agent per roster change (effective date).
select
    agent_id,
    agent_name,
    site,
    role,
    tier,
    supervisor_id,
    status,
    cast(effective_date as date)    as effective_date,
    cast(hire_date as date)         as hire_date
from {{ source('hr', 'agent_roster_changes') }}
