#!/usr/bin/env bash

set -euo pipefail

source ./common.sh

case $1 in
  is-ready)
    run_ssh 'bash -s' <<< \
      '[[ -f ~/.local/bin/poetry ]] && \
       (( $(~/.local/bin/poetry env list | wc -l) > 0 ))'
    ;;
  send-file)
    run_ssh mkdir -p '~/temp'
    run_scp "$2" "ec2-user@$INSTANCE_IP:~/temp/$3"
    ;;
  retrieve-file)
    run_scp "ec2-user@$INSTANCE_IP:~/temp/$2" "$3"
    ;;
  run-with-file)
    run_ssh 'bash -s' <<< \
      "
      cd nn-fire/
      ~/.local/bin/poetry run python experimenter/remote.py '$2'
      "
    ;;
  *)
    echo "Unknown command: $1"
    exit 1
    ;;
esac

