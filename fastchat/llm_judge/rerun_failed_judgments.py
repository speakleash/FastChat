"""Re-run judgments that failed to parse (score == -1)."""

import argparse
import json
import os

from tqdm import tqdm

from fastchat.llm_judge.common import (
    Judge,
    MatchSingle,
    NEED_REF_CATS,
    load_judge_prompts,
    load_model_answers,
    load_questions,
    play_a_match_single,
)
from fastchat.llm_judge.gen_judgment import make_judge_single


PROMPT_TO_KEY = {
    "single-v1": ("default", False),
    "single-math-v1": ("math", False),
    "single-v1-multi-turn": ("default-mt", True),
    "single-math-v1-multi-turn": ("math-mt", True),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench-name", default="mt_bench")
    parser.add_argument("--judge-file", default="data/judge_prompts.jsonl")
    parser.add_argument("--judge-model", required=True)
    parser.add_argument("--judgment-file", required=True)
    parser.add_argument("--reference-model", default="gpt-4")
    parser.add_argument("--openai-api-base", default=None)
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument("--disable-thinking", action="store_true")
    parser.add_argument("--parallel", type=int, default=1)
    args = parser.parse_args()

    api_dict = None
    if args.openai_api_base:
        api_dict = {
            "api_base": args.openai_api_base,
            "api_key": args.openai_api_key or os.environ.get("OPENAI_API_KEY", "EMPTY"),
        }

    rows = [json.loads(line) for line in open(args.judgment_file)]
    failed = [r for r in rows if r.get("score", -1) == -1]
    if not failed:
        print("No failed judgments to rerun.")
        return

    print(f"Rerunning {len(failed)} failed judgments...")

    base = f"data/{args.bench_name}"
    questions = {q["question_id"]: q for q in load_questions(f"{base}/question.jsonl", None, None)}
    model_answers = load_model_answers(f"{base}/model_answer")
    ref_answers = load_model_answers(f"{base}/reference_answer")
    judge_prompts = load_judge_prompts(args.judge_file)
    judges = make_judge_single(
        args.judge_model,
        judge_prompts,
        api_dict=api_dict,
        disable_thinking=args.disable_thinking,
    )

    new_results = {}
    for item in tqdm(failed):
        qid = item["question_id"]
        model = item["model"]
        turn = item["turn"]
        prompt_name = item["judge"][1]
        judge_key, multi_turn = PROMPT_TO_KEY[prompt_name]
        judge = judges[judge_key]

        q = questions[qid]
        answer = model_answers[model][qid]
        ref = ref_answers[args.reference_model][qid] if q["category"] in NEED_REF_CATS else None

        match = MatchSingle(dict(q), model, answer, judge, ref_answer=ref, multi_turn=multi_turn)
        result = play_a_match_single(match, output_file=None)
        key = (model, qid, turn)
        new_results[key] = result
        print(
            f"  Q{qid} {model} turn{turn}: "
            f"{item['score']} -> {result['score']}"
        )

    updated = []
    replaced = 0
    still_failed = 0
    for row in rows:
        key = (row["model"], row["question_id"], row["turn"])
        if row.get("score", -1) == -1 and key in new_results:
            updated.append(new_results[key])
            replaced += 1
            if new_results[key]["score"] == -1:
                still_failed += 1
        else:
            updated.append(row)

    with open(args.judgment_file, "w") as fout:
        for row in updated:
            fout.write(json.dumps(row) + "\n")

    print(f"Replaced {replaced} rows. Still failed: {still_failed}")


if __name__ == "__main__":
    main()
