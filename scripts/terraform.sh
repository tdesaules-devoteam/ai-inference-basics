#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
operation=${1:?plan, apply or destroy required}
profile=${PROFILE:-scaleway-cpu-pilot}
session=${SESSION:?Set a unique SESSION identifier}
[[ $session =~ ^[a-z0-9][a-z0-9-]{2,30}$ ]] || { echo 'Invalid SESSION.' >&2; exit 1; }
case "$profile" in
  scaleway-cpu-pilot) ;;
  scaleway-h100)
    python3 - <<'PY'
import json
from pathlib import Path
p = Path('reports/scaleway-cpu-pilot/G4/acceptance.json')
if not p.is_file(): raise SystemExit('CPU cloud acceptance and cleanup evidence is required first.')
d = json.loads(p.read_text())
if not (d.get('passed') is True and d.get('cleanup_complete') is True):
    raise SystemExit('CPU cloud acceptance and cleanup have not both passed.')
PY
    ;;
  *) echo 'Only individual pilots are currently enabled.' >&2; exit 1 ;;
esac
binary="$ROOT/.local/bin/terraform"
[[ -x $binary ]] || { echo 'Install checksum-verified Terraform 1.17.2 in .local/bin/terraform.' >&2; exit 1; }
directory="$ROOT/.local/terraform/$session"
mkdir -p "$directory"
chmod 700 "$directory"
export TF_DATA_DIR="$directory/.terraform"
vars="$directory/inputs.tfvars.json"
[[ -s $vars ]] || { echo "Create protected inputs at $vars; see docs/cloud.md." >&2; exit 1; }
python3 - "$vars" "$profile" "$session" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
if path.stat().st_mode & 0o077: raise SystemExit('Terraform input file must be mode 0600.')
d = json.loads(path.read_text())
if d.get('environment', 'scaleway-cpu-pilot') != sys.argv[2]: raise SystemExit('PROFILE and input environment differ.')
if d.get('training_session_id') != sys.argv[3]: raise SystemExit('SESSION and input training_session_id differ.')
if d.get('instance_count', 1) != 1: raise SystemExit('Only a single pilot is enabled by this wrapper.')
PY
"$binary" -chdir=infra/terraform init -reconfigure -backend-config="path=$directory/terraform.tfstate" -input=false
case "$operation" in
  plan)
    umask 077
    "$binary" -chdir=infra/terraform plan -var-file="$vars" -out="$directory/plan.tfplan"
    ;;
  apply)
    [[ -s "$directory/plan.tfplan" ]] || { echo 'Run task infra:plan for this session first.' >&2; exit 1; }
    "$binary" -chdir=infra/terraform show -no-color "$directory/plan.tfplan"
    echo "Billable apply: profile=$profile session=$session. Review instance type/count, volumes and IPs above."
    read -r -p 'Type the session identifier to apply this exact plan: ' confirmation
    [[ $confirmation == "$session" ]] || exit 1
    "$binary" -chdir=infra/terraform apply "$directory/plan.tfplan"
    ;;
  destroy)
    "$binary" -chdir=infra/terraform plan -destroy -var-file="$vars" -out="$directory/destroy.tfplan"
    read -r -p "Type $session to destroy this session: " confirmation
    [[ $confirmation == "$session" ]] || exit 1
    "$binary" -chdir=infra/terraform apply "$directory/destroy.tfplan"
    echo 'Destroy finished. Provider inventory audit is still required; empty state alone is insufficient.'
    ;;
  *) echo 'Unknown Terraform operation.' >&2; exit 1 ;;
esac
