{#- Ten-digit US phone number, or null. Strips punctuation and a leading country code. -#}
{% macro normalize_phone(col) -%}
    case
        when length(regexp_replace({{ col }}, '[^0-9]', '', 'g')) = 11
             and left(regexp_replace({{ col }}, '[^0-9]', '', 'g'), 1) = '1'
            then right(regexp_replace({{ col }}, '[^0-9]', '', 'g'), 10)
        when length(regexp_replace({{ col }}, '[^0-9]', '', 'g')) = 10
            then regexp_replace({{ col }}, '[^0-9]', '', 'g')
    end
{%- endmacro %}

{% macro normalize_email(col) -%}
    nullif(lower(trim({{ col }})), '')
{%- endmacro %}

{#- Naive local timestamp in a named zone -> naive UTC timestamp. -#}
{% macro local_to_utc(ts, tz_col) -%}
    timezone('UTC', timezone({{ tz_col }}, {{ ts }}))
{%- endmacro %}

{#- Naive UTC timestamp -> naive local time in the contact center's zone. -#}
{% macro utc_to_center(ts) -%}
    timezone('{{ var("center_timezone") }}', timezone('UTC', {{ ts }}))
{%- endmacro %}
