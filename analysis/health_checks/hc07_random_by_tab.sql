-- scope: full
-- HC 7: which tabs carry random insertions (full random log, about 1.19M rows). Counts only.
select
    tab,
    count(*) as n_random,
    count(*) / sum(count(*)) over () as share_of_random
from {rnd}
where event_date between '2022-04-22' and '2022-05-08'
group by tab
order by tab
