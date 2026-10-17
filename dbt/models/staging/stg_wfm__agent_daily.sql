-- Grain: one row per agent per scheduled work day.
select
    agent_id,
    cast(work_date as date)             as work_date,
    scheduled_minutes,
    adherent_minutes,
    paid_hours,
    loaded_hourly_rate_usd,
    paid_hours * loaded_hourly_rate_usd as labor_cost_usd
from {{ source('wfm', 'agent_daily') }}
