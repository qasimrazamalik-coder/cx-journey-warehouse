-- Grain: one row per vendor per campaign per day.
select
    cast(spend_date as date)            as spend_date,
    vendor_name,
    campaign_name,
    billed_leads,
    cast(spend_usd as decimal(12, 2))   as spend_usd
from {{ source('marketing', 'vendor_spend') }}
