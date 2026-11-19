-- D25/D29/D30 effective-view thresholds, frozen (D55): read from the frozen_reference_thresholds seed,
-- exported once from int_reference_thresholds_computed on the full-data prod build. Every target uses
-- these thresholds.
select
    duration_bucket,
    median_play_time_ms,
    n_reference_rows
from {{ ref('frozen_reference_thresholds') }}
