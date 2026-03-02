# HACK: TACC RAPIDS Spatio-Temporal Benchmark

## Objective
Reproduce and benchmark GPU-accelerated spatio-temporal query and maintenance workflows on TACC using a script-first, containerized setup.

## Setup Snapshot

| Item | Value |
|---|---|
| Date | `2026-03-01` |
| Cluster | `Vista` |
| Image pull job | `602474` (`gh-dev`) |
| SIF path | `/scratch/11039/logankronforst/containers/rapids.sif` |
| Pulled image tag | `rapidsai/rapidsai:23.08a-cuda11.8.0-py3.10` |
| Benchmark submission at snapshot | `602502` (`gh`) |

## Status Snapshot (March 2, 2026)

### Have
- Working image candidate identified: `rapidsai/rapidsai:23.08a-cuda11.8.0-py3.10`.
- `cuspatial` import validated in a direct image probe: `cudf=True`, `cuspatial=True` in [`jobs/logs/test-tag-604303.out`](/work/11039/logankronforst/vista/tacc-gpu-geospatial/jobs/logs/test-tag-604303.out).
- Existing staged SIF is present at `/scratch/11039/logankronforst/containers/rapids.sif` and readable on the login filesystem.

### Don’t Have
- No successful end-to-end validation run yet under the final benchmark pipeline.
- No benchmark results yet for this case (`benchmark_results.csv`, `summary.json`, and `gpu_metrics.csv` remain unproduced in a fresh run).
- Prior non-fakeroot container validation failed to locate Python (`No usable python interpreter found inside container`) in [`jobs/logs/validate-rapids-image-604288.out`](/work/11039/logankforst/vista/tacc-gpu-geospatial/jobs/logs/validate-rapids-image-604288.out), which is why the pipeline now defaults to `--fakeroot`.
- Prior quick checks also showed missing `cuspatial` with some 26.04a candidate images, which is why 23.08a is now prioritized.

### Current Queue Status
- `604346` (`pull-rapids-sif`) : `PENDING (Priority)` on `gh`
- `604342` (`quick-rapidsui-val`) : `PENDING (Priority)` on `gh`
- `604239` (`geo-bench`) : `PENDING (DependencyNeverSatisfied)` on `gh`
- `604345` (`pull-rapids-sif`) : `PENDING (Resources)` on `gh-dev`

## Environment Strategy (Path A)
- Runtime: `Apptainer --nv` with pre-staged RAPIDS SIF.
- Rationale: strongest reproducibility and lower CUDA/Python mismatch risk on shared HPC.
- Compute nodes: assume no internet dependency.
- Login nodes: may be used for staging only.
- Vista policy: do not run Apptainer container runtime on login nodes; pull/validate/run through Slurm on GPU nodes.

## Software Dependencies
- `Slurm` (`sbatch`, `scontrol`)
- `Apptainer` or `apptainer-suid`
- NVIDIA GPU driver stack on compute nodes
- RAPIDS userland in container image:
  - `cudf`
  - `cuspatial`
  - `cupy`
  - Python 3.x compatible with selected RAPIDS build
- Runtime note: on current cluster images, `/opt/conda` may only be accessible via `apptainer --fakeroot`.
  Validation and benchmark jobs are configured to use `--fakeroot` by default.

## Constraints and Compatibility
- RAPIDS build must match node CUDA driver/runtime compatibility.
- SIF must be on storage visible to compute nodes (`/scratch/$USER/containers/rapids.sif` recommended).
- Input data should be staged to TACC storage (`$SCRATCH` or project storage).
- Workload size must fit allocation limits (GPU memory + walltime).

## Benchmark Scenarios
Implemented in `src/spatial_benchmark.py`:

| Scenario | Description |
|---|---|
| `temporal` | Windowed temporal filtering at multiple interval sizes |
| `bbox` | Spatial bounding-box filtering over full time range |
| `maintenance` | Incremental ingest + rolling temporal window + fixed ROI query |
| `polygon_like` | Strict regional filters approximating multi-region polygon-like constraints |

## Metrics Captured
- Scenario runtime: `elapsed_ms`
- Throughput: `throughput_rows_per_s`
- Cardinality: `result_rows`, `active_rows` (where applicable)
- Per-run GPU snapshots:
  - `gpu_util_pre`, `gpu_util_post`
  - `mem_used_mb_pre`, `mem_used_mb_post`, `mem_total_mb`
- Job telemetry sampled every 5 seconds:
  - `gpu_metrics.csv` from `nvidia-smi`

## GPU Utilization Guidance
Use `summary.json` and `gpu_metrics.csv` to tune allocation/workload balance:

| Condition | Indicators | Action |
|---|---|---|
| Under-utilized | `gpu_util_post_mean < 30%`; memory peak `< 30%` of total | Increase `POINTS` and/or `BATCH_SIZE`, or combine scenarios per job |
| Balanced | `gpu_util_post_mean ~ 50-85%`; memory peak `50-85%` | Keep sizing, increase `REPEATS` for better statistical confidence |
| Over-utilized | Sustained memory near/exceeding `90%`; unstable runtimes | Reduce `POINTS`/`BATCH_SIZE`, or move to larger-memory GPU |

## Allocation Sizing Guidance
- Starting point: `--cpus-per-task=12`, `--time=02:00:00`, GPU partition such as `gh`.
- Scale up when memory is consistently near saturation and queue budget allows.
- Scale down when runs complete quickly with consistently low GPU/memory utilization.

## Run Procedure
### 1) Stage RAPIDS image (one-time)
```bash
export IMAGE_PATH=/scratch/11039/logankronforst/containers/rapids.sif
mkdir -p /scratch/11039/logankronforst/containers jobs/logs
sbatch --partition=gh-dev --export=ALL,IMAGE_PATH jobs/pull_rapids_image.sbatch
```

### 2) Validate image on GPU node (recommended)
```bash
export USE_FAKEROOT=1
sbatch --partition=gh --export=ALL,IMAGE_PATH,USE_FAKEROOT jobs/validate_rapids_image.sbatch
```

### 3) Set benchmark environment
```bash
# Optional if cluster default project is already configured:
export SLURM_ACCOUNT=

export IMAGE_PATH=/scratch/11039/$USER/containers/rapids.sif
export OUTPUT_ROOT=/scratch/11039/$USER/tacc-gpu-geospatial
export POINTS=200000
export REPEATS=3
export SCENARIOS=temporal,bbox,maintenance,polygon_like
export BATCH_SIZE=50000
export MAINTENANCE_WINDOW=3600
export SLURM_PARTITION=gh
export VALIDATE_IMAGE=1
export USE_FAKEROOT=1

# Optional external dataset path:
export DATA_PATH=
```

### 4) Submit benchmark
```bash
bash jobs/submit_spatial_benchmark.sh
```

### 5) Review outputs
- `$OUTPUT_ROOT/results/<timestamp>/benchmark_results.csv`
- `$OUTPUT_ROOT/results/<timestamp>/summary.json`
- `$OUTPUT_ROOT/results/<timestamp>/gpu_metrics.csv`

## Validation Checklist
- GPU is visible in job logs (`nvidia-smi`).
- RAPIDS imports succeed (`cudf`, `cuspatial` visible in logs).
- End-to-end run produces non-empty:
  - `benchmark_results.csv`
  - `summary.json`
- Runtime and memory footprint are summarized in:
  - `docs/results_summary.md`
  - `docs/notes.md`

## Job Patch Checklist (When Retuning Runs)
- Confirm `SLURM_PARTITION` and optional `SLURM_ACCOUNT` are correct for current allocation.
- Confirm `IMAGE_PATH` exists and is readable from compute nodes.
- Confirm validation dependency is enabled (`VALIDATE_IMAGE=1`) before benchmark submit.
- Tune `POINTS`, `BATCH_SIZE`, `REPEATS`, `MAINTENANCE_WINDOW` based on utilization guidance above.
