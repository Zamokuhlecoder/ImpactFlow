select
    province,
    count(distinct programme_name) as programmes,
    sum(participation_count) as participants,
    count(*) as participation_records
from {{ ref('stg_beneficiary_participation') }}
group by province
