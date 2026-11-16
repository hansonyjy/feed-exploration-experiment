{{
    config(
        partition_by={'field': 'event_date', 'data_type': 'date', 'granularity': 'day'},
        cluster_by=['user_id', 'video_id']
    )
}}

with pre_period as (
    {{ kr_log_select(kr_log_source('log_standard_pre'), 'log_standard_pre', 'pre',
                     var('pre_start'), var('pre_end')) }}
),

treatment_window as (
    {{ kr_log_select(kr_log_source('log_standard_treat'), 'log_standard_treat', 'treatment',
                     var('treat_start'), var('treat_end')) }}
)

select * from pre_period
union all
select * from treatment_window
