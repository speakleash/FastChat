#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PYTHON="../../.venv/bin/python3"
API_BASE="${PLGRID_API_BASE:-https://llmlab.plgrid.pl/api/v1}"
API_KEY="${PLGRID_API_KEY:?Set PLGRID_API_KEY}"
JUDGE_MODEL="Qwen/Qwen3.5-122B-A10B"
OUTPUT="data/mt_bench/model_judgment/${JUDGE_MODEL}_single.jsonl"

echo "=== Smoke test: ${JUDGE_MODEL} as judge (3 questions, step72) ==="
rm -f "$OUTPUT"

"$PYTHON" gen_judgment.py \
  --model-list step72 \
  --judge-model "$JUDGE_MODEL" \
  --reference-model gpt-4 \
  --openai-api-base "$API_BASE" \
  --openai-api-key "$API_KEY" \
  --disable-thinking \
  --first-n 3 \
  --parallel 1 \
  --yes

echo ""
echo "=== Test results ==="
"$PYTHON" - <<'PY'
import json, sys
path = "data/mt_bench/model_judgment/Qwen/Qwen3.5-122B-A10B_single.jsonl"
rows = [json.loads(l) for l in open(path)]
errors = sum(1 for r in rows if r["score"] == -1)
print(f"Judgments: {len(rows)}, parse errors: {errors}")
for r in rows:
    print(f"  Q{r['question_id']} turn{r['turn']}: score={r['score']}")
if errors:
    print("FAIL: judge could not parse ratings")
    sys.exit(1)
print("OK: judge works")
PY
