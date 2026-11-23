select
    f.participation_key,
    b.beneficiary_id,
    p.programme_name,
    l.province,
    d.full_date as participation_date,
    f.participation_count
from {{ source('warehouse', 'fact_beneficiary_participation') }} f
join {{ source('warehouse', 'dim_beneficiary') }} b
  on b.beneficiary_key = f.beneficiary_key
join {{ source('warehouse', 'dim_programme') }} p
  on p.programme_key = f.programme_key
join {{ source('warehouse', 'dim_location') }} l
  on l.location_key = f.location_key
join {{ source('warehouse', 'dim_date') }} d
  on d.date_key = f.date_key
