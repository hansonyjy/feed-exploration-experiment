#!/usr/bin/env bash
# Bytes billed by query jobs in this project: this month by Pacific day, and the month's total.
# The owner's stop rule (D55): pause and ask before the month's billed total would pass 800 GB.
# Usage: scripts/bytes_billed.sh [YYYY-MM]   (default: current month)
set -euo pipefail
month="${1:-$(date +%Y-%m)}"
bq query --nouse_legacy_sql --maximum_bytes_billed=1000000000 --format=pretty "
select
  coalesce(cast(day as string), 'month total') as day_pt,
  count(*) as n_jobs,
  round(sum(total_bytes_billed) / pow(10, 9), 2) as gb_billed
from (
  select date(creation_time, 'America/Los_Angeles') as day, total_bytes_billed, creation_time, job_type
  from \`region-us\`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
)
where job_type = 'QUERY'
  and format_timestamp('%Y-%m', creation_time, 'America/Los_Angeles') = '${month}'
group by rollup(day)
order by day_pt" 2>&1 | grep -v -i -E 'warn|requests/__init__'
