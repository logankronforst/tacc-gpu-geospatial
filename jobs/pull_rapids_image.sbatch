#!/bin/bash
#SBATCH --job-name=pull-rapids-sif
#SBATCH --time=00:30:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output=jobs/logs/%x-%j.out
#SBATCH --error=jobs/logs/%x-%j.err

set -euo pipefail

module purge
set +u
module load tacc-apptainer/1.4.1
set -u

IMAGE_PATH="${IMAGE_PATH:-/scratch/11039/${USER}/containers/rapids.sif}"
FORCE_PULL="${FORCE_PULL:-0}"

if [[ -f "${IMAGE_PATH}" && "${FORCE_PULL}" != "1" ]]; then
  echo "Image already exists at ${IMAGE_PATH}; skipping pull. Set FORCE_PULL=1 to refresh."
  exit 0
fi

mkdir -p "$(dirname "${IMAGE_PATH}")"

TAGS=(
  "rapidsai/rapidsai:23.08a-cuda11.8.0-py3.10"
  "rapidsai/notebooks:26.04a-cuda12-py3.12"
  "rapidsai/notebooks:26.04a-cuda12-py3.11"
  "rapidsai/base:26.04a-cuda12-py3.12"
  "rapidsai/notebooks:26.02a-cuda12-py3.12"
  "rapidsai/base:26.02a-cuda12-py3.12"
  "rapidsai/base:25.12a-cuda12-py3.11"
  "rapidsai/base:25.12a-cuda12-py3.10"
)

for tag in "${TAGS[@]}"; do
  echo "Trying docker://${tag}"
  if apptainer pull --force "${IMAGE_PATH}" "docker://${tag}"; then
    echo "Pulled ${tag} -> ${IMAGE_PATH}"
    exit 0
  fi
  echo "Failed tag ${tag}, trying next fallback"
done

echo "All RAPIDS image tag pulls failed."
exit 1
