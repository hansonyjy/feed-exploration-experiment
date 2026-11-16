{{ config(cluster_by=['video_id']) }}

-- One row per video (basic features). Floats that hold whole numbers in the source become int64.
with source as (
    select
        video_id,
        author_id,
        video_type,
        upload_dt,
        upload_type,
        visible_status,
        video_duration,
        server_width,
        server_height,
        music_id,
        music_type,
        tag
    from {{ source('kuairand', 'video_features_basic') }}
)

select
    video_id,
    author_id,
    nullif(video_type, 'UNKNOWN') as video_type,
    safe.parse_date('%Y-%m-%d', upload_dt) as upload_date,
    upload_type,
    safe_cast(visible_status as int64) as visible_status,
    video_duration as video_duration_ms,
    safe_cast(server_width as int64) as server_width,
    safe_cast(server_height as int64) as server_height,
    music_id,
    safe_cast(music_type as int64) as music_type,
    tag as tag_ids
from source
