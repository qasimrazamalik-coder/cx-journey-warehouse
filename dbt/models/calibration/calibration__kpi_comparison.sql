-- Grain: one row per month per KPI. Legacy value next to the governed value, with the
-- root cause of the gap in plain language for the go-live review.
with legacy as (
    select * from {{ ref('stg_legacy_bi__monthly_kpis') }}
),

governed as (
    select * from {{ ref('mart_monthly_kpis') }}
),

pairs as (
    {% set kpis = [
        ('Leads', 'leads', 'unique_leads', 'Legacy counts test leads and vendor resubmissions; governed counts unique people within a 30-day window.'),
        ('Contact rate', 'contact_rate', 'contact_rate', 'Legacy is per dial attempt and ignores disposition codes renamed on 2025-04-01; governed is the share of unique leads reached.'),
        ('Conversion rate', 'conversion_rate', 'conversion_rate', 'Legacy divides wins closed in the month by every lead row; governed follows each unique lead to its own outcome.'),
        ('Handled contacts', 'handled_contacts', 'handled_contacts', 'Legacy counts agent legs, so a transfer counts twice; governed counts customer contacts.'),
        ('AHT (seconds)', 'aht_seconds', 'aht_seconds', 'Legacy drops wrap time and averages per leg; governed is talk + hold + wrap per handled contact.'),
        ('FCR', 'fcr_rate', 'fcr_rate', 'Legacy is the share of legs agents marked resolved; governed checks for a repeat contact or ticket on the same driver within 7 days.'),
        ('Bot containment', 'bot_containment_rate', 'bot_containment_rate', 'Definitions match (vendor flag); small gaps come from UTC vs local month bucketing. See bot true resolution for the outcome view.'),
    ] %}
    {% for label, legacy_col, governed_col, cause in kpis %}
    select
        l.report_month,
        {{ loop.index }}                                    as kpi_order,
        '{{ label }}'                                       as kpi,
        cast(l.{{ legacy_col }} as double)                  as legacy_value,
        cast(g.{{ governed_col }} as double)                as governed_value,
        '{{ cause }}'                                       as root_cause
    from legacy as l
    left join governed as g on g.report_month = l.report_month
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

select
    *,
    governed_value - legacy_value                           as difference,
    round((governed_value - legacy_value) / nullif(legacy_value, 0), 4) as relative_difference
from pairs
