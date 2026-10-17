-- Grain: one row per non-test CRM lead, with the person it belongs to and whether it is a duplicate.
-- A lead is a duplicate if the same customer already had a lead within the duplicate window.
-- The first lead keeps the vendor credit; duplicates are kept for vendor billing disputes.
with leads as (
    select
        l.*,
        m.customer_key
    from {{ ref('stg_crm__leads') }} as l
    inner join {{ ref('int_identity__customer_map') }} as m
        on m.record_type = 'lead' and m.record_id = l.lead_id
    where not l.is_test_lead
),

ordered as (
    select
        *,
        lag(created_at_utc) over (partition by customer_key order by created_at_utc, lead_id) as previous_lead_at_utc,
        row_number() over (partition by customer_key order by created_at_utc, lead_id) as lead_sequence_for_customer
    from leads
),

flagged as (
    select
        *,
        coalesce(
            date_diff('second', previous_lead_at_utc, created_at_utc)
                < {{ var('duplicate_lead_window_days') }} * 86400,
            false
        ) as is_duplicate
    from ordered
)

select
    *,
    -- Every duplicate belongs to the most recent non-duplicate lead of the same customer.
    last_value(case when not is_duplicate then lead_id end ignore nulls) over (
        partition by customer_key order by created_at_utc, lead_id
        rows between unbounded preceding and current row
    ) as lead_group_id
from flagged
