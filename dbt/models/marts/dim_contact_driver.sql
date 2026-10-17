-- Grain: one row per contact driver (leaf of the three-level taxonomy), plus Unclassified.
select
    intent_code,
    driver_l1,
    driver_l2,
    driver_l3,
    driver_l1 || ' > ' || driver_l2 || ' > ' || driver_l3   as driver_path,
    is_avoidable,
    upstream_owner
from {{ ref('intent_taxonomy') }}

union all

select 'UNCLASSIFIED', 'Unclassified', 'Unclassified', 'Unclassified',
       'Unclassified', false, 'Analytics (taxonomy coverage)'
