select
    f.outcome_key,
    p.programme_name,
    l.province,
    i.indicator_name,
    d.full_date as outcome_date,
    f.target_value,
    f.actual_value,
    f.achievement_percentage
from {{ source('warehouse', 'fact_programme_outcomes') }} f
join {{ source('warehouse', 'dim_programme') }} p
  on p.programme_key = f.programme_key
join {{ source('warehouse', 'dim_location') }} l
  on l.location_key = f.location_key
join {{ source('warehouse', 'dim_indicator') }} i
  on i.indicator_key = f.indicator_key
join {{ source('warehouse', 'dim_date') }} d
  on d.date_key = f.date_key
