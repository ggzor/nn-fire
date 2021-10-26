#!/usr/bin/env bash

set -euo pipefail

# We are going to connect to an ephemeral server
# No need to save keys
SSH_OPTIONS=(
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
)

run_ssh() {
  ssh "${SSH_OPTIONS[@]}" ec2-user@"$INSTANCE_IP" "$@"
}

run_scp() {
  scp "${SSH_OPTIONS[@]}" "$@"
}

