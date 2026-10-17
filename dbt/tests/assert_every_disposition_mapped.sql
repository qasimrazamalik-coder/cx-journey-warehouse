-- A new or renamed disposition code must be added to the disposition_map seed before
-- it reaches the marts; otherwise contact and sale rates silently break.
select source_disposition_code, count(*) as attempts
from {{ ref('stg_dialer__call_attempts') }}
where outcome is null
group by 1
