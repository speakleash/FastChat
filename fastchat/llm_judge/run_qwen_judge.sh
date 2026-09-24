#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PYTHON="../../.venv/bin/python3"
API_BASE="${PLGRID_API_BASE:-https://llmlab.plgrid.pl/api/v1}"
API_KEY="${PLGRID_API_KEY:?Set PLGRID_API_KEY}"
JUDGE_MODEL="Qwen/Qwen3.5-122B-A10B"

MODELS=(
  "Qwen3.6-35B-A3B"
  "Qwen3.6-27B"
  "Llama-3.3-70B-Instruct"
  "Bielik-11B-v3.0-Instruct"
  "Bielik-11B-v2.6-Instruct"
  "step72"
  "Llama-PLLuM-70B-chat-250801"
  "pllum-12b-nc-chat-250715"
)

OUTPUT="data/mt_bench/model_judgment/${JUDGE_MODEL}_single.jsonl"
if [[ -f "$OUTPUT" ]]; then
  echo "Output already exists: $OUTPUT"
  echo "Remove it first if you want a fresh run."
  exit 1
fi

echo "=== Judging all models with ${JUDGE_MODEL} ==="
"$PYTHON" gen_judgment.py \
  --model-list "${MODELS[@]}" \
  --judge-model "$JUDGE_MODEL" \
  --reference-model gpt-4 \
  --openai-api-base "$API_BASE" \
  --openai-api-key "$API_KEY" \
  --disable-thinking \
  --parallel 4 \
  --yes

echo ""
echo "=== Qwen judge results ==="
"$PYTHON" show_result.py \
  --judge-model "$JUDGE_MODEL" \
  --model-list "${MODELS[@]}"

echo ""
echo "=== Comparison: gemma vs qwen ==="
"$PYTHON" compare_judges.py \
  --judge-a google/gemma-4-31B \
  --judge-b "$JUDGE_MODEL" \
  --model-list "${MODELS[@]}"
