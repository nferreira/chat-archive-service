#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:8000}"

usage() {
    cat <<EOF
Usage: $(basename "$0") --user-id ID --name NAME --question TEXT --answer TEXT

Store a chat message.

Options:
  --user-id   ID      User identifier (required)
  --name      NAME    User display name (required)
  --question  TEXT    Question text (required)
  --answer    TEXT    Answer text (required)
  -h, --help          Show this help
EOF
    exit 1
}

USER_ID="" NAME="" QUESTION="" ANSWER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user-id)  USER_ID="$2";  shift 2 ;;
        --name)     NAME="$2";     shift 2 ;;
        --question) QUESTION="$2"; shift 2 ;;
        --answer)   ANSWER="$2";   shift 2 ;;
        -h|--help)  usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

[[ -z "$USER_ID" || -z "$NAME" || -z "$QUESTION" || -z "$ANSWER" ]] && usage

exec curl -s -w "\n" -X POST "${BASE_URL}/api/v1/messages" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"${USER_ID}\", \"name\": \"${NAME}\", \"question\": \"${QUESTION}\", \"answer\": \"${ANSWER}\"}"
