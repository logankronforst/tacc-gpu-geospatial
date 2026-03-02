# HACK: TACC RAPIDS Spatio-Temporal Benchmark

## Objective
Reproduce and benchmark GPU-accelerated spatio-temporal query and maintenance workflows on TACC using a reproducible, containerized setup.

## Setup Snapshot

| Item | Value |
|---|---|
| Date | `2026-03-01` |
| Cluster | `Vista` |
| Image pull job | `602474` (`gh-dev`) |
| SIF path | `/scratch/11039/logankronforst/containers/rapids.sif` |
| Pulled image tag | `rapidsai/rapidsai:23.08a-cuda11.8.0-py3.10` |
| Staged container | present and readable |

## Status Snapshot (March 2, 2026)

### What Works
- End-to-end image validation passes on login policy-compliant GPU job (`validate-rapids-image`, job `604458`).
  - RAPIDS versions: `python 3.10.12`, `cudf 23.08.00`, `cuspatial 23.08.00`.
- Full benchmark sweep executed successfully with full scenarios (`temporal`, `bbox`, `maintenance`, `polygon_like`) on two parallel Slurm jobs.
  - `604507` -> completed successfully on `c639-021` in `00:00:16`
  - `604513` -> completed successfully on `c640-032` in `00:00:16`
- Both completed jobs produced all expected artifacts under:
  - `/scratch/11039/logankronforst/tacc-gpu-geospatial/results/20260302_122356/`
  - `/scratch/11039/logankronforst/tacc-gpu-geospatial/results/20260302_122357/`
- Successful outputs per run:
  - `benchmark_results.csv`
  - `summary.json`
  - `gpu_metrics.csv`
- Representative aggregate metrics (successful run `20260302_122357`):
  - `elapsed_ms_mean`: `2.5244453715`
  - `gpu_util_post_mean`: `0.8611111111`
  - `max_mem_used_mb_post`: `583`
  - `rows_out`: `722,815`
- GPU context is visible and correctly bound in logs via `nvidia-smi`.

### Failures and Fixes
- Failure: `validate-rapids-image` non-fakeroot path could not find a usable Python in early runs.
  - Fix: defaulted benchmark/validation jobs to `--fakeroot` and explicit Python candidate probing.
- Failure: initial `604471` run crashed with `AttributeError: 'RandomState' object has no attribute 'random'`.
  - Fix: updated synthetic payload generation from `rng.random(...)` to `rng.rand(...).astype(cp.float32)` in `src/spatial_benchmark.py` (commit `4ee0556`).
- Failure: earlier candidate images with quick checks showed missing `cuspatial`.
  - Fix: switched image preference to `23.08a-cuda11.8.0-py3.10`.

### Current Queue Status
- `604239` (`geo-bench`) : `PENDING (DependencyNeverSatisfied)` on `gh` (dependency on failed `604238`)
- Historical/one-off queue artifacts are no longer active: `604346`, `604342`, `604345`.

## Run Log

| Date | Jobs | Status | Notes |
|---|---|---|---|
| 2026-03-02 | `604458` | Validation passed | `validate-rapids-image` job confirmed `python 3.10.12`, `cudf 23.08.00`, `cuspatial 23.08.00` |
| 2026-03-02 | `604471` | Failed (RNG API) | `RandomState.random` is not available in this cupy version; fixed in source (`rng.rand`) |
| 2026-03-02 | `604507` | Completed | Artifacts in `results/20260302_122356`, exit `0:0`, runtime `00:00:16`, node `c639-021` |
| 2026-03-02 | `604513` | Completed | Artifacts in `results/20260302_122357`, exit `0:0`, runtime `00:00:16`, node `c640-032` |

## Authoritative Results (single source of truth)

| Run | Status | Artifacts | Key Summary |
|---|---|---|---|
| `20260302_122356` | Success | `benchmark_results.csv`, `summary.json`, `gpu_metrics.csv` | `results_count=36`, `rows_out=722,815`, `elapsed_ms_mean=2.444148461`, `gpu_util_post_mean=0.75` |
| `20260302_122357` | Success | `benchmark_results.csv`, `summary.json`, `gpu_metrics.csv` | `results_count=36`, `rows_out=722,815`, `elapsed_ms_mean=2.5244453715`, `gpu_util_post_mean=0.8611111111` |

Canonical result reference: [results_summary.md](results_summary.md)

## Environment Strategy (Path A)
- Runtime: `Apptainer --nv` with pre-staged RAPIDS SIF.
- Rationale: reproducibility and lower CUDA/Python mismatch risk on shared HPC.
- Compute nodes: no internet dependency.
- Login nodes: staging only.
- Vista policy: do not run Apptainer container runtime on login nodes; pull/validate/run through Slurm GPU jobs.

## Software Dependencies
- `Slurm` (`sbatch`, `scontrol`)
- `Apptainer` or `apptainer-suid`
- NVIDIA GPU driver stack on compute nodes
- RAPIDS userland in container image:
  - `cudf`
  - `cuspatial`
  - `cupy`
  - Python 3.x compatible with selected RAPIDS build

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
export SEED=42
export SLURM_PARTITION=gh
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
- RAPIDS imports succeed (`cudf`, `cuspatial`) in logs.
- End-to-end run produces non-empty:
  - `benchmark_results.csv`
  - `summary.json`
  - `gpu_metrics.csv`

## Job Patch Checklist (When Retuning Runs)
- Confirm `SLURM_PARTITION` and optional `SLURM_ACCOUNT` are correct for current allocation.
- Confirm `IMAGE_PATH` exists and is readable from compute nodes.
- Confirm validation dependency behavior before benchmark submit (if using manual chain).
- Tune `POINTS`, `BATCH_SIZE`, `REPEATS`, `MAINTENANCE_WINDOW` based on utilization guidance.
