-- Grain: one row per identifier-bearing record in any source system.
-- These are the inputs to identity resolution: every record carries an email, a phone, or both.
with leads as (
    select 'lead' as record_type, lead_id as record_id, email, phone
    from {{ ref('stg_crm__leads') }}
    where not is_test_lead
),

accounts as (
    select 'account' as record_type, account_id as record_id, email, phone
    from {{ ref('stg_billing__subscriptions') }}
),

sessions as (
    -- A voice session carries the caller's number, a chat session the login email.
    select 'session' as record_type, session_id as record_id,
           max(customer_email) as email, max(customer_phone) as phone
    from {{ ref('stg_ccaas__interaction_legs') }}
    group by session_id
),

tickets as (
    select 'ticket' as record_type, ticket_id as record_id, requester_email as email, null as phone
    from {{ ref('stg_ticketing__tickets') }}
)

select * from leads    where email is not null or phone is not null
union all
select * from accounts where email is not null or phone is not null
union all
select * from sessions where email is not null or phone is not null
union all
select * from tickets  where email is not null
