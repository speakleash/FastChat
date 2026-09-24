#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="../../.venv/bin/python3"
API_BASE="${PLGRID_API_BASE:-https://llmlab.plgrid.pl/api/v1}"
API_KEY="${PLGRID_API_KEY:?Set PLGRID_API_KEY}"

declare -A MODELS=(
  ["Qwen/Qwen3.6-27B"]="Qwen3.6-27B"
  ["Qwen/Qwen3.6-35B-A3B"]="Qwen3.6-35B-A3B"
)

for api_model in "${!MODELS[@]}"; do
  model_id="${MODELS[$api_model]}"
  answer_file="data/mt_bench/model_answer/${model_id}.jsonl"
  echo "=== $api_model ==="
  "$PYTHON" gen_api_answer.py \
    --model "$api_model" \
    --answer-file "$answer_file" \
    --openai-api-base "$API_BASE" \
    --openai-api-key "$API_KEY" \
    --disable-thinking \
    --parallel 8
done

# Remove old Qwen judgments before re-judging
JUDGMENT="data/mt_bench/model_judgment/google/gemma-4-31B_single.jsonl"
"$PYTHON" - <<'PY'
import json
path = "data/mt_bench/model_judgment/google/gemma-4-31B_single.jsonl"
models = {"Qwen3.6-27B", "Qwen3.6-35B-A3B"}
rows = []
with open(path) as f:
    for line in f:
        row = json.loads(line)
        if row.get("model") not in models:
            rows.append(line)
with open(path, "w") as f:
    f.writelines(rows)
print(f"Kept {len(rows)} judgment rows (removed Qwen entries)")
PY

echo "=== Judgment ==="
printf '\n' | "$PYTHON" gen_judgment.py \
  --model-list Qwen3.6-27B Qwen3.6-35B-A3B \
  --judge-model google/gemma-4-31B \
  --openai-api-base "$API_BASE" \
  --openai-api-key "$API_KEY" \
  --parallel 4

echo "=== Results ==="
"$PYTHON" show_result.py \
  --judge-model google/gemma-4-31B \
  --model-list Qwen3.6-27B Qwen3.6-35B-A3B
