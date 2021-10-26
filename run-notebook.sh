#!/usr/bin/env bash

set -euo pipefail

mkdir -p result

echo "Running notebook..."

(
  cd nn-fire
  time ~/.local/bin/poetry run jupyter nbconvert \
    --to notebook \
    --execute notebook.ipynb \
    --output result.ipynb \
    --debug
) | tee result/performance.txt

cp nn-fire/result.ipynb result/

