#!/usr/bin/env python3
"""Validate benchmark outputs for the TACC RAPIDS spatio-temporal run.

Checks:
- required artifacts exist
- CSV has expected columns and non-negative/finite numeric values
- scenario coverage includes expected workload families
- summary and CSV are internally consistent (row counts, totals, timing)
- GPU metrics file has parseable header and at least one sample row
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path


EXPECTED_SCENARIOS = [
    "temporal",
    "bbox_full_time",
    "maintenance",
    "polygon_like",
]

REQUIRED_CSV_COLUMNS = [
    "scenario",
    "label",
    "source",
    "points",
    "seed",
    "batch_size",
    "maintenance_window",
    "repeat",
    "param_window_start",
    "param_window_end",
    "param_bbox",
    "param_batch_size",
    "param_poly_like_id",
    "n_points",
    "elapsed_ms",
    "result_rows",
    "active_rows",
    "throughput_rows_per_s",
    "gpu_util_pre",
    "gpu_util_post",
    "mem_used_mb_pre",
    "mem_used_mb_post",
    "mem_total_mb",
    "repeats",
]

REQUIRED_SUMMARY_KEYS = [
    "run_at_utc",
    "hostname",
    "source",
    "n_points",
    "scenarios",
    "results_count",
    "rows_out",
    "elapsed_ms_mean",
    "gpu_util_post_mean",
    "max_mem_used_mb_post",
    "records",
]

REQUIRED_GPU_COLUMNS = [
    "timestamp",
    "index",
    "utilization.gpu",
    "utilization.memory",
    "memory.used",
    "memory.total",
]
GPU_METRIC_COLUMNS_EXPECTED = len(REQUIRED_GPU_COLUMNS)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate benchmark result folder")
    p.add_argument("result_dir", help="Path to run output directory")
    p.add_argument("--expected-scenarios", default=",".join(EXPECTED_SCENARIOS), help="Comma-separated scenario names")
    p.add_argument("--min-rows", type=int, default=1, help="Minimum expected number of rows in CSV")
    return p.parse_args()


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def check_file_exists(path: Path, label: str) -> None:
    if not path.is_file():
        fail(f"{label} missing: {path}")


def as_float(value: str, label: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        fail(f"{label} has non-numeric value '{value}'")
    if not math.isfinite(parsed):
        fail(f"{label} has non-finite value '{value}'")
    return parsed


def as_int(value: str, label: str) -> int:
    parsed = as_float(value, label)
    if parsed != int(parsed):
        fail(f"{label} is not an integer value '{value}'")
    return int(parsed)


def validate_csv(path: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    if not rows:
        fail(f"CSV contains no rows: {path}")

    missing_cols = [c for c in REQUIRED_CSV_COLUMNS if c not in reader.fieldnames]
    if missing_cols:
        fail(f"CSV missing required columns {missing_cols}: {path}")

    scenario_counts = {}
    elapsed_sum = 0.0
    row_sum = 0
    for idx, row in enumerate(rows, start=1):
        scenario = row.get("scenario", "")
        scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1

        n_points = as_int(row.get("n_points", "-1"), f"row {idx} n_points")
        if n_points <= 0:
            fail(f"row {idx} has non-positive n_points: {n_points}")

        elapsed = as_float(row.get("elapsed_ms", "-1"), f"row {idx} elapsed_ms")
        if elapsed <= 0:
            fail(f"row {idx} has non-positive elapsed_ms: {elapsed}")
        elapsed_sum += elapsed

        results = as_int(row.get("result_rows", "-1"), f"row {idx} result_rows")
        if results < 0:
            fail(f"row {idx} has negative result_rows: {results}")
        row_sum += results

        if as_float(row.get("gpu_util_pre", "0"), f"row {idx} gpu_util_pre") < 0:
            fail(f"row {idx} has negative gpu_util_pre")
        if as_float(row.get("gpu_util_post", "0"), f"row {idx} gpu_util_post") < 0:
            fail(f"row {idx} has negative gpu_util_post")

    elapsed_mean = elapsed_sum / len(rows)
    return rows, {
        "row_count": len(rows),
        "results_sum": row_sum,
        "elapsed_mean": elapsed_mean,
        "scenario_counts": scenario_counts,
    }


def validate_summary(path: Path, csv_stats: dict[str, object]) -> None:
    with path.open() as fh:
        summary = json.load(fh)

    missing = [k for k in REQUIRED_SUMMARY_KEYS if k not in summary]
    if missing:
        fail(f"summary.json missing keys {missing}")

    if not isinstance(summary.get("records"), list):
        fail("summary.json.records is not a list")

    results_count = summary["results_count"]
    if not isinstance(results_count, int) or results_count != csv_stats["row_count"]:
        fail(
            f"summary results_count mismatch: summary={results_count}, csv={csv_stats['row_count']}"
        )

    rows_out = summary["rows_out"]
    if not isinstance(rows_out, int) or rows_out != csv_stats["results_sum"]:
        fail(
            f"summary rows_out mismatch: summary={rows_out}, csv_sum={csv_stats['results_sum']}"
        )

    mean_delta = abs(float(summary["elapsed_ms_mean"]) - float(csv_stats["elapsed_mean"]))
    if mean_delta > 1e-6:
        fail(
            f"summary elapsed_ms_mean mismatch: summary={summary['elapsed_ms_mean']}, csv_mean={csv_stats['elapsed_mean']}"
        )

    scenarios = summary.get("scenarios")
    if not isinstance(scenarios, list):
        fail("summary.scenarios is not a list")


def validate_gpu_metrics(path: Path) -> int:
    with path.open(newline="") as fh:
        lines = [line.strip() for line in fh.read().splitlines() if line.strip()]

    if not lines:
        fail(f"gpu_metrics.csv is empty: {path}")

    first_row = [col.strip() for col in csv.reader([lines[0]]).__next__()]
    if (
        len(first_row) >= 2
        and first_row[0].lower() == "timestamp"
        and any(col.lower().startswith("index") for col in first_row[1:])
    ):
        missing = [c for c in REQUIRED_GPU_COLUMNS if c not in first_row]
        if missing:
            fail(f"gpu_metrics.csv missing required columns {missing}")

        data_start = 1
    else:
        data_start = 0

    for lineno, line in enumerate(lines[data_start:], start=data_start + 1):
        cols = [col.strip() for col in csv.reader([line]).__next__()]
        if len(cols) < GPU_METRIC_COLUMNS_EXPECTED:
            fail(
                f"gpu_metrics.csv row {lineno} has too few columns: "
                f"{len(cols)} < {GPU_METRIC_COLUMNS_EXPECTED}"
            )

        index = cols[1]
        if index == "":
            fail(f"gpu_metrics.csv row {lineno} missing index value")
        try:
            int(float(index))
        except ValueError:
            fail(f"gpu_metrics.csv row {lineno} has non-integer index: '{index}'")

        # Keep parsing strict but tolerant of additional columns.
        for metric_name, value in [
            ("utilization.gpu", cols[2]),
            ("utilization.memory", cols[3]),
            ("memory.used", cols[4]),
            ("memory.total", cols[5]),
        ]:
            as_float(value, f"gpu_metrics.csv row {lineno} {metric_name}")

            if metric_name.startswith("utilization") and not (0.0 <= float(value) <= 100.0):
                fail(
                    f"gpu_metrics.csv row {lineno} {metric_name} outside expected range: '{value}'"
                )

    return len(lines) - data_start


def main() -> int:
    args = parse_args()
    result_dir = Path(args.result_dir)
    if not result_dir.is_dir():
        fail(f"Run directory not found: {result_dir}")

    csv_path = result_dir / "benchmark_results.csv"
    summary_path = result_dir / "summary.json"
    gpu_path = result_dir / "gpu_metrics.csv"

    check_file_exists(csv_path, "benchmark_results.csv")
    check_file_exists(summary_path, "summary.json")
    check_file_exists(gpu_path, "gpu_metrics.csv")

    rows, csv_stats = validate_csv(csv_path)
    validate_summary(summary_path, csv_stats)
    samples = validate_gpu_metrics(gpu_path)

    expected = [s.strip() for s in args.expected_scenarios.split(",") if s.strip()]
    scenario_counts = csv_stats["scenario_counts"]

    missing_scenarios = [s for s in expected if s not in scenario_counts]
    if missing_scenarios:
        fail(f"Missing expected scenarios in CSV: {missing_scenarios}")

    if csv_stats["row_count"] < args.min_rows:
        fail(f"CSV row count below minimum: {csv_stats['row_count']} < {args.min_rows}")

    total_rows_reported = sum(scenario_counts.values())
    if total_rows_reported != csv_stats["row_count"]:
        fail(
            f"Scenario row count accounting mismatch: total={total_rows_reported}, row_count={csv_stats['row_count']}"
        )

    print("[OK] benchmark output validation passed")
    print(f"rows={csv_stats['row_count']}")
    print(f"rows_out={csv_stats['results_sum']}")
    print(f"scenario_counts={scenario_counts}")
    print(f"gpu_metrics_samples={samples}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
