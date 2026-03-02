#!/bin/bash
#SBATCH --job-name=geo-bench
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --output=jobs/logs/%x-%j.out
#SBATCH --error=jobs/logs/%x-%j.err

set -euo pipefail
set -x

module purge

# Optional: request a specific GPU partition/quality of service if required by site policy.
# #SBATCH --partition=gpu

REPO_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DATA_PATH="${DATA_PATH:-}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/scratch/11039/${USER}/tacc-gpu-geospatial}"
IMAGE_PATH="${IMAGE_PATH:-/scratch/11039/${USER}/containers/rapids.sif}"
USE_FAKEROOT="${USE_FAKEROOT:-1}"
RESULT_ROOT="${OUTPUT_ROOT}/results/${TIMESTAMP}"
RUN_DIR="${OUTPUT_ROOT}/runs/${TIMESTAMP}"

POINTS="${POINTS:-200000}"
REPEATS="${REPEATS:-3}"
SCENARIOS="${SCENARIOS:-temporal,bbox,maintenance,polygon_like}"
SEED="${SEED:-1337}"
BATCH_SIZE="${BATCH_SIZE:-50000}"
MAINTENANCE_WINDOW="${MAINTENANCE_WINDOW:-3600}"

mkdir -p "${RUN_DIR}" "${RESULT_ROOT}" "${REPO_DIR}/jobs/logs"
mkdir -p "${RUN_DIR}/apptainer-tmp" "${RUN_DIR}/apptainer-cache"

export TMPDIR="${RUN_DIR}/apptainer-tmp"
export APPTAINER_TMPDIR="${RUN_DIR}/apptainer-tmp"
export APPTAINER_CACHEDIR="${RUN_DIR}/apptainer-cache"
export SINGULARITY_TMPDIR="${RUN_DIR}/apptainer-tmp"
export SINGULARITY_CACHEDIR="${RUN_DIR}/apptainer-cache"

cat <<EOF > "${RUN_DIR}/job-env.txt"
JOB_ID=${SLURM_JOB_ID}
JOB_NAME=${SLURM_JOB_NAME}
POINTS=${POINTS}
REPEATS=${REPEATS}
SCENARIOS=${SCENARIOS}
SEED=${SEED}
BATCH_SIZE=${BATCH_SIZE}
MAINTENANCE_WINDOW=${MAINTENANCE_WINDOW}
IMAGE_PATH=${IMAGE_PATH}
DATA_PATH=${DATA_PATH}
OUTPUT_ROOT=${OUTPUT_ROOT}
RESULT_ROOT=${RESULT_ROOT}
EOF

if [[ ! -f "${IMAGE_PATH}" ]]; then
  echo "RAPIDS image not found at ${IMAGE_PATH}."
  echo "Set IMAGE_PATH to a pre-staged Apptainer SIF before submitting."
  exit 1
fi

if ! command -v apptainer >/dev/null 2>&1; then
  set +u
  module load tacc-apptainer/1.4.1 || module load apptainer || module load apptainer-suid || true
  set -u
fi

if ! command -v apptainer >/dev/null 2>&1; then
  echo "apptainer executable not found after module load attempt."
  exit 1
fi

cd "${REPO_DIR}"

echo "=== Job context ==="
scontrol show job ${SLURM_JOB_ID}
nvidia-smi

# Capture coarse GPU utilization timeline during the benchmark.
nvidia-smi \
  --query-gpu=timestamp,index,utilization.gpu,utilization.memory,memory.used,memory.total \
  --format=csv,noheader,nounits \
  -l 5 > "${RUN_DIR}/gpu_metrics.csv" &
GPU_MONITOR_PID=$!
trap 'kill ${GPU_MONITOR_PID} >/dev/null 2>&1 || true' EXIT

FAKEROOT_FLAG=""
if [[ "${USE_FAKEROOT}" == "1" ]]; then
  FAKEROOT_FLAG="--fakeroot"
  echo "Using --fakeroot for container execution."
fi

apptainer exec ${FAKEROOT_FLAG} --nv \
  -B "${REPO_DIR}:/workspace" \
  -B "${OUTPUT_ROOT}:/output" \
  -B "${RUN_DIR}:/run" \
  "${IMAGE_PATH}" \
  bash -lc '
    echo "=== Container diagnostics ==="
    echo "PATH=${PATH}"
    command -v python3 || true
    command -v python || true
    ls -l /opt/conda/bin 2>/dev/null | head -n 20 || true

    PYTHON_BIN=""
    shopt -s nullglob
    for candidate in \
      /opt/conda/bin/python \
      /opt/conda/bin/python3 \
      /usr/bin/python3 \
      /usr/local/bin/python3 \
      /usr/bin/python \
      /usr/local/bin/python \
      /bin/python3 \
      /bin/python \
      /usr/local/anaconda*/bin/python \
      /usr/local/anaconda*/bin/python3 \
      /opt/conda/envs/*/bin/python \
      /opt/conda/envs/*/bin/python3 \
      /usr/bin/python3.* \
      /bin/python3.*
    do
      if [[ -x "${candidate}" ]]; then
        PYTHON_BIN="${candidate}"
        break
      fi
    done

    if [[ -z "${PYTHON_BIN}" ]]; then
      for p in $(echo "${PATH}" | tr ":" "\n"); do
        if [[ -x "${p}/python3" ]]; then
          PYTHON_BIN="${p}/python3"
          break
        fi
        if [[ -x "${p}/python" ]]; then
          PYTHON_BIN="${p}/python"
          break
        fi
      done
    fi

    if [[ -z "${PYTHON_BIN}" ]]; then
      echo "PATH candidates checked:"
      for p in $(echo "${PATH}" | tr ":" "\n"); do
        printf "%s\n" "${p}/python3" "${p}/python"
      done
      echo "No python executable found via PATH scan."
      find /usr /opt /bin /home /root -maxdepth 4 -type f -name 'python*' 2>/dev/null | head -n 40 || true
    fi

    if [[ -z "${PYTHON_BIN}" ]]; then
      for candidate in $(find / -xdev -maxdepth 6 -type f -name "python*" 2>/dev/null); do
        if [[ -x "${candidate}" ]]; then
          case "$(basename "${candidate}")" in
            python|python3|python3.*|python[0-9]*)
              PYTHON_BIN="${candidate}"
              break
              ;;
          esac
        fi
      done
    fi

    if [[ -z "${PYTHON_BIN}" ]]; then
      PYTHON_BIN="$(command -v python3 || command -v python || true)"
    fi

    if [[ -z "${PYTHON_BIN}" ]]; then
      echo "No usable python interpreter found inside container."
      exit 1
    fi
    echo "Using PYTHON_BIN=${PYTHON_BIN}"
    cd /workspace
    "${PYTHON_BIN}" - <<PY
import cudf, cuspatial
import platform
print("RAPIDS versions", {
    "python": platform.python_version(),
    "cudf": getattr(cudf, "__version__", "unknown"),
    "cuspatial": getattr(cuspatial, "__version__", "unknown"),
})
PY
    "${PYTHON_BIN}" /workspace/src/spatial_benchmark.py \
      --output-dir /run \
      --scenario-list ${SCENARIOS} \
      --points ${POINTS} \
      --repeats ${REPEATS} \
      --batch-size ${BATCH_SIZE} \
      --maintenance-window ${MAINTENANCE_WINDOW} \
      --seed ${SEED} \
      ${DATA_PATH:+--data-path ${DATA_PATH}} \
      --result-csv benchmark_results.csv \
      --result-json summary.json
  '

cp -v "${RUN_DIR}/benchmark_results.csv" "${RESULT_ROOT}/benchmark_results.csv"
cp -v "${RUN_DIR}/summary.json" "${RESULT_ROOT}/summary.json"
cp -v "${RUN_DIR}/gpu_metrics.csv" "${RESULT_ROOT}/gpu_metrics.csv"

echo "Artifacts written to ${RESULT_ROOT}"
