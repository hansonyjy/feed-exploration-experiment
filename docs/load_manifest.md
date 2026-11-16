# Load manifest

Written by `scripts/load_kuairand.py verify`. Counts and hashes only, no data.

## Source files

| File | Table | Bytes | Lines (excl. header) | SHA-256 |
| --- | --- | ---: | ---: | --- |
| `log_random_4_22_to_5_08_27k.csv` | log_random_treat | 87,086,116 | 1,186,059 | `60b80994da969cd53da4d50c37ba3dafd6fb185df804c92c8410df34845a9d2c` |
| `log_standard_4_08_to_4_21_27k_part1.csv` | log_standard_pre | 5,182,942,311 | 68,148,288 | `b433233d6bdf9e8590aa1c92a9d3fe2876ae6e9f8c5c04ee085ad21fbfd6413f` |
| `log_standard_4_08_to_4_21_27k_part2.csv` | log_standard_pre | 5,157,310,890 | 68,148,288 | `26fefe715f3ac9b693ba8771b66dbda9a0f34a19034acb9005cb04aecd894717` |
| `log_standard_4_22_to_5_08_27k_part1.csv` | log_standard_treat | 7,080,264,277 | 93,062,020 | `6057df35a8918825bd7ec72c46f0aac54ec6d04b2ad432418aa7c2c79bf85274` |
| `log_standard_4_22_to_5_08_27k_part2.csv` | log_standard_treat | 7,035,008,322 | 92,919,789 | `ee82474e37f7b8b3fcbeffb0e15c3913ed8be436af5d5f94d672168cf663645d` |
| `user_features_27k.csv` | user_features | 3,519,028 | 27,285 | `dc729a656301b4c6d07f713fe41d05ec9bfaab670b90e531c70037caf033c011` |
| `video_features_basic_27k.csv` | video_features_basic | 2,796,341,026 | 32,038,725 | `b3ccf2be3a63e08bb85a08093ee01f8d6266cdcd184eabf0d5ecd1797530f950` |
| `kuairand_video_categories.csv` | video_categories | 3,687,928,520 | 32,038,725 | `744010240c8ae829a80998532737f710e6493d50c500c256ca39bd9f102aa4ad` |

## BigQuery tables (`feed-exploration-hy.raw`)

| Table | Parquet rows | BigQuery rows | Event dates |
| --- | ---: | ---: | --- |
| `log_random_treat` | 1,186,059 | 1,186,059 | 2022-04-22 to 2022-05-08 |
| `log_random_treat_dev5` | 51,570 | 51,570 | 2022-04-22 to 2022-05-08 |
| `log_standard_pre` | 136,296,576 | 136,296,576 | 2022-04-08 to 2022-04-21 |
| `log_standard_pre_dev5` | 6,349,506 | 6,349,506 | 2022-04-08 to 2022-04-21 |
| `log_standard_treat` | 185,981,809 | 185,981,809 | 2022-04-22 to 2022-05-08 |
| `log_standard_treat_dev5` | 8,825,087 | 8,825,087 | 2022-04-22 to 2022-05-08 |
| `user_features` | 27,285 | 27,285 | - |
| `video_categories` | 32,038,725 | 32,038,725 | - |
| `video_features_basic` | 32,038,725 | 32,038,725 | - |

## Dev sample

1,248 of 27,285 users (4.57% realized, 5% target; the hash buckets are uniform, so the gap is chance). Rule in BigQuery SQL:

```sql
mod(cast(concat('0x', substr(to_hex(md5(cast(user_id as string))), 1, 8)) as int64), 100) < 5
```

SHA-256 of the sorted, comma-joined sampled user_ids: `d9ac9e0b363f23336984ca543f9dc5931fefc32102fd5f83bf20e336a09f86bd`

## Verification

All checks passed.
