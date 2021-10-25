#!/usr/bin/env bash

set -euo pipefail

sudo yum update -y --quiet

# Install Python 3.9 from source
echo "Installing python3.8"
(
  sudo amazon-linux-extras enable python3.8
  sudo yum install -y --quiet python38 python38-devel

  sudo yum groupinstall -y --quiet "Development Tools"
  sudo yum install -y --quiet openssl-devel bzip2-devel libffi-devel xz-devel

  echo "Installing poetry..."
  curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py \
    | python3.8 -
) 1>/dev/null

# Run notebook
(
  sudo yum install -y --quiet git
  git clone --branch complete-blur https://github.com/ggzor/nn-fire
  cd nn-fire

  echo "Installing project dependencies..."
  ~/.local/bin/poetry install

  echo "Running notebook..."
  ( time ~/.local/bin/poetry run jupyter nbconvert \
    --to notebook \
    --execute notebook.ipynb \
    --output result.ipynb ) > performance.txt
)

# Generate results
mkdir results
mv nn-fire/result.ipynb results/
mv nn-fire/performance.txt results/

