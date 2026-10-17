-- Every calibration bridge must close exactly: the legacy number is reproduced from raw
-- data, and the steps add up to the governed number with nothing unexplained.
select report_month, 'lead bridge: legacy != raw rows' as failure
from {{ ref('calibration__lead_count_bridge') }}
where check_legacy_equals_raw_rows <> 0
union all
select report_month, 'lead bridge: residual not zero'
from {{ ref('calibration__lead_count_bridge') }}
where check_residual <> 0
union all
select report_month, 'aht bridge: recompute does not match legacy'
from {{ ref('calibration__aht_bridge') }}
where abs(check_recompute_matches_legacy) > 0.15
union all
select report_month, 'aht bridge: steps do not add up'
from {{ ref('calibration__aht_bridge') }}
where abs(legacy_recomputed + step_add_wrap_time + step_count_contacts_not_legs + step_rebucket_to_center_month - governed) > 0.3
