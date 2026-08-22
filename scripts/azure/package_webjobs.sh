#!/usr/bin/env bash
set -euo pipefail

out_dir="${1:-$(mktemp -d)}"
mkdir -p "$out_dir"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

for job in worker migrate; do
  mkdir -p "$tmp_dir/$job"
  cp "deploy/webjobs/$job/run.sh" "deploy/webjobs/$job/settings.job" "$tmp_dir/$job/"
  chmod 0755 "$tmp_dir/$job/run.sh"
  touch -t 198001010000 "$tmp_dir/$job" "$tmp_dir/$job/run.sh" "$tmp_dir/$job/settings.job"
  (cd "$tmp_dir" && zip -X -q -r "$out_dir/$job.zip" "$job")
  shasum -a 256 "$out_dir/$job.zip" | awk '{print $1}' > "$out_dir/$job.zip.sha256"
done

printf 'WEBJOBS_OUTPUT=%s\n' "$out_dir"
