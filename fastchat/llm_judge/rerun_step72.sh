#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="../../.venv/bin/python3"

echo "=== Regenerating step72 answers ==="
rm -f data/mt_bench/model_answer/step72.jsonl
"$PYTHON" gen_api_answer.py \
  --model step72 \
  --answer-file data/mt_bench/model_answer/step72.jsonl \
  --openai-api-base http://localhost:8000/v1 \
  --openai-api-key EMPTY \
  --parallel 1 \
  --max-tokens 2048

echo "=== Checking for errors ==="
"$PYTHON" - <<'PY'
import json, sys
errors = nulls = 0
total = 0
for line in open("data/mt_bench/model_answer/step72.jsonl"):
    for t in json.loads(line)["choices"][0]["turns"]:
        total += 1
        if t is None:
            nulls += 1
        elif t == "$ERROR$":
            errors += 1
print(f"errors={errors} nulls={nulls} total_turns={total}")
if errors or nulls:
    sys.exit(1)
PY

echo "=== Removing old step72 judgments ==="
"$PYTHON" - <<'PY'
import json
path = "data/mt_bench/model_judgment/google/gemma-4-31B_single.jsonl"
rows = [l for l in open(path) if json.loads(l).get("model") != "step72"]
with open(path, "w") as f:
    f.writelines(rows)
print(f"kept {len(rows)} judgment rows")
PY

echo "=== Judging step72 ==="
PLGRID_API_BASE="${PLGRID_API_BASE:-https://llmlab.plgrid.pl/api/v1}"
PLGRID_API_KEY="${PLGRID_API_KEY:?Set PLGRID_API_KEY}"
printf '\n' | "$PYTHON" gen_judgment.py \
  --model-list step72 \
  --judge-model google/gemma-4-31B \
  --openai-api-base "$PLGRID_API_BASE" \
  --openai-api-key "$PLGRID_API_KEY" \
  --parallel 4

echo "=== Results ==="
"$PYTHON" show_result.py \
  --judge-model google/gemma-4-31B \
  --model-list step72
