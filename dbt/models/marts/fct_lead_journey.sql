-- Grain: one row per unique lead (accumulating snapshot):
-- created -> first attempt -> first contact -> qualified -> sold -> activated.
with groups as (
    select * from {{ ref('int_lead_groups') }}
),

speed as (
    select * from {{ ref('int_leads__speed_to_lead') }}
),

lead_to_group as (
    select lead_id, lead_group_id from {{ ref('int_leads__deduplicated') }}
),

opps as (
    select
        lg.lead_group_id,
        count(*)                                        as opportunity_count,
        bool_or(o.is_won)                               as is_won,
        max(o.amount_usd) filter (where o.is_won)       as won_amount_usd,
        min(o.created_at_utc)                           as qualified_at_utc
    from {{ ref('stg_crm__opportunities') }} as o
    inner join lead_to_group as lg on lg.lead_id = o.lead_id
    group by lg.lead_group_id
),

accounts as (
    select m.customer_key, s.account_id, s.started_at_utc, s.mrr_usd
    from {{ ref('stg_billing__subscriptions') }} as s
    inner join {{ ref('int_identity__customer_map') }} as m
        on m.record_type = 'account' and m.record_id = s.account_id
),

journey as (
    select
        g.*,
        s.created_at_local,
        s.arrived_after_hours,
        s.speed_to_lead_business_minutes,
        s.speed_to_lead_clock_minutes,
        coalesce(o.opportunity_count, 0) > 0            as is_qualified,
        o.qualified_at_utc,
        coalesce(o.is_won, false)                       as is_sold,
        o.won_amount_usd,
        g.sale_attempt_at_utc                           as sold_at_utc
    from groups as g
    left join speed as s on s.lead_group_id = g.lead_group_id
    left join opps as o on o.lead_group_id = g.lead_group_id
),

activation as (
    -- The first account the customer started within 45 days after the sale.
    select
        j.lead_group_id,
        min(a.started_at_utc)                           as activated_at_utc,
        arg_min(a.account_id, a.started_at_utc)         as activated_account_id,
        arg_min(a.mrr_usd, a.started_at_utc)            as activated_mrr_usd
    from journey as j
    inner join accounts as a
        on a.customer_key = j.customer_key
       and a.started_at_utc >= j.sold_at_utc
       and a.started_at_utc < j.sold_at_utc + interval 45 day
    where j.is_sold
    group by j.lead_group_id
)

select
    j.lead_group_id                                     as lead_id,
    j.customer_key,
    j.vendor_name,
    j.campaign_name,
    j.state,
    j.created_at_utc,
    j.created_at_local,
    cast(j.created_at_local as date)                    as created_date,
    j.arrived_after_hours,
    j.duplicate_lead_count,
    j.duplicate_vendor_names,
    j.first_attempt_at_utc,
    j.first_attempt_agent_id,
    ag.site                                             as first_attempt_site,
    j.attempt_count,
    j.speed_to_lead_business_minutes,
    j.speed_to_lead_clock_minutes,
    case
        when j.first_attempt_at_utc is null then 'never attempted'
        when j.speed_to_lead_business_minutes <= 5 then '0-5 min'
        when j.speed_to_lead_business_minutes <= 15 then '5-15 min'
        when j.speed_to_lead_business_minutes <= 30 then '15-30 min'
        when j.speed_to_lead_business_minutes <= 60 then '30-60 min'
        else '60+ min'
    end                                                 as speed_to_lead_band,
    j.first_contact_at_utc,
    j.is_contacted,
    j.is_qualified,
    j.qualified_at_utc,
    j.is_sold,
    j.sold_at_utc,
    j.won_amount_usd,
    act.activated_at_utc is not null                    as is_activated,
    act.activated_at_utc,
    act.activated_account_id,
    act.activated_mrr_usd,
    j.is_sold and act.activated_at_utc is null          as is_sold_not_activated,
    case when j.is_contacted then 1 else 0 end          as contacted_count,
    case when j.is_qualified then 1 else 0 end          as qualified_count,
    case when j.is_sold then 1 else 0 end               as sold_count,
    case when act.activated_at_utc is not null then 1 else 0 end as activated_count
from journey as j
left join activation as act on act.lead_group_id = j.lead_group_id
left join {{ ref('dim_agent') }} as ag
    on ag.agent_id = j.first_attempt_agent_id
   and cast(j.first_attempt_at_utc as date) >= ag.valid_from
   and (ag.valid_to is null or cast(j.first_attempt_at_utc as date) < ag.valid_to)
