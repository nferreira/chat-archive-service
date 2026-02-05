#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

usage() {
    cat <<EOF
Usage: $(basename "$0") --user-id ID --start YYYY-MM-DD --end YYYY-MM-DD [--page-size N] [--page N]

Get messages for a specific user within a date range.

Options:
  --user-id     ID    User identifier (required)
  --start       DATE  Start date in YYYY-MM-DD format (required)
  --end         DATE  End date in YYYY-MM-DD format (required)
  --page-size   N     Results per page (1-200, default 50)
  --page        N     Page number (default 0)
  -h, --help          Show this help
EOF
    exit 1
}

USER_ID="" START="" END="" PAGE_SIZE="" PAGE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user-id)    USER_ID="$2";   shift 2 ;;
        --start)      START="$2";     shift 2 ;;
        --end)        END="$2";       shift 2 ;;
        --page-size)  PAGE_SIZE="$2"; shift 2 ;;
        --page)       PAGE="$2";      shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

[[ -z "$USER_ID" || -z "$START" || -z "$END" ]] && usage

PARAMS="start=${START}&end=${END}"
[[ -n "$PAGE_SIZE" ]] && PARAMS="${PARAMS}&page_size=${PAGE_SIZE}"
[[ -n "$PAGE" ]]      && PARAMS="${PARAMS}&page=${PAGE}"

exec curl -s -w "\n" "${BASE_URL}/api/v1/users/${USER_ID}/messages?${PARAMS}"
