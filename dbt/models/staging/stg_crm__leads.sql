-- Grain: one row per CRM lead record (including duplicates and test leads; flagged, not removed).
select
    lead_id,
    trim(vendor_name)                                   as vendor_name,
    trim(campaign_name)                                 as campaign_name,
    trim(first_name)                                    as first_name,
    trim(last_name)                                     as last_name,
    {{ normalize_email('email') }}                      as email,
    {{ normalize_phone('phone') }}                      as phone,
    upper(state)                                        as state,
    created_timezone,
    created_at_local                                    as created_at_lead_local,
    {{ local_to_utc('created_at_local', 'created_timezone') }} as created_at_utc,
    lead_status,
    (
        {{ normalize_email('email') }} like '%@test.northwind.example'
        or upper(trim(first_name)) = 'TEST'
    )                                                   as is_test_lead
from {{ source('crm', 'leads') }}
