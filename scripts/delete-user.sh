#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

usage() {
    cat <<EOF
Usage: $(basename "$0") --user-id ID

Delete a user and all their messages.

Options:
  --user-id   ID    User identifier (required)
  -h, --help        Show this help
EOF
    exit 1
}

USER_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user-id) USER_ID="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

[[ -z "$USER_ID" ]] && usage

exec curl -s -w "\n" -X DELETE "${BASE_URL}/api/v1/users/${USER_ID}"
