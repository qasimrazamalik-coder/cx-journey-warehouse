{#-
  Business-hours helpers. Inputs are naive timestamps in the contact center's
  local zone. Open hours: var open_hour..close_hour, Monday to Saturday.
-#}

{% macro next_open(ts) -%}
    case
        when isodow({{ ts }}) between 1 and 6
             and hour({{ ts }}) >= {{ var('open_hour') }} and hour({{ ts }}) < {{ var('close_hour') }}
            then {{ ts }}
        when isodow({{ ts }}) between 1 and 6 and hour({{ ts }}) < {{ var('open_hour') }}
            then date_trunc('day', {{ ts }}) + interval '{{ var('open_hour') }} hours'
        when isodow(date_trunc('day', {{ ts }}) + interval 1 day) = 7
            then date_trunc('day', {{ ts }}) + interval 2 day + interval '{{ var('open_hour') }} hours'
        else date_trunc('day', {{ ts }}) + interval 1 day + interval '{{ var('open_hour') }} hours'
    end
{%- endmacro %}

{#-
  Open minutes between two local timestamps that both fall inside open hours.
  Same day: plain difference. Otherwise: rest of the first day + start of the
  last day + 12 open hours for each full open day in between (Sundays skipped).
-#}
{% macro business_minutes_between(start_ts, end_ts) -%}
    case
        when {{ end_ts }} is null or {{ start_ts }} is null then null
        when {{ end_ts }} <= {{ start_ts }} then 0
        when cast({{ start_ts }} as date) = cast({{ end_ts }} as date)
            then date_diff('second', {{ start_ts }}, {{ end_ts }}) / 60.0
        else
            date_diff('second', {{ start_ts }},
                      date_trunc('day', {{ start_ts }}) + interval '{{ var('close_hour') }} hours') / 60.0
          + date_diff('second', date_trunc('day', {{ end_ts }}) + interval '{{ var('open_hour') }} hours',
                      {{ end_ts }}) / 60.0
          + 60.0 * ({{ var('close_hour') }} - {{ var('open_hour') }}) * (
                date_diff('day', cast({{ start_ts }} as date), cast({{ end_ts }} as date)) - 1
              - {{ sundays_strictly_between('cast(' ~ start_ts ~ ' as date)', 'cast(' ~ end_ts ~ ' as date)') }}
            )
    end
{%- endmacro %}

{#- Number of Sundays strictly between two dates, without generating rows. -#}
{% macro sundays_strictly_between(d1, d2) -%}
    (
        floor((date_diff('day', date '2023-01-01', {{ d2 }}) - 1) / 7)
      - floor(date_diff('day', date '2023-01-01', {{ d1 }}) / 7)
    )
{%- endmacro %}
