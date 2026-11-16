"""Load KuaiRand-27K into BigQuery `raw`: CSV -> typed Parquet (DuckDB) -> GCS -> BigQuery.

Steps (run in order, or `all`):
  check    verify every source file exists and its header matches the explicit schema below;
           record bytes, sha256 and newline-based line counts
  convert  write typed Parquet per table (adds event_date to logs) and the 5% dev-sample logs
  upload   copy Parquet to gs://$GCS_BUCKET/parquet/
  load     (re)create each raw table with explicit schema, partitioning and clustering, then load
  verify   compare BigQuery row counts (table metadata, no query cost) with the manifest; check that
           the BigQuery formula for the dev sample reproduces the local user list
Results accumulate in a local JSON state file, and `verify` writes docs/load_manifest.md.

Usage: uv run python scripts/load_kuairand.py {check|convert|upload|load|verify|all}
Config (.env): GCP_PROJECT, GCS_BUCKET (default <project>-kuairand), KUAIRAND_DIR (default ~/data/kuairand).
Raw data never enters the repo; only the manifest (counts and hashes) is committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------------------------
# Dev sample: 5% of users, by a hash that DuckDB/Python and BigQuery compute identically.
# BigQuery: mod(cast(concat('0x', substr(to_hex(md5(cast(user_id as string))), 1, 8)) as int64), 100) < 5
# ---------------------------------------------------------------------------------------------
DEV_SAMPLE_PCT = 5
DEV_SAMPLE_SQL_BQ = (
    "mod(cast(concat('0x', substr(to_hex(md5(cast(user_id as string))), 1, 8)) as int64), 100) "
    f"< {DEV_SAMPLE_PCT}"
)


def in_dev_sample(user_id: int) -> bool:
    return int(hashlib.md5(str(user_id).encode()).hexdigest()[:8], 16) % 100 < DEV_SAMPLE_PCT


# ---------------------------------------------------------------------------------------------
# Explicit schemas. Column order must match the CSV header exactly, or `check` stops.
# Types are (duckdb_type, bigquery_type).
# ---------------------------------------------------------------------------------------------
LOG_COLUMNS = [
    ("user_id", "BIGINT", "INT64"),
    ("video_id", "BIGINT", "INT64"),
    ("date", "BIGINT", "INT64"),          # YYYYMMDD as an integer; event_date is derived from it
    ("hourmin", "BIGINT", "INT64"),       # HHMM as an integer, e.g. 1800
    ("time_ms", "BIGINT", "INT64"),       # epoch milliseconds
    ("is_click", "BIGINT", "INT64"),
    ("is_like", "BIGINT", "INT64"),
    ("is_follow", "BIGINT", "INT64"),
    ("is_comment", "BIGINT", "INT64"),
    ("is_forward", "BIGINT", "INT64"),
    ("is_hate", "BIGINT", "INT64"),
    ("long_view", "BIGINT", "INT64"),
    ("play_time_ms", "BIGINT", "INT64"),
    ("duration_ms", "BIGINT", "INT64"),
    ("profile_stay_time", "BIGINT", "INT64"),
    ("comment_stay_time", "BIGINT", "INT64"),
    ("is_profile_enter", "BIGINT", "INT64"),
    ("is_rand", "BIGINT", "INT64"),
    ("tab", "BIGINT", "INT64"),
]

USER_COLUMNS = [
    ("user_id", "BIGINT", "INT64"),
    ("user_active_degree", "VARCHAR", "STRING"),
    ("is_lowactive_period", "BIGINT", "INT64"),
    ("is_live_streamer", "BIGINT", "INT64"),
    ("is_video_author", "BIGINT", "INT64"),
    ("follow_user_num", "BIGINT", "INT64"),
    ("follow_user_num_range", "VARCHAR", "STRING"),
    ("fans_user_num", "BIGINT", "INT64"),
    ("fans_user_num_range", "VARCHAR", "STRING"),
    ("friend_user_num", "BIGINT", "INT64"),
    ("friend_user_num_range", "VARCHAR", "STRING"),
    ("register_days", "BIGINT", "INT64"),
    ("register_days_range", "VARCHAR", "STRING"),
] + [(f"onehot_feat{i}", "DOUBLE", "FLOAT64") for i in range(18)]  # encrypted, mixed int/float

VIDEO_COLUMNS = [
    ("video_id", "BIGINT", "INT64"),
    ("author_id", "BIGINT", "INT64"),
    ("video_type", "VARCHAR", "STRING"),
    ("upload_dt", "VARCHAR", "STRING"),   # kept as text in raw; staging parses it
    ("upload_type", "VARCHAR", "STRING"),
    ("visible_status", "DOUBLE", "FLOAT64"),
    ("video_duration", "DOUBLE", "FLOAT64"),  # ms, stored as float in the source
    ("server_width", "DOUBLE", "FLOAT64"),
    ("server_height", "DOUBLE", "FLOAT64"),
    ("music_id", "BIGINT", "INT64"),
    ("music_type", "DOUBLE", "FLOAT64"),
    ("tag", "VARCHAR", "STRING"),         # comma-separated tag ids, e.g. "12,65"
]

CATEGORY_COLUMNS = [("final_video_id", "BIGINT", "INT64")] + [
    (f"{level}_level_category_{part}", dtype, btype)
    for level in ("first", "second", "third", "fourth")
    # ids are written as floats in the source ("39.0"; -124.0 = missing level); staging casts them
    for part, dtype, btype in (("id", "DOUBLE", "FLOAT64"), ("name", "VARCHAR", "STRING"),
                               ("prob", "DOUBLE", "FLOAT64"))
]


@dataclass
class Table:
    name: str                      # BigQuery table name in `raw`
    files: list[str]               # paths relative to KUAIRAND_DIR
    columns: list[tuple[str, str, str]]
    description: str
    is_log: bool = False           # logs get event_date, partitioning, clustering and a dev copy
    date_range: tuple[str, str] | None = None
    cluster_by: list[str] = field(default_factory=list)


DATA = "extracted/KuaiRand-27K/data"
TABLES = [
    Table("log_standard_pre",
          [f"{DATA}/log_standard_4_08_to_4_21_27k_part1.csv",
           f"{DATA}/log_standard_4_08_to_4_21_27k_part2.csv"],
          LOG_COLUMNS, "Standard-policy log, pre-period 2022-04-08 to 04-21. Never measures effects.",
          is_log=True, date_range=("2022-04-08", "2022-04-21"), cluster_by=["user_id", "video_id"]),
    Table("log_standard_treat",
          [f"{DATA}/log_standard_4_22_to_5_08_27k_part1.csv",
           f"{DATA}/log_standard_4_22_to_5_08_27k_part2.csv"],
          LOG_COLUMNS, "Standard-policy log, treatment window 2022-04-22 to 05-08.",
          is_log=True, date_range=("2022-04-22", "2022-05-08"), cluster_by=["user_id", "video_id"]),
    Table("log_random_treat",
          [f"{DATA}/log_random_4_22_to_5_08_27k.csv"],
          LOG_COLUMNS, "Random-intervention log (is_rand = 1), treatment window 2022-04-22 to 05-08.",
          is_log=True, date_range=("2022-04-22", "2022-05-08"), cluster_by=["user_id", "video_id"]),
    Table("user_features", [f"{DATA}/user_features_27k.csv"], USER_COLUMNS,
          "KuaiRand-27K user features (static).", cluster_by=["user_id"]),
    Table("video_features_basic", [f"{DATA}/video_features_basic_27k.csv"], VIDEO_COLUMNS,
          "KuaiRand-27K basic video features (static).", cluster_by=["video_id"]),
    Table("video_categories", ["supplementary/kuairand_video_categories.csv"], CATEGORY_COLUMNS,
          "KuaiRand supplementary video categories (Zenodo 10.5281/zenodo.18159199, CC BY 4.0). "
          "Joins on final_video_id.", cluster_by=["final_video_id"]),
]
DEV_SUFFIX = f"_dev{DEV_SAMPLE_PCT}"


# ---------------------------------------------------------------------------------------------
# Config and state
# ---------------------------------------------------------------------------------------------
def load_env() -> None:
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def cfg() -> dict[str, str | Path]:
    load_env()
    project = os.environ.get("GCP_PROJECT", "")
    if not project:
        sys.exit("set GCP_PROJECT in .env")
    data_dir = Path(os.path.expanduser(os.environ.get("KUAIRAND_DIR", "~/data/kuairand")))
    return {
        "project": project,
        "bucket": os.environ.get("GCS_BUCKET") or f"{project}-kuairand",
        "location": os.environ.get("GCP_LOCATION", "US"),
        "data_dir": data_dir,
        "parquet_dir": data_dir / "parquet",
        "state_file": data_dir / "load_state.json",
    }


def read_state(c) -> dict:
    return json.loads(c["state_file"].read_text()) if c["state_file"].exists() else {}


def write_state(c, state: dict) -> None:
    c["state_file"].write_text(json.dumps(state, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------------------------
def sha256_and_lines(path: Path) -> tuple[str, int]:
    digest, lines = hashlib.sha256(), 0
    with path.open("rb") as fh:
        while chunk := fh.read(64 * 1024 * 1024):
            digest.update(chunk)
            lines += chunk.count(b"\n")
    return digest.hexdigest(), lines


def step_check(c) -> None:
    state = read_state(c)
    files = state.setdefault("files", {})
    for t in TABLES:
        expected = [name for name, _, _ in t.columns]
        for rel in t.files:
            path = c["data_dir"] / rel
            if not path.exists():
                sys.exit(f"missing source file: {path}")
            with path.open() as fh:
                header = fh.readline().strip().split(",")
            if header != expected:
                sys.exit(f"header mismatch in {rel}:\n  got      {header}\n  expected {expected}")
            print(f"hashing {rel} ...", flush=True)
            sha, lines = sha256_and_lines(path)
            files[rel] = {"table": t.name, "bytes": path.stat().st_size, "sha256": sha,
                          "newline_count": lines}
    write_state(c, state)
    print("check ok: all files present, headers match")


def duckdb_select(t: Table, c) -> str:
    cols = ", ".join(f"'{n}': '{d}'" for n, d, _ in t.columns)
    paths = ", ".join(f"'{c['data_dir'] / rel}'" for rel in t.files)
    names = ", ".join(n for n, _, _ in t.columns)
    extra = ", strptime(cast(date as varchar), '%Y%m%d')::date as event_date" if t.is_log else ""
    return (f"select {names}{extra} from read_csv([{paths}], header = true, delim = ',', "
            f"quote = '\"', columns = {{{cols}}}, auto_detect = false)")


def step_convert(c) -> None:
    import duckdb

    state = read_state(c)
    rows = state.setdefault("parquet_rows", {})
    out_root: Path = c["parquet_dir"]
    con = duckdb.connect()
    con.execute("set preserve_insertion_order = false")

    # Dev-sample users, from the user feature file (every log user is expected to be in it;
    # HC 11 checks coverage). Python md5, so it can be reproduced exactly in BigQuery.
    users =con.execute(f"select distinct user_id from ({duckdb_select(TABLES[3], c)})").fetchall()
    dev_users = sorted(u for (u,) in users if in_dev_sample(u))
    con.execute("create temp table dev_users (user_id bigint)")
    con.executemany("insert into dev_users values (?)", [(u,) for u in dev_users])
    state["dev_sample"] = {"pct": DEV_SAMPLE_PCT, "n_users_total": len(users),
                           "n_users_sampled": len(dev_users),
                           "user_ids_sha256": hashlib.sha256(
                               ",".join(map(str, dev_users)).encode()).hexdigest()}
    print(f"dev sample: {len(dev_users)} of {len(users)} users", flush=True)

    for t in TABLES:
        targets = [(t.name, duckdb_select(t, c))]
        if t.is_log:
            cols = ", ".join(n for n, _, _ in t.columns) + ", event_date"
            targets.append((t.name + DEV_SUFFIX,
                            f"select {cols} from ({duckdb_select(t, c)}) "
                            "where user_id in (select user_id from dev_users)"))
        for name, select in targets:
            out = out_root / name
            if out.exists():
                for f in out.glob("*.parquet"):
                    f.unlink()
            out.mkdir(parents=True, exist_ok=True)
            print(f"converting {name} ...", flush=True)
            con.execute(f"copy ({select}) to '{out}' (format parquet, compression snappy, "
                        "row_group_size 500000, per_thread_output true, overwrite_or_ignore true)")
            n = con.execute(f"select count(*) from read_parquet('{out}/*.parquet')").fetchone()[0]
            rows[name] = n
            print(f"  {name}: {n:,} rows", flush=True)
            if t.is_log:
                lo, hi = con.execute(
                    f"select min(event_date), max(event_date) from read_parquet('{out}/*.parquet')"
                ).fetchone()
                state.setdefault("date_ranges", {})[name] = [str(lo), str(hi)]
    write_state(c, state)


def step_upload(c) -> None:
    src = str(c["parquet_dir"]) + "/*"
    dst = f"gs://{c['bucket']}/parquet/"
    print(f"uploading {src} -> {dst}", flush=True)
    subprocess.run(["gcloud", "storage", "cp", "-r", src, dst, f"--project={c['project']}"],
                   check=True)


def step_load(c) -> None:
    from google.cloud import bigquery

    client = bigquery.Client(project=c["project"], location=c["location"])
    names = [(t, t.name) for t in TABLES] + [(t, t.name + DEV_SUFFIX) for t in TABLES if t.is_log]
    for t, name in names:
        table_id = f"{c['project']}.raw.{name}"
        schema = [bigquery.SchemaField(n, b) for n, _, b in t.columns]
        table = bigquery.Table(table_id, schema=schema +
                               ([bigquery.SchemaField("event_date", "DATE")] if t.is_log else []))
        table.description = t.description + (" 5% hashed user sample." if name.endswith(DEV_SUFFIX)
                                             else "")
        table.labels = {"project": "feed-exploration"}
        table.clustering_fields = t.cluster_by
        if t.is_log:
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY, field="event_date")
            table.require_partition_filter = True
        client.delete_table(table_id, not_found_ok=True)
        client.create_table(table)
        job = client.load_table_from_uri(
            f"gs://{c['bucket']}/parquet/{name}/*.parquet", table_id,
            job_config=bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.PARQUET,
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND))
        print(f"loading {name} (job {job.job_id}) ...", flush=True)
        job.result()
        print(f"  {name}: {client.get_table(table_id).num_rows:,} rows", flush=True)


def step_verify(c) -> None:
    from google.cloud import bigquery

    client = bigquery.Client(project=c["project"], location=c["location"])
    state = read_state(c)
    problems: list[str] = []
    loaded = {}
    for name, expected in sorted(state["parquet_rows"].items()):
        actual = client.get_table(f"{c['project']}.raw.{name}").num_rows  # metadata, free
        loaded[name] = actual
        if actual != expected:
            problems.append(f"{name}: BigQuery {actual:,} != Parquet {expected:,}")

    # Source line counts minus one header line per file vs parsed rows (catches parser drops).
    for t in TABLES:
        lines = sum(state["files"][rel]["newline_count"] - 1 for rel in t.files)
        if lines != state["parquet_rows"][t.name]:
            problems.append(f"{t.name}: source lines {lines:,} != parsed rows "
                            f"{state['parquet_rows'][t.name]:,}")

    # The BigQuery dev-sample formula must reproduce the local user list (27K-row table).
    sql = (f"select count(*) n, to_hex(sha256(string_agg(cast(user_id as string), ',' "
           f"order by user_id))) h from `{c['project']}.raw.user_features` "
           f"where {DEV_SAMPLE_SQL_BQ}")
    cfg_job = bigquery.QueryJobConfig(maximum_bytes_billed=10 * 1024**3)
    n, h = list(client.query(sql, job_config=cfg_job).result())[0]
    ds = state["dev_sample"]
    if (n, h) != (ds["n_users_sampled"], ds["user_ids_sha256"]):
        problems.append(f"dev sample mismatch: BigQuery {n} users / {h}, local "
                        f"{ds['n_users_sampled']} / {ds['user_ids_sha256']}")

    state["bigquery_rows"] = loaded
    state["verify_problems"] = problems
    write_state(c, state)
    write_manifest(state, c)
    if problems:
        sys.exit("verify FAILED:\n  " + "\n  ".join(problems))
    print("verify ok: BigQuery rows == Parquet rows == source lines; dev sample reproducible")


def write_manifest(state: dict, c) -> None:
    out = ["# Load manifest", "",
           "Written by `scripts/load_kuairand.py verify`. Counts and hashes only, no data.", "",
           "## Source files", "",
           "| File | Table | Bytes | Lines (excl. header) | SHA-256 |", "| --- | --- | ---: | ---: | --- |"]
    for rel, f in sorted(state["files"].items()):
        out.append(f"| `{Path(rel).name}` | {f['table']} | {f['bytes']:,} | "
                   f"{f['newline_count'] - 1:,} | `{f['sha256']}` |")
    out += ["", f"## BigQuery tables (`{c['project']}.raw`)", "",
            "| Table | Parquet rows | BigQuery rows | Event dates |", "| --- | ---: | ---: | --- |"]
    for name, n in sorted(state["parquet_rows"].items()):
        dr = state.get("date_ranges", {}).get(name)
        out.append(f"| `{name}` | {n:,} | {state['bigquery_rows'].get(name, 0):,} | "
                   f"{' to '.join(dr) if dr else '-'} |")
    ds = state["dev_sample"]
    out += ["", "## Dev sample", "",
            f"{ds['n_users_sampled']:,} of {ds['n_users_total']:,} users "
            f"({ds['pct']}% target). Rule in BigQuery SQL:", "", "```sql", DEV_SAMPLE_SQL_BQ, "```",
            "", f"SHA-256 of the sorted, comma-joined sampled user_ids: `{ds['user_ids_sha256']}`", "",
            "## Verification", "",
            "All checks passed." if not state["verify_problems"]
            else "\n".join(f"- FAILED: {p}" for p in state["verify_problems"]), ""]
    (REPO_ROOT / "docs" / "load_manifest.md").write_text("\n".join(out))
    print("wrote docs/load_manifest.md")


STEPS = {"check": step_check, "convert": step_convert, "upload": step_upload,
         "load": step_load, "verify": step_verify}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=[*STEPS, "all"])
    args = parser.parse_args()
    c = cfg()
    for name in (STEPS if args.step == "all" else [args.step]):
        STEPS[name](c)


if __name__ == "__main__":
    main()
