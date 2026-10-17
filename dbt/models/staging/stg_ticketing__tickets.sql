-- Grain: one row per ticket.
select
    ticket_id,
    {{ normalize_email('requester_email') }}   as requester_email,
    subject_category                            as intent_code,
    created_at                                  as created_at_utc,
    status,
    solved_at                                   as solved_at_utc
from {{ source('ticketing', 'tickets') }}
