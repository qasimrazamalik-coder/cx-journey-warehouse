-- Grain: one row per month, as reported by the client's legacy BI.
select
    cast(month as date)     as report_month,
    leads,
    contact_rate,
    conversion_rate,
    handled_contacts,
    aht_seconds,
    fcr_rate,
    bot_containment_rate
from {{ source('legacy_bi', 'monthly_kpis') }}
