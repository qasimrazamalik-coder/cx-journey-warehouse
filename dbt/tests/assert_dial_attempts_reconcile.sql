-- No dial attempt is lost or duplicated between staging and the fact table.
select s.n as staging_rows, f.n as fact_rows
from (select count(*) as n from {{ ref('stg_dialer__call_attempts') }}) as s
cross join (select count(*) as n from {{ ref('fct_dial_attempts') }}) as f
where s.n <> f.n
