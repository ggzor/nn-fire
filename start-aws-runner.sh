#!/usr/bin/env bash

set -euo pipefail

if (( $# < 2 || $# > 3 )); then
  cat <<EOF
Usage: $0 STACK_NAME KEY_NAME [IMAGE=t4g.nano]"

STACK_NAME: The name to use to manage this stack.
KEY_NAME: The key to use from your account to allow SSH access
EOF
  exit 1
fi

STACK_NAME=$1
KEY_NAME=$2
IMAGE=${3:-t4g.nano}

stack_exists() {
  aws cloudformation describe-stacks --stack-name "$STACK_NAME" &>/dev/null
}

delete_stack() {
  echo "Deleting previously used stack..."
  aws cloudformation delete-stack --stack-name "$STACK_NAME"
}

cleanup_stack() {
  EXIT_CODE=$?

  if stack_exists; then
    delete_stack
  fi

  exit "$EXIT_CODE"
}

trap cleanup_stack SIGINT SIGTERM ERR EXIT

if stack_exists; then
  delete_stack

  echo "Waiting for delete completion..."
  aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"

  echo "Stack deleted successfully."
fi

echo "Creating a fresh stack..."
aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body file://template.yaml \
  --tags "Key=compute_stack,Value=$STACK_NAME" \
  --parameters ParameterKey=InstanceType,ParameterValue="$IMAGE" \
               ParameterKey=KeyName,ParameterValue="$KEY_NAME" \
  1>/dev/null

echo "Waiting for complete initialization..."
aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME"

INSTANCE_IP="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
  --query "Stacks[].Outputs[?OutputKey=='PublicIp'].OutputValue[]" \
  --output text)"

echo "The compute server IP is: $INSTANCE_IP"


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

echo "Connecting to instance..."

retry=0
max_retry=4
until run_ssh true; do
  if (( $retry >= 4 )); then
    echo "Giving up in retries."
    exit 1
  fi

  wait_time=$(( 2 ** $retry ))
  echo "Retry $retry: $wait_time s"
  sleep "$wait_time"

  (( retry += 1 ))
done

echo "Setting up the environment..."
run_scp ./setup-environment.sh ec2-user@"$INSTANCE_IP":~
run_ssh ./setup-environment.sh

echo "Runner ready. Press Ctrl+C to tear down."

delete_stack

echo "Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"

echo "Stack deleted succesfully"

