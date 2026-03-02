#!/usr/bin/env python3

"""
TACC RAPIDS geospatial benchmark harness.

Path A (container-first) entrypoint used by jobs/spatial_benchmark.sbatch.
The script is designed to run in a cuDF/cuspatial environment and produce
CSV + JSON artifacts for comparison across spatio-temporal query scenarios.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Tuple

import cupy as cp
import cudf


def gpu_stats() -> Dict[str, Any]:
    """Query lightweight GPU utilization/memory metrics using nvidia-smi."""
    import subprocess

    fields = (
        "utilization.gpu,"
        "utilization.memory,"
        "memory.used,"
        "memory.total"
    )
    cmd = [
        "nvidia-smi",
        "--query-gpu=" + fields,
        "--format=csv,noheader,nounits",
    ]

    try:
        raw = subprocess.check_output(cmd, text=True).strip().splitlines()
        if not raw:
            return {
                "gpu_util": None,
                "mem_util": None,
                "mem_used_mb": None,
                "mem_total_mb": None,
            }

        first = raw[0].split(",")
        values = [part.strip() for part in first]
        return {
            "gpu_util": float(values[0]) if values[0] != "[Not Supported]" else None,
            "mem_util": float(values[1]) if values[1] != "[Not Supported]" else None,
            "mem_used_mb": int(float(values[2])) if values[2] != "[Not Supported]" else None,
            "mem_total_mb": int(float(values[3])) if values[3] != "[Not Supported]" else None,
        }
    except Exception:
        return {
            "gpu_util": None,
            "mem_util": None,
            "mem_used_mb": None,
            "mem_total_mb": None,
        }


def time_iterable(fn, iterations: int = 1) -> Tuple[Any, float]:
    """Run callable a fixed number of iterations and return last output + median duration."""
    durations = []
    result = None
    for _ in range(iterations):
        cp.cuda.runtime.deviceSynchronize()
        t_start = cp.cuda.Event()
        t_end = cp.cuda.Event()
        t_start.record()
        result = fn()
        t_end.record()
        t_end.synchronize()
        elapsed_ms = cp.cuda.get_elapsed_time(t_start, t_end)
        durations.append(float(elapsed_ms))

        # keep the result live by materializing length
        if hasattr(result, "shape"):
            _ = result.shape[0]
        else:
            _ = len(result)

    return result, float(mean(durations))


def ensure_columns(df: cudf.DataFrame, cols: Iterable[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(
            "Input data missing required columns: "
            f"{', '.join(missing)}. Expected at least x, y, ts."
        )


def load_points(path: str, x_col: str, y_col: str, ts_col: str) -> cudf.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Data path does not exist: {path}")

    if p.suffix.lower() in {".parquet", ".pq"}:
        df = cudf.read_parquet(path)
    elif p.suffix.lower() in {".csv", ".txt"}:
        df = cudf.read_csv(path)
    else:
        raise ValueError(f"Unsupported input format for {path}; use parquet or csv")

    if x_col in df.columns and x_col != "x":
        df = df.rename({x_col: "x"})
    if y_col in df.columns and y_col != "y":
        df = df.rename({y_col: "y"})
    if ts_col in df.columns and ts_col != "ts":
        df = df.rename({ts_col: "ts"})

    ensure_columns(df, ["x", "y", "ts"])

    df = df.loc[:, ["x", "y", "ts"]]
    df = df.sort_values("ts").reset_index(drop=True)
    if not (df["ts"].dtype.kind in {"i", "u"}):
        df["ts"] = df["ts"].astype("int64")

    return df


def make_synthetic(n_points: int, seed: int) -> cudf.DataFrame:
    rng = cp.random.RandomState(seed)
    return cudf.DataFrame(
        {
            "point_id": cp.arange(n_points, dtype=cp.int64),
            "x": rng.uniform(-180.0, 180.0, n_points).astype(cp.float32),
            "y": rng.uniform(-90.0, 90.0, n_points).astype(cp.float32),
            "ts": rng.randint(0, 86_400 * 30, size=n_points, dtype=cp.int64),
            "payload": rng.random(n_points, dtype=cp.float32),
        }
    )


def spatial_temporal_query(df: cudf.DataFrame, bbox: Tuple[float, float, float, float],
                          t0: int, t1: int) -> cudf.DataFrame:
    xmin, xmax, ymin, ymax = bbox
    mask = (
        (df["x"] >= xmin)
        & (df["x"] <= xmax)
        & (df["y"] >= ymin)
        & (df["y"] <= ymax)
        & (df["ts"] >= t0)
        & (df["ts"] < t1)
    )
    return df.loc[mask]


def temporal_query(df: cudf.DataFrame, t0: int, t1: int) -> cudf.DataFrame:
    mask = (df["ts"] >= t0) & (df["ts"] < t1)
    return df.loc[mask]


def temporal_windows(ts_min: int, ts_max: int) -> List[Tuple[int, int]]:
    span = ts_max - ts_min
    windows = [60, 600, 3600, 10800, 86400]
    out = []
    for w in windows:
        end = ts_min + w
        if end <= ts_max:
            out.append((ts_min, end))
        elif w >= 60:
            out.append((ts_max - min(w, span), ts_max))
    # deduplicate preserve order
    uniq = []
    seen = set()
    for a, b in out:
        if (a, b) not in seen:
            uniq.append((a, b))
            seen.add((a, b))
    return uniq


def bbox_presets() -> List[Tuple[float, float, float, float]]:
    return [
        (-180.0, 180.0, -90.0, 90.0),
        (-50.0, 50.0, -20.0, 20.0),
        (-10.0, 10.0, -5.0, 5.0),
    ]


def benchmark_temporal(df: cudf.DataFrame, repeats: int) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    tmin, tmax = int(df["ts"].min()), int(df["ts"].max())
    for idx, (t0, t1) in enumerate(temporal_windows(tmin, tmax)):
        for rep in range(repeats):
            pre = gpu_stats()
            _, elapsed_ms = time_iterable(lambda: temporal_query(df, t0, t1), 1)
            post = gpu_stats()
            result_size = int(df[((df["ts"] >= t0) & (df["ts"] < t1))].shape[0])
            records.append(
                {
                    "scenario": "temporal",
                    "label": f"window-{idx}",
                    "n_points": int(len(df)),
                    "repeat": rep + 1,
                    "param_window_start": t0,
                    "param_window_end": t1,
                    "elapsed_ms": elapsed_ms,
                    "result_rows": result_size,
                    "throughput_rows_per_s": int(
                        (result_size / (elapsed_ms / 1000.0)) if elapsed_ms > 0 else 0
                    ),
                    "gpu_util_pre": pre["gpu_util"],
                    "gpu_util_post": post["gpu_util"],
                    "mem_used_mb_pre": pre["mem_used_mb"],
                    "mem_used_mb_post": post["mem_used_mb"],
                    "mem_total_mb": pre["mem_total_mb"],
                }
            )
    return records


def benchmark_bbox(df: cudf.DataFrame, repeats: int) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    tmin, tmax = int(df["ts"].min()), int(df["ts"].max())
    for idx, box in enumerate(bbox_presets()):
        for rep in range(repeats):
            pre = gpu_stats()
            _, elapsed_ms = time_iterable(
                lambda: spatial_temporal_query(df, box, tmin, tmax), 1
            )
            post = gpu_stats()
            result_size = int(
                spatial_temporal_query(df, box, tmin, tmax).shape[0]
            )
            records.append(
                {
                    "scenario": "bbox_full_time",
                    "label": f"bbox-{idx}",
                    "n_points": int(len(df)),
                    "repeat": rep + 1,
                    "param_bbox": f"{box}",
                    "elapsed_ms": elapsed_ms,
                    "result_rows": result_size,
                    "throughput_rows_per_s": int(
                        (result_size / (elapsed_ms / 1000.0)) if elapsed_ms > 0 else 0
                    ),
                    "gpu_util_pre": pre["gpu_util"],
                    "gpu_util_post": post["gpu_util"],
                    "mem_used_mb_pre": pre["mem_used_mb"],
                    "mem_used_mb_post": post["mem_used_mb"],
                    "mem_total_mb": pre["mem_total_mb"],
                }
            )
    return records


def benchmark_maintenance(
    df: cudf.DataFrame, batch_size: int, repeats: int, window_seconds: int
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    df = df.sort_values("ts").reset_index(drop=True)
    updates = min(repeats, int(len(df) / max(batch_size, 1)))

    for batch_idx in range(updates):
        start = batch_idx * batch_size
        end = start + batch_size
        batch = df.iloc[start:end]
        if len(batch) == 0:
            break

        # maintenance-style rolling window with incremental ingestion
        if batch_idx == 0:
            active = batch.iloc[0:0].copy()

        pre = gpu_stats()

        active = cudf.concat([active, batch], ignore_index=True)
        t_cut = int(batch["ts"].max()) - int(window_seconds)
        if t_cut < 0:
            t_cut = 0
        active = active[active["ts"] >= t_cut]

        # fixed region of interest for spatio-temporal maintenance query
        box = (-10.0, 10.0, -10.0, 10.0)
        _, elapsed_ms = time_iterable(
            lambda: spatial_temporal_query(active, box, t_cut, int(batch["ts"].max())), 1
        )
        post = gpu_stats()

        result_size = int(
            spatial_temporal_query(active, box, t_cut, int(batch["ts"].max())).shape[0]
        )
        records.append(
            {
                "scenario": "maintenance",
                "label": f"batch-{batch_idx}",
                "n_points": int(len(df)),
                "repeat": batch_idx + 1,
                "param_batch_size": int(batch_size),
                "param_window_seconds": int(window_seconds),
                "elapsed_ms": elapsed_ms,
                "result_rows": result_size,
                "active_rows": int(len(active)),
                "throughput_rows_per_s": int(
                    (result_size / (elapsed_ms / 1000.0)) if elapsed_ms > 0 else 0
                ),
                "gpu_util_pre": pre["gpu_util"],
                "gpu_util_post": post["gpu_util"],
                "mem_used_mb_pre": pre["mem_used_mb"],
                "mem_used_mb_post": post["mem_used_mb"],
                "mem_total_mb": pre["mem_total_mb"],
            }
        )

    return records


def benchmark_polygon_like(df: cudf.DataFrame, repeats: int) -> List[Dict[str, Any]]:
    """
    Polygon-like scenario without requiring external polygon files.

    Uses a rotated-grid approximation implemented as chained axis-aligned boxes,
    which still exercises strict spatial constraints for workload characterization.
    """

    records: List[Dict[str, Any]] = []
    tmin, tmax = int(df["ts"].min()), int(df["ts"].max())
    boxes = [
        (-150.0, -120.0, -50.0, -20.0),
        (-20.0, 40.0, 20.0, 55.0),
        (90.0, 150.0, -30.0, 30.0),
    ]

    for idx, box in enumerate(boxes):
        for rep in range(repeats):
            pre = gpu_stats()
            _, elapsed_ms = time_iterable(lambda: spatial_temporal_query(df, box, tmin, tmax), 1)
            post = gpu_stats()
            result_size = int(spatial_temporal_query(df, box, tmin, tmax).shape[0])
            records.append(
                {
                    "scenario": "polygon_like",
                    "label": f"polybox-{idx}",
                    "n_points": int(len(df)),
                    "repeat": rep + 1,
                    "param_poly_like_id": idx,
                    "elapsed_ms": elapsed_ms,
                    "result_rows": result_size,
                    "throughput_rows_per_s": int(
                        (result_size / (elapsed_ms / 1000.0)) if elapsed_ms > 0 else 0
                    ),
                    "gpu_util_pre": pre["gpu_util"],
                    "gpu_util_post": post["gpu_util"],
                    "mem_used_mb_pre": pre["mem_used_mb"],
                    "mem_used_mb_post": post["mem_used_mb"],
                    "mem_total_mb": pre["mem_total_mb"],
                }
            )

    return records


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run RAPIDS geospatial spatio-temporal benchmark scenarios"
    )
    parser.add_argument("--data-path", default="", help="Optional input data (parquet/csv)")
    parser.add_argument("--x-col", default="x", help="X coordinate column name")
    parser.add_argument("--y-col", default="y", help="Y coordinate column name")
    parser.add_argument("--ts-col", default="ts", help="Timestamp column name")
    parser.add_argument("--points", type=int, default=200_000, help="Synthetic point count")
    parser.add_argument(
        "--scenario-list",
        default="temporal,bbox,maintenance,polygon_like",
        help="Comma-separated scenarios to run",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Scenario repeat count")
    parser.add_argument("--batch-size", type=int, default=50_000, help="Maintenance batch size")
    parser.add_argument("--maintenance-window", type=int, default=3600, help="Maintenance window in seconds")
    parser.add_argument("--seed", type=int, default=42, help="Synthetic seed")
    parser.add_argument("--output-dir", default=".", help="Directory for result artifacts")
    parser.add_argument("--result-csv", default="benchmark_results.csv", help="CSV output filename")
    parser.add_argument("--result-json", default="benchmark_summary.json", help="JSON output filename")
    parser.add_argument("--append-only", action="store_true", help="Append to existing CSV")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    scenarios = {s.strip() for s in args.scenario_list.split(",") if s.strip()}

    if not cp.cuda.runtime.getDeviceCount():
        raise RuntimeError("No CUDA device visible. Check container/cluster GPU binding")

    # dataset
    if args.data_path:
        df = load_points(args.data_path, args.x_col, args.y_col, args.ts_col)
        source = os.path.abspath(args.data_path)
    else:
        df = make_synthetic(args.points, args.seed)
        source = "synthetic"

    # minimal environment checks
    import cupy as _
    import cudf as _
    import cuspatial

    _ = cuspatial.__version__

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_records: List[Dict[str, Any]] = []
    if "temporal" in scenarios:
        all_records.extend(benchmark_temporal(df, args.repeats))
    if "bbox" in scenarios:
        all_records.extend(benchmark_bbox(df, args.repeats))
    if "maintenance" in scenarios:
        all_records.extend(
            benchmark_maintenance(df, args.batch_size, args.repeats, args.maintenance_window)
        )
    if "polygon_like" in scenarios:
        all_records.extend(benchmark_polygon_like(df, args.repeats))

    # add shared metadata to each record
    for rec in all_records:
        rec.update(
            {
                "source": source,
                "points": int(len(df)),
                "seed": int(args.seed),
                "batch_size": int(args.batch_size),
                "maintenance_window": int(args.maintenance_window),
                "repeats": int(args.repeats),
            }
        )

    fieldnames = [
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

    csv_path = out_dir / args.result_csv
    write_header = args.append_only is False or not csv_path.exists()
    with csv_path.open("a", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for r in all_records:
            writer.writerow(r)

    summary = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": os.uname().nodename,
        "source": source,
        "n_points": int(len(df)),
        "scenarios": sorted(scenarios),
        "results_count": len(all_records),
        "rows_out": int(sum(r.get("result_rows", 0) for r in all_records)),
        "elapsed_ms_mean": float(mean([r["elapsed_ms"] for r in all_records])) if all_records else 0.0,
        "gpu_util_post_mean": float(
            mean([r["gpu_util_post"] for r in all_records if r.get("gpu_util_post") is not None])
        ) if any(r.get("gpu_util_post") is not None for r in all_records) else None,
        "max_mem_used_mb_post": int(
            max([r["mem_used_mb_post"] for r in all_records if r.get("mem_used_mb_post") is not None])
        ) if any(r.get("mem_used_mb_post") is not None for r in all_records) else None,
        "records": all_records,
    }
    with (out_dir / args.result_json).open("w") as fp:
        json.dump(summary, fp, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
