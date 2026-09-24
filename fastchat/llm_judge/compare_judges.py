"""Compare MT-Bench scores between two judges."""

import argparse
import json
from collections import defaultdict

import pandas as pd


def load_scores(path):
    rows = []
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            if row.get("score", -1) == -1:
                continue
            rows.append(row)
    df = pd.DataFrame(rows)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench-name", default="mt_bench")
    parser.add_argument("--judge-a", default="google/gemma-4-31B")
    parser.add_argument("--judge-b", default="Qwen/Qwen3.5-122B-A10B")
    parser.add_argument("--file-a", default=None)
    parser.add_argument("--file-b", default=None)
    parser.add_argument("--model-list", nargs="+", default=None)
    args = parser.parse_args()

    base = f"data/{args.bench_name}"
    file_a = args.file_a or f"{base}/model_judgment/{args.judge_a}_single.jsonl"
    file_b = args.file_b or f"{base}/model_judgment/{args.judge_b}_single.jsonl"

    df_a = load_scores(file_a)
    df_b = load_scores(file_b)

    if args.model_list:
        df_a = df_a[df_a["model"].isin(args.model_list)]
        df_b = df_b[df_b["model"].isin(args.model_list)]

    qfile = f"{base}/question.jsonl"
    qid_to_cat = {}
    with open(qfile) as f:
        for line in f:
            q = json.loads(line)
            qid_to_cat[q["question_id"]] = q["category"]

    key_cols = ["model", "question_id", "turn"]
    merged = df_a[key_cols + ["score"]].merge(
        df_b[key_cols + ["score"]],
        on=key_cols,
        suffixes=("_a", "_b"),
        how="inner",
    )
    merged["delta"] = merged["score_b"] - merged["score_a"]
    merged["category"] = merged["question_id"].map(qid_to_cat)

    print(f"Judge A: {args.judge_a}")
    print(f"  file: {file_a}")
    print(f"Judge B: {args.judge_b}")
    print(f"  file: {file_b}")
    print(f"Matched judgments: {len(merged)}\n")

    avg_a = df_a.groupby("model")["score"].mean().rename("judge_a")
    avg_b = df_b.groupby("model")["score"].mean().rename("judge_b")
    summary = pd.concat([avg_a, avg_b], axis=1)
    summary["delta"] = summary["judge_b"] - summary["judge_a"]
    summary = summary.sort_values("judge_a", ascending=False)
    print("########## Overall average ##########")
    print(summary.round(3).to_string())
    print()

    corr = merged.groupby("model").apply(
        lambda g: g["score_a"].corr(g["score_b"]), include_groups=False
    )
    print("########## Per-model correlation ##########")
    print(corr.round(3).sort_values(ascending=False).to_string())
    print()

    cat_summary = (
        merged.groupby(["model", "category"])["delta"]
        .mean()
        .unstack("category")
    )
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
    cat_summary = cat_summary.reindex(columns=[c for c in cat_order if c in cat_summary.columns])
    print("########## Delta by category (B - A) ##########")
    print(cat_summary.round(2).to_string())
    print()

    outliers = merged.reindex(merged["delta"].abs().sort_values(ascending=False).index)
    print("########## Largest disagreements (top 10) ##########")
    top = outliers.head(10)[
        ["model", "question_id", "category", "turn", "score_a", "score_b", "delta"]
    ]
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()
