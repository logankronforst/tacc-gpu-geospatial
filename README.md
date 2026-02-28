# TACC GPU Geospatial Experiment

This repository is for running the RAPIDS geospatial experiment on TACC using GPU resources.

## Mission Context
This work supports spatio-temporal querying for dynamic environment updates and policy-learning workflows.

"Of course dont wish to spoil any weekend plans.... . Its integral, i believe to all our differential Hamiltonian Policy optimization learning, e.g. spatio-temporal querying of the environments by the mobile PIN-radio agent, as well as dynamic updates to the Gym too. Our group is developing PIN agents for dynamic adversarial networking response for the US Army."

## Feasibility on TACC
Status: High feasibility on standard GPU allocations.

## Hard Requirements
1. TACC GPU allocation (A100/H100 class preferred).
2. RAPIDS-compatible software stack (container or conda env).
3. CUDA driver/runtime compatibility for the chosen RAPIDS version.
4. Input datasets staged to TACC storage (`$SCRATCH` or project storage).
5. Batch or interactive job workflow (`sbatch` or equivalent).

## Deliverables
1. Reproducible environment setup (`env/` or container reference).
2. Job scripts for TACC (`jobs/`).
3. Query notebooks/scripts for spatial filtering and indexing (`src/`).
4. Runtime/performance notes (`docs/notes.md`).

## Handoff
See `AGENTS.md` and `skills/tacc-agent-handoff/SKILL.md`.
