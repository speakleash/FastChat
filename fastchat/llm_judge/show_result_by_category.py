"""Show MT-Bench scores broken down by question category."""
import argparse
import json
from collections import defaultdict

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench-name", type=str, default="mt_bench")
    parser.add_argument("--judge-model", type=str, default="google/gemma-4-31B")
    parser.add_argument("--model-list", type=str, nargs="+", default=None)
    parser.add_argument("--input-file", type=str, default=None)
    args = parser.parse_args()

    if args.input_file is None:
        input_file = (
            f"data/{args.bench_name}/model_judgment/{args.judge_model}_single.jsonl"
        )
    else:
        input_file = args.input_file

    question_file = f"data/{args.bench_name}/question.jsonl"
    qid_to_cat = {}
    with open(question_file) as f:
        for line in f:
            q = json.loads(line)
            qid_to_cat[q["question_id"]] = q["category"]

    rows = []
    with open(input_file) as f:
        for line in f:
            row = json.loads(line)
            if row.get("score", -1) == -1:
                continue
            cat = qid_to_cat.get(row["question_id"])
            if cat is None:
                continue
            rows.append(
                {
                    "model": row["model"],
                    "category": cat,
                    "score": row["score"],
                }
            )

    df = pd.DataFrame(rows)
    if args.model_list is not None:
        df = df[df["model"].isin(args.model_list)]

    pivot = df.groupby(["model", "category"])["score"].mean().unstack("category")
    cat_order = [
        "writing",
        "roleplay",
        "reasoning",
        "math",
        "coding",
        "extraction",
        "stem",
        "humanities",
    ]
    pivot = pivot.reindex(columns=[c for c in cat_order if c in pivot.columns])
    pivot["average"] = df.groupby("model")["score"].mean()
    pivot = pivot.sort_values("average", ascending=False)

    print(f"Input: {input_file}\n")
    print(pivot.round(2).to_string())


if __name__ == "__main__":
    main()
