#!/usr/bin/env bash

set -euo pipefail

# Update system dependencies
echo "Installing missing dependencies..."
(
sudo yum update -y
sudo yum groupinstall -y "Development Tools"
sudo yum -y install openssl-devel bzip2-devel libffi-devel xz-devel
sudo yum -y install wget
) 1>/dev/null

# Install Python 3.9 from source
echo "Installing python3.9 from source..."
(
  wget -nv 'https://www.python.org/ftp/python/3.9.7/Python-3.9.7.tgz'
  tar -xvf 'Python-3.9.7.tgz'
  cd Python-3.9*

  ./configure --enable-optimizations &>/dev/null
  sudo make altinstall &>/dev/null

  echo "Installing poetry..."
  pip3.9 install --user poetry &>/dev/null
) 1>/dev/null

# Run notebook
(
  git clone --branch main https://github.com/ggzor/nn-fire
  cd nn-fire

  echo "Installing project dependencies..."
  ~/.local/bin/poetry install 1>/dev/null

  echo "Running notebook..."
  ( time ~/.local/bin/poetry run jupyter nbconvert \
    --to notebook \
    --execute notebook.ipynb \
    --output result.ipynb ) &> performance.txt
)

# Generate results
mkdir results
mv nn-fire/result.ipynb results/
mv nn-fire/performance.txt results/

