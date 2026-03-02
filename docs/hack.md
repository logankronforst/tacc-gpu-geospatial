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

## Proven Environment

- Python interpreter discovered and used by all successful jobs: `/opt/conda/bin/python` (or `/opt/conda/bin/python3`).
- Validation output for image (job `604458`): `python` `3.10.12`, `cudf` `23.08.00`, `cuspatial` `23.08.00`.
- Runtime command path used in passing benchmark jobs: `apptainer exec --nv --fakeroot -B ... "${IMAGE_PATH}" bash -lc`.
- RAPIDS validation in running jobs includes `import cudf`, `import cuspatial`, `import cupy`.
- Critical behavior confirmation: synthetic point generation succeeded using cupy RNG API `cp.random.RandomState(seed).rand(...)`.
- Gap for reproducibility: `cupy.__version__` was not emitted in historical logs, but cupy import and execution path both succeeded.

## Blocker Ledger (All major blockers addressed)

- `Image selector` (blocking): initial pull attempts across nightly `rapidsai` tags (`26.04a*`, `26.02a*`, `25.12a*`) passed image conversion but did not provide `cuspatial` or used mismatched RAPIDS/Python stacks for this workflow.
  - Evidence in logs: `quick-pkgcheck` and `quick-rapidsui` checks reported `cuspatial False` for those tags.
  - Fix: switched to `rapidsai/rapidsai:23.08a-cuda11.8.0-py3.10` and confirmed `cudf 23.08.00` + `cuspatial 23.08.00`.
- `In-container Python discovery` (blocking): early validation runs in `validate-rapids-image` could not find a usable interpreter (`No usable python interpreter found inside container`).
  - Fix: `jobs/validate_rapids_image.sbatch` and `jobs/spatial_benchmark.sbatch` now probe a deterministic candidate list and PATH fallback (`/opt/conda/bin`, `/usr/bin`, `/usr/local/bin`, `PATH`, then filesystem search), then print the chosen interpreter.
- `Python compatibility mode` (blocking): `--fakeroot` was inconsistent across runs.
  - Fix: both benchmark and validation scripts default to `USE_FAKEROOT=1`; wrapper exports this explicitly.
- `cuPy API compatibility` (blocking): benchmark crashed with `AttributeError: 'RandomState' object has no attribute 'random'` on the first full run.
  - Fix: changed synthetic payload call to `cp.random.RandomState(seed).rand(...)` in `src/spatial_benchmark.py`.
- `Workflow dependency chain` (blocking): queue job `604239` is blocked as `DependencyNeverSatisfied` because the validating precursor job (`604238`) failed.
  - Fix path: continue by launching independent jobs when needed; maintain dependency checks before chained submit.

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

- `2026-03-02` `604458` - `validate-rapids-image` - `PASSED`; Evidence: `python 3.10.12`, `cudf 23.08.00`, `cuspatial 23.08.00`.
- `2026-03-02` `604471` - `FAILED`; Error: `AttributeError: 'RandomState' object has no attribute 'random'` (cuPy API mismatch path).
- `2026-03-02` `604507` - `COMPLETED`; Exit `0:0`, runtime `00:00:16`, node `c639-021`, artifacts `/scratch/11039/logankronforst/tacc-gpu-geospatial/results/20260302_122356`.
- `2026-03-02` `604513` - `COMPLETED`; Exit `0:0`, runtime `00:00:16`, node `c640-032`, artifacts `/scratch/11039/logankronforst/tacc-gpu-geospatial/results/20260302_122357`.

## Authoritative Results (single source of truth)

Authoritative results are recorded per timestamp in `results_summary.md` and backed by three artifacts each.
- `20260302_122356` is the first successful benchmark run: artifacts are `benchmark_results.csv`, `summary.json`, `gpu_metrics.csv` under `/scratch/11039/logankronforst/tacc-gpu-geospatial/results/20260302_122356` with `results_count=36`, `rows_out=722,815`, `elapsed_ms_mean=2.444148461`, `gpu_util_post_mean=0.75`.
- `20260302_122357` is the second successful benchmark run: artifacts are `benchmark_results.csv`, `summary.json`, `gpu_metrics.csv` under `/scratch/11039/logankronforst/tacc-gpu-geospatial/results/20260302_122357` with `results_count=36`, `rows_out=722,815`, `elapsed_ms_mean=2.5244453715`, `gpu_util_post_mean=0.8611111111`.

### Authoritative Results Matrix (machine-readable)

| Run | Status | rows_out | elapsed_ms_mean | gpu_util_post_mean |
|---|---|---|---|---|
| `20260302_122356` | `SUCCESS` | `722,815` | `2.444148461` | `0.75` |
| `20260302_122357` | `SUCCESS` | `722,815` | `2.5244453715` | `0.8611111111` |

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
  - Python 3.10.12 observed in validation and benchmark context

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

### 6) Validate output quality
```bash
python3 scripts/validate_benchmark_results.py /scratch/11039/logankronforst/tacc-gpu-geospatial/results/<timestamp>
```

The validator checks:
- presence of all required artifacts
- expected CSV schema and numeric sanity
- summary consistency (`results_count`, `rows_out`, `elapsed_ms_mean`)
- required scenario coverage
- GPU metrics parseability

## Validation Checklist
- GPU is visible in job logs (`nvidia-smi`).
- RAPIDS imports succeed (`cudf`, `cuspatial`) in logs.
- End-to-end run produces non-empty:
  - `benchmark_results.csv`
  - `summary.json`
  - `gpu_metrics.csv`
- Post-run validator passes (`scripts/validate_benchmark_results.py`).

## Job Patch Checklist (When Retuning Runs)
- Confirm `SLURM_PARTITION` and optional `SLURM_ACCOUNT` are correct for current allocation.
- Confirm `IMAGE_PATH` exists and is readable from compute nodes.
- Confirm validation dependency behavior before benchmark submit (if using manual chain).
- Tune `POINTS`, `BATCH_SIZE`, `REPEATS`, `MAINTENANCE_WINDOW` based on utilization guidance.
