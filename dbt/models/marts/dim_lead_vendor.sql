-- Grain: one row per lead vendor (conformed dimension shared by leads and spend).
select distinct vendor_name
from {{ ref('stg_crm__leads') }}
where not is_test_lead
