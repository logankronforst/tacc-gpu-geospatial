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
3. Stage datasets to `$SCRATCH`.
4. Execute batch workflow from `jobs/`.
5. Validate outputs and capture metrics.

## Non-Negotiables
- Version pinning for RAPIDS/CUDA.
- Script-first execution (no manual-only steps).
- Logging of parameters and output paths.

## Known Risks
- Driver/library mismatch.
- Data staging bottlenecks.
- Node variability if resource requests are underspecified.
