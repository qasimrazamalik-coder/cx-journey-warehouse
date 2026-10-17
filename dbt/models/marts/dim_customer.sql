-- Grain: one row per resolved customer (person) who has a billing account.
-- If a person has several accounts, the most recent one describes them.
with accounts as (
    select
        m.customer_key,
        s.*
    from {{ ref('stg_billing__subscriptions') }} as s
    inner join {{ ref('int_identity__customer_map') }} as m
        on m.record_type = 'account' and m.record_id = s.account_id
)

select
    customer_key,
    count(*)                                                as account_count,
    arg_max(account_id, started_at_utc)                     as current_account_id,
    arg_max(plan_name, started_at_utc)                      as current_plan_name,
    arg_max(mrr_usd, started_at_utc)                        as current_mrr_usd,
    arg_max(state, started_at_utc)                          as state,
    min(started_at_utc)                                     as first_subscribed_at_utc,
    arg_max(cancelled_at_utc, started_at_utc)               as cancelled_at_utc,
    arg_max(cancel_reason, started_at_utc)                  as cancel_reason,
    arg_max(cancelled_at_utc, started_at_utc) is null       as is_active
from accounts
group by customer_key
