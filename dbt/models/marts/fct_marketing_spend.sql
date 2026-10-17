-- Grain: one row per vendor per campaign per day.
select
    md5(vendor_name || '|' || campaign_name || '|' || cast(spend_date as varchar)) as spend_key,
    *
from {{ ref('stg_marketing__vendor_spend') }}
