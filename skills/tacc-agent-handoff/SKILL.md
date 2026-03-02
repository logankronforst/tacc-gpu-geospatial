# SKILL: tacc-agent-handoff (GPU Geospatial)

## Goal
Enable a clean transfer to a TACC execution agent for RAPIDS geospatial experiments.

## Use This Skill When
- You need to stand up or resume the geospatial pipeline on TACC.
- You need a deterministic setup/run/validate loop.

## Steps
1. Verify allocation and GPU node target.
2. Select environment strategy:
   - Apptainer/NGC RAPIDS image, or
   - Conda RAPIDS environment pinned by CUDA compatibility.
3. Stage/validate RAPIDS image (`jobs/pull_rapids_image.sbatch`, then `jobs/validate_rapids_image.sbatch`).
4. Stage datasets to `$SCRATCH`.
5. Execute batch workflow from `jobs/` (with validation dependency enabled by default in submit wrapper).
6. Validate outputs and capture metrics.
7. Evaluate allocation efficiency and retune workload size.

## Non-Negotiables
- Version pinning for RAPIDS/CUDA.
- Script-first execution (no manual-only steps).
- Logging of parameters and output paths.
- Capture GPU telemetry (`nvidia-smi`) during benchmark runtime.
- Record runtime and memory footprint in docs.
- Validate container Python + RAPIDS imports on GPU node before benchmark submission.

## GPU Usage Guidance
- Target utilization:
- GPU compute utilization typically `50-85%` for balanced runs.
- Peak memory occupancy typically `50-85%` of total GPU memory.
- Under-utilization indicators:
- GPU utilization often below `30%`.
- GPU memory stays below `30%` for most scenarios.
- Over-utilization indicators:
- Repeated OOM or sustained memory above `90%`.
- Large timing variance across repeats due saturation.
- Tuning actions:
- Under-utilized: increase `POINTS`, `BATCH_SIZE`, or concurrent scenario breadth.
- Over-utilized: reduce `POINTS`, `BATCH_SIZE`, `MAINTENANCE_WINDOW`, or move to larger-memory GPU.
- Keep one GPU per task unless workload is explicitly distributed.

## Vista Issues and Applied Patches
- Partition requirement:
- Vista requires explicit queue selection (`--partition`), patched via submit workflow defaults (`gh`).
- Account handling:
- Explicit account may fail if site-side project aliases differ; submit wrapper allows optional `SLURM_ACCOUNT` and uses default when unset.
- Login-node container restriction:
- Apptainer pull/exec is done in Slurm jobs, not on login shell.
- Slurm path drift:
- Batch scripts now resolve repo root from `SLURM_SUBMIT_DIR` to avoid `/var/spool/slurmd` path errors.
- Module load with `set -u`:
- Module load is wrapped with temporary `set +u` to avoid shell-completion nounset failures.
- Container runtime temp/cache permissions:
- `APPTAINER_TMPDIR` and cache dirs are set into per-run scratch directories.
- Image-runtime uncertainty:
- Benchmark submit now chains image validation job (`afterok`) to avoid running benchmark against invalid image/runtime.
- Container interpreter discovery:
- Benchmark and validation scripts probe multiple Python candidate paths and print diagnostics.

## Known Risks
- Driver/library mismatch.
- Data staging bottlenecks.
- Node variability if resource requests are underspecified.
