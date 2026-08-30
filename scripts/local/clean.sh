#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ACTION="${1:-legacy}"
CONFIRM=0
[[ "${2:-}" == "--confirm" || "${1:-}" == "--confirm" ]] && CONFIRM=1
[[ "$ACTION" == "legacy" || "$ACTION" == "--confirm" ]] || {
  echo "Usage: ./rtgs clean legacy [--confirm]" >&2
  exit 2
}

mapfile -t files < <(find "$ROOT_DIR/data/matches" -mindepth 2 -maxdepth 2 -type f -name team_classifier.pkl 2>/dev/null | sort)
if ((${#files[@]} == 0)); then
  echo "No legacy team_classifier.pkl artifacts were found."
  exit 0
fi

echo "Legacy classifier artifacts:"
du -h "${files[@]}"
if ((!CONFIRM)); then
  echo "Dry run only. Re-run './rtgs clean legacy --confirm' to move them into data/.trash/."
  exit 0
fi

trash="$ROOT_DIR/data/.trash/legacy-classifiers-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$trash"
for source in "${files[@]}"; do
  match_id="$(basename "$(dirname "$source")")"
  mkdir -p "$trash/$match_id"
  mv "$source" "$trash/$match_id/team_classifier.pkl"
done
echo "Moved ${#files[@]} artifact(s) to $trash. They can be restored until that directory is deleted manually."
