{{
    config(
        partition_by={'field': 'event_date', 'data_type': 'date', 'granularity': 'day'},
        cluster_by=['user_id', 'video_id']
    )
}}

with random_exposures as (
    {{ kr_log_select(kr_log_source('log_random_treat'), 'log_random_treat', 'treatment',
                     var('treat_start'), var('treat_end')) }}
)

select * from random_exposures
