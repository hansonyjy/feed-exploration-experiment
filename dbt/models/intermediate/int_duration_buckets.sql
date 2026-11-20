-- D26 duration buckets, frozen (D25, D27, D55): read from the frozen_duration_buckets seed, exported once
-- from int_duration_buckets_computed on the full-data prod build. Every target uses these edges.
select
    duration_bucket,
    lower_exclusive_ms,
    upper_inclusive_ms,
    n_reference_rows
from {{ ref('frozen_duration_buckets') }}
