# HACK: TACC RAPIDS Spatio-Temporal Benchmark

## Objective
Reproduce and benchmark GPU-accelerated spatio-temporal query and maintenance workflows on TACC with a script-first, containerized setup.

## Validated Setup Snapshot
- Date: 2026-03-01
- Cluster: Vista
- Successful image pull job: `602474` on partition `gh-dev`
- Resolved image path: `/scratch/11039/logankronforst/containers/rapids.sif`
- Pulled tag: `rapidsai/base:26.02-cuda12-py3.11`
- Active benchmark submission: `602502` on partition `gh` (pending by scheduler priority at last check).

## Environment Strategy (Path A)
- Runtime mode: `Apptainer` (`--nv`) with a pre-staged RAPIDS SIF image.
- Why Path A: strongest reproducibility and lower CUDA/Python mismatch risk on shared HPC systems.
- Compute-node assumption: no internet dependency.
- Login-node assumption: internet may be used only for image staging.
- Site policy note: Vista does not allow Apptainer runtime on login nodes. Pull/build must run via batch or interactive compute allocation.

## Software Dependencies
- `Slurm` for job scheduling (`sbatch`, `scontrol`).
- `Apptainer` or `apptainer-suid`.
- NVIDIA GPU drivers available on compute nodes.
- RAPIDS stack inside the image:
- `cudf`
- `cuspatial`
- `cupy`
- Python 3.x compatible with selected RAPIDS build.

## Constraints and Compatibility Notes
- RAPIDS and CUDA must be compatible with node driver/runtime.
- Image must be pre-staged to storage visible from compute node, typically:
- `/scratch/$USER/containers/rapids.sif`
- Input data should be staged to TACC storage (`$SCRATCH` or project storage).
- Workload sizing must match allocation limits (GPU memory and wall time).

## Benchmark Scenarios
`src/spatial_benchmark.py` implements:
1. `temporal`
- Windowed temporal filtering at several interval sizes.
2. `bbox`
- Spatial bounding-box + full time range.
3. `maintenance`
- Incremental ingest + rolling temporal window + fixed ROI query.
4. `polygon_like`
- Strict regional filters approximating multi-region polygon-like constraints.

## Metrics Captured
- Scenario-level timings (`elapsed_ms`).
- Throughput (`throughput_rows_per_s`).
- Result cardinality (`result_rows`, `active_rows` where applicable).
- GPU snapshot metrics around each run:
- `gpu_util_pre`, `gpu_util_post`
- `mem_used_mb_pre`, `mem_used_mb_post`, `mem_total_mb`
- Job-level GPU telemetry sampled every 5s:
- `gpu_metrics.csv` from `nvidia-smi`.

## GPU Utilization Guidance (Avoid Under/Over Allocation)
Use these guardrails when reviewing `summary.json` and `gpu_metrics.csv`:
1. Under-utilization indicators:
- `gpu_util_post_mean < 30%` for most runs.
- Peak `mem_used_mb_post < 30%` of `mem_total_mb`.
- Action: increase `POINTS`, `BATCH_SIZE`, or combine scenarios in one job.
2. Balanced utilization target:
- `gpu_util_post_mean` roughly `50-85%`.
- Peak memory between `50-85%` of GPU memory.
- Action: keep current sizing and increase repeat count for statistical stability.
3. Over-utilization indicators:
- Frequent OOM or near-OOM (`>90%` memory sustained).
- Severe runtime volatility across repeats.
- Action: reduce `POINTS` or `BATCH_SIZE`, or request larger-memory GPU.

## Node and Allocation Sizing Recommendations
1. Start point:
- `--cpus-per-task=12`, `--time=02:00:00`, GPU-capable partition (for example `gh`).
2. Move up allocation when:
- Memory is repeatedly near saturation.
- Queue and runtime budget support larger nodes/longer runs.
3. Move down allocation when:
- Benchmarks complete quickly with consistently low utilization.

## Run Procedure
1. Stage RAPIDS image to scratch (one-time):
```bash
export IMAGE_PATH=/scratch/11039/logankronforst/containers/rapids.sif
mkdir -p /scratch/11039/logankronforst/containers jobs/logs
# On Vista, specify partition explicitly. Account is optional if your default is configured.
sbatch --partition=gh-dev --export=ALL,IMAGE_PATH jobs/pull_rapids_image.sbatch
```
2. Validate image on GPU node (recommended):
```bash
sbatch --partition=gh --export=ALL,IMAGE_PATH jobs/validate_rapids_image.sbatch
```
3. Export benchmark parameters:
```bash
# Optional if cluster default project is configured:
export SLURM_ACCOUNT=
export IMAGE_PATH=/scratch/$USER/containers/rapids.sif
export OUTPUT_ROOT=/scratch/$USER/tacc-gpu-geospatial
export POINTS=200000
export REPEATS=3
export SCENARIOS=temporal,bbox,maintenance,polygon_like
export BATCH_SIZE=50000
export MAINTENANCE_WINDOW=3600
export SLURM_PARTITION=gh
export VALIDATE_IMAGE=1
# Optional:
export DATA_PATH=
```
4. Submit:
```bash
bash jobs/submit_spatial_benchmark.sh
```
5. Inspect outputs:
- `$OUTPUT_ROOT/results/<timestamp>/benchmark_results.csv`
- `$OUTPUT_ROOT/results/<timestamp>/summary.json`
- `$OUTPUT_ROOT/results/<timestamp>/gpu_metrics.csv`

## Validation Checklist
1. GPU visibility:
- `nvidia-smi` appears in job logs.
2. RAPIDS imports:
- job logs show successful `cudf` and `cuspatial` import/version print.
3. End-to-end run:
- `benchmark_results.csv` and `summary.json` exist and are non-empty.
4. Runtime and memory footprint:
- documented in `docs/results_summary.md` and `docs/notes.md`.

## Failure Modes and Mitigations
1. `apptainer` not found:
- load `apptainer` or `apptainer-suid` module.
2. Image missing:
 - stage SIF on login node; verify path in `IMAGE_PATH`.
 - on Vista, use `jobs/pull_rapids_image.sbatch` to pull on a compute node.
 - default pull tag sequence currently starts at `rapidsai/base:26.02-cuda12-py3.11`.
3. Driver/CUDA mismatch:
- select RAPIDS image matching TACC node driver support.
4. Out-of-memory:
- reduce `POINTS`/`BATCH_SIZE`; shorten maintenance window.
5. Data schema mismatch:
- ensure dataset has `x`, `y`, `ts` columns or map with `--x-col/--y-col/--ts-col`.
