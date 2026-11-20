-- The random policy's pool has 7,583 videos (paper Sec. 3.2, HC 2). Returns a row if the count differs.
{{ config(severity='warn') }}

select count(*) as n_pool_videos
from {{ ref('int_pool_videos') }}
having count(*) != 7583
