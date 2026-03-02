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
| Pulled image tag | `rapidsai/base:26.02-cuda12-py3.11` |
| Benchmark submission at snapshot | `602502` (`gh`) |

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
sbatch --partition=gh --export=ALL,IMAGE_PATH jobs/validate_rapids_image.sbatch
```

### 3) Set benchmark environment
```bash
# Optional if cluster default project is already configured:
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
