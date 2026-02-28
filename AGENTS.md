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

## Required Outputs
1. `jobs/` with at least one batch script.
2. `src/` with executable query workflow.
3. `docs/` with runbook and results summary.

## Validation
- Confirm GPU visibility in job context.
- Confirm RAPIDS imports and end-to-end query run.
- Record runtime and memory footprint.
