-- Non-test, non-duplicate leads and journey rows must match one to one.
with expected as (
    select lead_id from {{ ref('int_leads__deduplicated') }} where not is_duplicate
)
select coalesce(e.lead_id, j.lead_id) as lead_id
from expected as e
full outer join {{ ref('fct_lead_journey') }} as j on j.lead_id = e.lead_id
where e.lead_id is null or j.lead_id is null
