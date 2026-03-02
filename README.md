# TACC GPU Geospatial Experiment

RAPIDS-based, container-first spatio-temporal benchmark harness for TACC GPU nodes.

## Mission Context
This workspace benchmarks geospatial query and maintenance workloads that support dynamic environment updates and policy-learning loops.

## Path A: Container-First (Apptainer) Quickstart
1. Stage RAPIDS SIF (one-time, via batch on Vista):
```bash
export IMAGE_PATH=/scratch/11039/$USER/containers/rapids.sif
mkdir -p /scratch/11039/$USER/containers jobs/logs
sbatch --partition=gh-dev --export=ALL,IMAGE_PATH jobs/pull_rapids_image.sbatch
```
2. Export your benchmark parameters:
```bash
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
# Optional dataset path (parquet/csv with x,y,ts columns)
export DATA_PATH=
```
3. Submit the benchmark:
```bash
bash jobs/submit_spatial_benchmark.sh
```
This now submits `jobs/validate_rapids_image.sbatch` first and runs the benchmark only if validation succeeds (`afterok` dependency).
4. Artifacts are written under:
`$OUTPUT_ROOT/results/<timestamp>/`

## Repository Outputs
- `jobs/spatial_benchmark.sbatch`: batch benchmark job with GPU telemetry capture.
- `jobs/submit_spatial_benchmark.sh`: submission wrapper with exported parameters.
- `src/spatial_benchmark.py`: executable spatio-temporal benchmark workflow.
- `docs/hack.md`: benchmark runbook, dependency and constraint notes, scenario definitions.
- `docs/results_summary.md`: experiment logging template.
- `docs/notes.md`: concise runtime notes scaffold.
- `scripts/validate_benchmark_results.py`: authoritative post-run validator for benchmark output artifacts.

## Handoff
See `AGENTS.md` and `skills/tacc-agent-handoff/SKILL.md`.
