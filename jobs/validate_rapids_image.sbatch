#!/bin/bash
#SBATCH --job-name=validate-rapids-image
#SBATCH --time=00:10:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output=jobs/logs/%x-%j.out
#SBATCH --error=jobs/logs/%x-%j.err

set -euo pipefail

REPO_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
IMAGE_PATH="${IMAGE_PATH:-/scratch/${USER}/containers/rapids.sif}"

mkdir -p "${REPO_DIR}/jobs/logs"

if [[ ! -f "${IMAGE_PATH}" ]]; then
  echo "Image not found: ${IMAGE_PATH}"
  exit 1
fi

set +u
module purge
module load tacc-apptainer/1.4.1 || module load apptainer || module load apptainer-suid || true
set -u

if ! command -v apptainer >/dev/null 2>&1; then
  echo "apptainer executable not found"
  exit 1
fi

echo "=== Host GPU check ==="
nvidia-smi

echo "=== Container RAPIDS check ==="
apptainer exec --nv "${IMAGE_PATH}" bash -lc '
  set -euo pipefail
  echo "PATH=${PATH}"
  command -v python3 || true
  command -v python || true

  PYTHON_BIN=""
  for candidate in \
    /opt/conda/bin/python \
    /opt/conda/bin/python3 \
    /usr/bin/python3 \
    /usr/local/bin/python3 \
    /usr/bin/python \
    /usr/local/bin/python
  do
    if [[ -x "${candidate}" ]]; then
      PYTHON_BIN="${candidate}"
      break
    fi
  done

  if [[ -z "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="$(command -v python3 || command -v python || true)"
  fi

  if [[ -z "${PYTHON_BIN}" ]]; then
    echo "No usable python interpreter found inside container."
    exit 1
  fi

  echo "Using PYTHON_BIN=${PYTHON_BIN}"
  "${PYTHON_BIN}" -V
  "${PYTHON_BIN}" - <<PY
import platform
import cudf
import cuspatial
print("python", platform.python_version())
print("cudf", getattr(cudf, "__version__", "unknown"))
print("cuspatial", getattr(cuspatial, "__version__", "unknown"))
PY
'

echo "Image validation passed."
