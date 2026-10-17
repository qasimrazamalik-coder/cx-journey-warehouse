-- Grain: one row per calendar day. Required by the dbt semantic layer.
select cast(range as date) as date_day
from range(timestamp '2024-01-01', timestamp '2027-01-01', interval 1 day)
