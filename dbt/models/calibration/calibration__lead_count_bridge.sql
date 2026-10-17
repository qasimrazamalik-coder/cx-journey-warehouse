-- Grain: one row per month. Walks the legacy "Leads" number down to the governed
-- unique-lead count, one documented cause at a time. Both checks must be zero
-- (see tests/assert_calibration_bridges_close.sql).
with legacy as (
    select report_month, leads as legacy_reported_leads from {{ ref('stg_legacy_bi__monthly_kpis') }}
),

raw_rows as (
    select
        cast(date_trunc('month', created_at_lead_local) as date)               as report_month,
        count(*)                                                                as raw_lead_rows,
        count(*) filter (where is_test_lead)                                    as test_leads
    from {{ ref('stg_crm__leads') }}
    group by 1
),

dedup as (
    select
        cast(date_trunc('month', created_at_lead_local) as date)               as report_month,
        count(*) filter (where is_duplicate)                                    as duplicate_leads,
        count(*) filter (where not is_duplicate)                                as unique_leads_lead_local_month
    from {{ ref('int_leads__deduplicated') }}
    group by 1
),

governed as (
    select
        cast(date_trunc('month', created_at_local) as date)                    as report_month,
        count(*)                                                                as governed_unique_leads
    from {{ ref('fct_lead_journey') }}
    group by 1
)

select
    l.report_month,
    l.legacy_reported_leads,
    r.raw_lead_rows,
    l.legacy_reported_leads - r.raw_lead_rows                                   as check_legacy_equals_raw_rows,
    -r.test_leads                                                               as step_remove_test_leads,
    -d.duplicate_leads                                                          as step_remove_duplicate_leads,
    d.unique_leads_lead_local_month,
    g.governed_unique_leads - d.unique_leads_lead_local_month                   as step_rebucket_to_center_month,
    g.governed_unique_leads,
    r.raw_lead_rows - r.test_leads - d.duplicate_leads - d.unique_leads_lead_local_month as check_residual
from legacy as l
left join raw_rows as r on r.report_month = l.report_month
left join dedup as d on d.report_month = l.report_month
left join governed as g on g.report_month = l.report_month
