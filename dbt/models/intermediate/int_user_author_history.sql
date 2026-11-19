{{ config(cluster_by=['user_id']) }}

-- D32: (user, author) pairs with any pre-period exposure, on any tab. An author absent here is new to
-- the user for the new-author follow rate (D33). Treatment-window exposures never enter the history.
select distinct
    {{ dbt_utils.generate_surrogate_key(['user_id', 'author_id']) }} as user_author_key,
    user_id,
    author_id
from {{ ref('int_exposures') }}
where period = 'pre'
    and event_date between '{{ var("pre_start") }}' and '{{ var("pre_end") }}'
    and author_id is not null
