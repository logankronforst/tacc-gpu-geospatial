# AGENTS.md

## Purpose
Operate this repo as a focused TACC geospatial experiment workspace.

## Scope
- Build and run cuDF/cuGraph/cuSpatial workflows for spatial query workloads.
- Keep setup reproducible for direct TACC handoff.

## Constraints
- Prefer non-interactive, scriptable workflows.
- Do not assume internet access on compute nodes.
- Stage data and dependencies from login nodes when needed.

## Vista Operational Notes (No Drift)
- Always pass a partition (`-p` / `--partition`) for `sbatch` on Vista.
- Use `gh` for GPU benchmark jobs; `gg` is not the target for this RAPIDS workflow.
- Apptainer execution on login nodes is restricted; run image pull/validation via Slurm jobs.
- Use `/scratch/11039/logankronforst/containers/rapids.sif` as the staged image path.
- Do not rely on fixed container Python paths; validate Python and RAPIDS imports in job context first.
- Use `SLURM_SUBMIT_DIR` for repo path resolution inside Slurm scripts (not `BASH_SOURCE` path under `/var/spool/slurmd`).

## Required Outputs
1. `jobs/` with at least one batch script.
2. `src/` with executable query workflow.
3. `docs/` with runbook and results summary.

## Validation
- Confirm GPU visibility in job context.
- Confirm RAPIDS imports and end-to-end query run.
- Record runtime and memory footprint.
