-- Grain: one row per unique lead.
-- Speed to lead is measured in open (business) minutes: a lead that arrives at 11pm is
-- not "late" until the contact center opens. Clock minutes are kept for comparison.
with g as (
    select
        lead_group_id,
        created_at_utc,
        first_attempt_at_utc,
        {{ utc_to_center('created_at_utc') }}           as created_at_local,
        {{ utc_to_center('first_attempt_at_utc') }}     as first_attempt_at_local
    from {{ ref('int_lead_groups') }}
),

with_start as (
    select
        *,
        {{ next_open('created_at_local') }}             as clock_start_local
    from g
)

select
    lead_group_id,
    created_at_local,
    clock_start_local,
    first_attempt_at_local,
    clock_start_local <> created_at_local               as arrived_after_hours,
    {{ business_minutes_between('clock_start_local', 'first_attempt_at_local') }} as speed_to_lead_business_minutes,
    date_diff('second', created_at_local, first_attempt_at_local) / 60.0           as speed_to_lead_clock_minutes
from with_start
