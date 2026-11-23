select
    programme_name as programme,
    province,
    sum(target_value) as target,
    sum(actual_value) as actual,
    case
        when sum(target_value) = 0 then null
        else round(
            (sum(actual_value) / nullif(sum(target_value), 0) * 100)::numeric,
            2
        )
    end as achievement_percentage
from {{ ref('stg_programme_outcomes') }}
group by programme_name, province
