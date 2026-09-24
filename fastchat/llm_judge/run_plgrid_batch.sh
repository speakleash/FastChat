#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PYTHON="../../.venv/bin/python3"
API_BASE="${PLGRID_API_BASE:-https://llmlab.plgrid.pl/api/v1}"
API_KEY="${PLGRID_API_KEY:?Set PLGRID_API_KEY}"

declare -A MODELS=(
  ["CYFRAGOVPL/pllum-12b-nc-chat-250715"]="pllum-12b-nc-chat-250715"
  ["CYFRAGOVPL/Llama-PLLuM-70B-chat-250801"]="Llama-PLLuM-70B-chat-250801"
  ["meta-llama/Llama-3.3-70B-Instruct"]="Llama-3.3-70B-Instruct"
  ["Qwen/Qwen3.6-27B"]="Qwen3.6-27B"
  ["Qwen/Qwen3.6-35B-A3B"]="Qwen3.6-35B-A3B"
  ["speakleash/Bielik-11B-v2.6-Instruct"]="Bielik-11B-v2.6-Instruct"
)

MODEL_IDS=()
for api_model in "${!MODELS[@]}"; do
  model_id="${MODELS[$api_model]}"
  MODEL_IDS+=("$model_id")
  answer_file="data/mt_bench/model_answer/${model_id}.jsonl"
  echo "=== Generating answers: $api_model -> $model_id ==="
  "$PYTHON" gen_api_answer.py \
    --model "$api_model" \
    --answer-file "$answer_file" \
    --openai-api-base "$API_BASE" \
    --openai-api-key "$API_KEY" \
    --parallel 8
done

echo "=== Running judgment (judge: google/gemma-4-31B) ==="
printf '\n' | "$PYTHON" gen_judgment.py \
  --model-list "${MODEL_IDS[@]}" \
  --judge-model google/gemma-4-31B \
  --openai-api-base "$API_BASE" \
  --openai-api-key "$API_KEY" \
  --parallel 4

echo "=== Results ==="
"$PYTHON" show_result.py \
  --judge-model google/gemma-4-31B \
  --model-list "${MODEL_IDS[@]}"

echo "=== Done ==="
