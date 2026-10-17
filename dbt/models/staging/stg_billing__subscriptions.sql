-- Grain: one row per subscription (one account per subscription in this client's billing system).
select
    subscription_id,
    account_id,
    {{ normalize_email('email') }}      as email,
    {{ normalize_phone('phone') }}      as phone,
    trim(first_name)                    as first_name,
    trim(last_name)                     as last_name,
    upper(state)                        as state,
    plan_name,
    cast(mrr_usd as decimal(10, 2))     as mrr_usd,
    started_at                          as started_at_utc,
    cancelled_at                        as cancelled_at_utc,
    cancel_reason
from {{ source('billing', 'subscriptions') }}
