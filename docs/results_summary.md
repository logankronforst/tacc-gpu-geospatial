# Results Summary

## Authoritative Run

- Date (UTC): `2026-03-02T18:24:06.611465+00:00`
- Cluster: `Vista`
- Job ID: `604513`
- Allocation / Account: `CCR25007`
- Node type: `c640-032` (GH200 120GB)
- Image path: `/scratch/11039/logankronforst/containers/rapids.sif`
- RAPIDS versions: `python 3.10.12`, `cudf 23.08.00`, `cuspatial 23.08.00`

## Benchmark Parameters
- `POINTS`: `200000`
- `REPEATS`: `3`
- `SCENARIOS`: `temporal,bbox,maintenance,polygon_like`
- `BATCH_SIZE`: `50000`
- `MAINTENANCE_WINDOW`: `3600`
- `DATA_PATH`: `` (synthetic)

## Artifacts
- `benchmark_results.csv`: `/scratch/11039/logankronforst/tacc-gpu-geospatial/results/20260302_122357/benchmark_results.csv`
- `summary.json`: `/scratch/11039/logankronforst/tacc-gpu-geospatial/results/20260302_122357/summary.json`
- `gpu_metrics.csv`: `/scratch/11039/logankronforst/tacc-gpu-geospatial/results/20260302_122357/gpu_metrics.csv`
- Job log: `/work/11039/logankronforst/vista/tacc-gpu-geospatial/jobs/logs/geo-bench-604513.err`

## Performance Summary
- Mean elapsed time (`elapsed_ms_mean`): `2.5244453715`
- Mean post-run GPU util (`gpu_util_post_mean`): `0.8611111111`
- Peak GPU memory post-run (`max_mem_used_mb_post`): `583`
- Total output rows (`rows_out`): `722,815`

## Scenario Composition (results rows)
- `temporal`: `15` records
- `bbox_full_time`: `9` records
- `maintenance`: `3` records
- `polygon_like`: `9` records

## Allocation Assessment
- Assessment: **under-utilized** (`gpu_util_post_mean` `0.86`, low memory)
- Recommended next tuning step: increase `POINTS` and/or `BATCH_SIZE` to raise utilization before increasing repeats.

## Validation Cross-check
- Confirm all files exist at the paths above.
- Compare scenario labels against expected set: `temporal`, `bbox_full_time`, `maintenance`, `polygon_like`.
- Confirm run state and exit code in `sacct` for job `604513`.
