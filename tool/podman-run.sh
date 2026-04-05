#!/bin/bash
# Wrapper to run podman image with automatic volume mounting for output
IMAGE="$1"
shift
ARGS=("$@")
MOUNT_ARGS=()

# Find --output path and mount its directory
for i in "${!ARGS[@]}"; do
  if [[ "${ARGS[i]}" == "--output" ]]; then
    VAL="${ARGS[i+1]}"
    if [[ -n "$VAL" && "$VAL" != "-" ]]; then
      # Get absolute directory of the output file
      # Use readlink -f to get absolute path even if file doesnt exist
      ABS_PATH=$(readlink -f "$VAL")
      DIR=$(dirname "$ABS_PATH")
      if [ -d "$DIR" ]; then
        MOUNT_ARGS+=("-v" "$DIR:$DIR:Z")
      fi
    fi
  fi
done

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
exec podman run --rm --network host -i "${MOUNT_ARGS[@]}" "$IMAGE" "${ARGS[@]}"
