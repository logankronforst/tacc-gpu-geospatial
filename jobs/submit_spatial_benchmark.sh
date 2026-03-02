#!/bin/bash
set -euo pipefail

# Wrapper for submitting the containerized TACC geospatial benchmark job.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export SLURM_ACCOUNT="${SLURM_ACCOUNT:-}"
export IMAGE_PATH="${IMAGE_PATH:-/scratch/${USER}/containers/rapids.sif}"
export OUTPUT_ROOT="${OUTPUT_ROOT:-/scratch/${USER}/tacc-gpu-geospatial}"
export DATA_PATH="${DATA_PATH:-}"
export SLURM_PARTITION="${SLURM_PARTITION:-gh}"
export POINTS="${POINTS:-200000}"
export REPEATS="${REPEATS:-3}"
export SCENARIOS="${SCENARIOS:-temporal,bbox,maintenance,polygon_like}"
export SEED="${SEED:-42}"
export BATCH_SIZE="${BATCH_SIZE:-50000}"
export MAINTENANCE_WINDOW="${MAINTENANCE_WINDOW:-3600}"
export VALIDATE_IMAGE="${VALIDATE_IMAGE:-1}"

mkdir -p "${OUTPUT_ROOT}/runs" "${OUTPUT_ROOT}/results" "${OUTPUT_ROOT}/logs"

SBATCH_ARGS=(
  --export=ALL,SLURM_ACCOUNT,SLURM_PARTITION,IMAGE_PATH,OUTPUT_ROOT,DATA_PATH,POINTS,REPEATS,SCENARIOS,SEED,BATCH_SIZE,MAINTENANCE_WINDOW
)

if [[ -n "${SLURM_ACCOUNT}" ]]; then
  SBATCH_ARGS+=(--account="${SLURM_ACCOUNT}")
fi

if [[ -n "${SLURM_PARTITION}" ]]; then
  SBATCH_ARGS+=(--partition="${SLURM_PARTITION}")
fi

if [[ "${VALIDATE_IMAGE}" == "1" ]]; then
  echo "Submitting image validation job first..."
  VALIDATE_SUBMIT_OUTPUT="$(sbatch "${SBATCH_ARGS[@]}" "${REPO_DIR}/jobs/validate_rapids_image.sbatch")"
  echo "${VALIDATE_SUBMIT_OUTPUT}"
  VALIDATE_JOB_ID="$(echo "${VALIDATE_SUBMIT_OUTPUT}" | rg -o '[0-9]+' | tail -n1)"
  if [[ -z "${VALIDATE_JOB_ID}" ]]; then
    echo "Could not parse validation job ID from sbatch output."
    exit 1
  fi
  echo "Validation job: ${VALIDATE_JOB_ID}"
  SBATCH_ARGS+=(--dependency=afterok:"${VALIDATE_JOB_ID}")
fi

sbatch "${SBATCH_ARGS[@]}" "${REPO_DIR}/jobs/spatial_benchmark.sbatch"
