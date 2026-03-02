# Results Summary Template

## Run Metadata
- Date (UTC):
- Cluster:
- Allocation:
- Node type:
- Job ID:
- Image path:
- RAPIDS versions (`cudf`, `cuspatial`, Python):

## Benchmark Parameters
- `POINTS`:
- `REPEATS`:
- `SCENARIOS`:
- `BATCH_SIZE`:
- `MAINTENANCE_WINDOW`:
- `DATA_PATH`:

## Artifacts
- `benchmark_results.csv`:
- `summary.json`:
- `gpu_metrics.csv`:
- Job log:

## Performance Summary
- Mean elapsed time (`elapsed_ms_mean`):
- Mean post-run GPU util (`gpu_util_post_mean`):
- Peak GPU memory post-run (`max_mem_used_mb_post`):
- Total output rows (`rows_out`):

## Scenario Notes
- `temporal`:
- `bbox`:
- `maintenance`:
- `polygon_like`:

## Allocation Assessment
- Under-utilized / balanced / over-utilized:
- Recommended next tuning step:
