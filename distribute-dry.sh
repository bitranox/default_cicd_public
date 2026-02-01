#!/usr/bin/env bash
# Dry run: show what would be distributed without making changes
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default search root: the fileshare (e.g., /media/srv-main-softdev or /mnt/share)
if [[ "$SCRIPT_DIR" == /media/* ]]; then
    DEFAULT_SEARCH_ROOT="/media/$(echo "$SCRIPT_DIR" | cut -d'/' -f3)"
elif [[ "$SCRIPT_DIR" == /mnt/* ]]; then
    DEFAULT_SEARCH_ROOT="/mnt/$(echo "$SCRIPT_DIR" | cut -d'/' -f3)"
else
    DEFAULT_SEARCH_ROOT="$(dirname "$SCRIPT_DIR")"
fi

exec uvx --from "$SCRIPT_DIR" default-cicd-public distribute \
    --source "$SCRIPT_DIR/.github" \
    --dry-run \
    --verbose \
    --search-root "${1:-$DEFAULT_SEARCH_ROOT}"
