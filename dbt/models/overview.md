{% docs __overview__ %}

# Feed exploration budget: data models

This project asks how much of a short-video feed should go to exploration and what it costs, using KuaiRand's randomly inserted videos as measured exploration slots. The answer is on the [dashboard](https://hansonyjy.github.io/feed-exploration-experiment/) and in the [decision memo](https://github.com/hansonyjy/feed-exploration-experiment/blob/main/docs/memo.md); these models are how the numbers were built.

## Layers

- **Staging** (`stg_`): types, renames and deduplication of the raw KuaiRand tables.
- **Intermediate** (`int_`): shared logic, such as duration buckets, effective-view thresholds, sessions, pre-period user profiles and the tab-1 analysis population.
- **Marts** (`fct_`, `mart_`): the tables the analysis scripts read.

## Start here

- [fct_tab1_impression_metrics](#!/model/model.feed_exploration.fct_tab1_impression_metrics): one row per tab-1 impression in the test window, with every pre-registered metric and the robustness flags.
- [mart_random_request_items](#!/model/model.feed_exploration.mart_random_request_items): every item in requests that contain a random video; the input to the main random vs recommended comparison.
- [mart_decomposition_user_day](#!/model/model.feed_exploration.mart_decomposition_user_day): sums per user and day for random, recommended pool and other recommended videos; the input to the content vs targeting split.
- [mart_same_video_items](#!/model/model.feed_exploration.mart_same_video_items): every exposure of a random-pool video, recommended or random; the input to the same-video comparison.
- **Frozen seeds:** [frozen_duration_buckets](#!/model/seed.feed_exploration.frozen_duration_buckets) and [frozen_reference_thresholds](#!/model/seed.feed_exploration.frozen_reference_thresholds) fix the duration buckets and effective-view thresholds computed once from the full data, and [segment_merge_map](#!/model/seed.feed_exploration.segment_merge_map) fixes the segment merges committed before any segment outcome was read.

## Conventions

- **Naming:** `stg_` for staging, `int_` for intermediate, `fct_` and `mart_` for the tables the analysis reads; one model per file.
- **Tests:** every model's key is tested unique and not_null, 235 tests in total.

Click the blue icon at the bottom right to see the lineage graph.

{% enddocs %}
