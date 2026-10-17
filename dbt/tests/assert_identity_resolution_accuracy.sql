-- Identity resolution must recover the true people behind lead and billing records.
-- Purity: share of resolved customers whose records all belong to one true person.
-- Completeness: share of true people whose records all landed in one customer.
-- Fails if either is below 99%.
with resolved as (
    select m.customer_key, t.person_id
    from {{ ref('int_identity__customer_map') }} as m
    inner join {{ source('truth', 'lead_person') }} as t
        on m.record_type = 'lead' and m.record_id = t.lead_id
    union all
    select m.customer_key, t.person_id
    from {{ ref('int_identity__customer_map') }} as m
    inner join {{ source('truth', 'account_person') }} as t
        on m.record_type = 'account' and m.record_id = t.account_id
),

purity as (
    select avg(case when n = 1 then 1.0 else 0 end) as value
    from (select customer_key, count(distinct person_id) as n from resolved group by 1)
),

completeness as (
    select avg(case when n = 1 then 1.0 else 0 end) as value
    from (select person_id, count(distinct customer_key) as n from resolved group by 1)
)

select p.value as purity, c.value as completeness
from purity as p cross join completeness as c
where p.value < 0.99 or c.value < 0.99
