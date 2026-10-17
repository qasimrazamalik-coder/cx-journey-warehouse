-- Grain: one row per opportunity.
select
    opportunity_id,
    lead_id,
    owner_agent_id,
    created_at                          as created_at_utc,
    stage_name,
    stage_name = 'Closed Won'           as is_won,
    cast(close_date as date)            as close_date,
    cast(amount_usd as decimal(12, 2))  as amount_usd
from {{ source('crm', 'opportunities') }}
