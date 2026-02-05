#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

usage() {
    cat <<EOF
Usage: $(basename "$0") --day YYYY-MM-DD [--page-size N] [--page N]

Get messages for a specific day.

Options:
  --day         DATE  Date in YYYY-MM-DD format (required)
  --page-size   N     Results per page (1-200, default 50)
  --page        N     Page number (default 0)
  -h, --help          Show this help
EOF
    exit 1
}

DAY="" PAGE_SIZE="" PAGE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --day)        DAY="$2";       shift 2 ;;
        --page-size)  PAGE_SIZE="$2"; shift 2 ;;
        --page)       PAGE="$2";      shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

[[ -z "$DAY" ]] && usage

PARAMS="day=${DAY}"
[[ -n "$PAGE_SIZE" ]] && PARAMS="${PARAMS}&page_size=${PAGE_SIZE}"
[[ -n "$PAGE" ]]      && PARAMS="${PARAMS}&page=${PAGE}"

exec curl -s -w "\n" "${BASE_URL}/api/v1/messages?${PARAMS}"
