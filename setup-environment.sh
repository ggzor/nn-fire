#!/usr/bin/env bash

set -euo pipefail

sudo yum update -y --quiet &>/dev/null

# Install Python 3.9 from source
echo "Installing python3.8"
(
  sudo amazon-linux-extras enable python3.8
  sudo yum install -y --quiet python38 python38-devel &>/dev/null

  sudo yum groupinstall -y --quiet "Development Tools" &>/dev/null
  sudo yum install -y --quiet openssl-devel bzip2-devel libffi-devel xz-devel &>/dev/null

  echo "Installing poetry..."
  curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py \
    | python3.8 -
) 1>/dev/null

# Install dependencies
(
  sudo yum install -y --quiet git &>/dev/null
  git clone --branch complete-blur https://github.com/ggzor/nn-fire
  cd nn-fire

  echo "Installing project dependencies..."
  ~/.local/bin/poetry install
)

