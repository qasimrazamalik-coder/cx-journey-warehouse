-- Funnel stages must be in order: activated => sold => qualified => contacted => attempted.
select lead_id
from {{ ref('fct_lead_journey') }}
where (is_activated and not is_sold)
   or (is_sold and not is_qualified)
   or (is_sold and not is_contacted)
   or (is_contacted and first_attempt_at_utc is null)
   or speed_to_lead_business_minutes < 0
