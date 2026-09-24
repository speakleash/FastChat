"""Generate per-model HTML reports with answers and judge scores."""

import argparse
import html
import json
import os
from collections import defaultdict

CATEGORY_ORDER = [
    "writing",
    "roleplay",
    "reasoning",
    "math",
    "coding",
    "extraction",
    "stem",
    "humanities",
]

CSS = """
:root {
  --bg: #f8f9fb;
  --card: #fff;
  --border: #e2e6ee;
  --text: #1a1d26;
  --muted: #5c6478;
  --accent: #2563eb;
  --score-high: #15803d;
  --score-mid: #b45309;
  --score-low: #b91c1c;
  --error: #fef2f2;
}
* { box-sizing: border-box; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  margin: 0;
  line-height: 1.55;
}
header {
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 1.25rem 2rem;
  position: sticky;
  top: 0;
  z-index: 10;
}
header h1 { margin: 0 0 .25rem; font-size: 1.5rem; }
header .meta { color: var(--muted); font-size: .9rem; }
nav { margin-top: .75rem; display: flex; flex-wrap: wrap; gap: .5rem; }
nav a {
  color: var(--accent);
  text-decoration: none;
  padding: .25rem .6rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  font-size: .85rem;
}
nav a:hover { background: #eef2ff; }
nav a.active { background: var(--accent); color: #fff; border-color: var(--accent); }
main { max-width: 960px; margin: 0 auto; padding: 1.5rem 2rem 3rem; }
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.stat {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: .75rem 1rem;
  min-width: 120px;
}
.stat .label { font-size: .75rem; color: var(--muted); text-transform: uppercase; }
.stat .value { font-size: 1.4rem; font-weight: 700; }
.filters { margin-bottom: 1.25rem; display: flex; flex-wrap: wrap; gap: .4rem; }
.filters button {
  border: 1px solid var(--border);
  background: var(--card);
  border-radius: 999px;
  padding: .3rem .75rem;
  cursor: pointer;
  font-size: .82rem;
}
.filters button.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.task {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 1.25rem;
  overflow: hidden;
}
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .85rem 1.1rem;
  background: #f1f4f9;
  border-bottom: 1px solid var(--border);
  gap: .75rem;
  flex-wrap: wrap;
}
.task-header .id { font-weight: 700; }
.badge {
  display: inline-block;
  padding: .15rem .55rem;
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 600;
  background: #e8ecf4;
  color: var(--muted);
  text-transform: capitalize;
}
.turn { padding: 1rem 1.1rem; border-bottom: 1px solid var(--border); }
.turn:last-child { border-bottom: none; }
.turn-title {
  font-weight: 700;
  font-size: .85rem;
  color: var(--muted);
  margin-bottom: .5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: .5rem;
}
.score {
  font-weight: 800;
  font-size: 1rem;
  padding: .15rem .55rem;
  border-radius: 6px;
  white-space: nowrap;
}
.score-high { background: #dcfce7; color: var(--score-high); }
.score-mid { background: #fef3c7; color: var(--score-mid); }
.score-low { background: #fee2e2; color: var(--score-low); }
.score-missing { background: #f3f4f6; color: var(--muted); }
.label-block {
  font-size: .72rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--muted);
  margin: .6rem 0 .25rem;
}
.content {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: .92rem;
  background: #fafbfc;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: .75rem .9rem;
}
.content.error { background: var(--error); border-color: #fecaca; }
.judgment {
  margin-top: .6rem;
  font-size: .88rem;
  color: #374151;
  background: #f9fafb;
  border-left: 3px solid var(--accent);
  padding: .6rem .8rem;
  white-space: pre-wrap;
}
.index-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.index-table th, .index-table td {
  padding: .65rem .9rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
.index-table th { background: #f1f4f9; font-size: .8rem; text-transform: uppercase; }
.index-table tr:last-child td { border-bottom: none; }
.index-table a { color: var(--accent); text-decoration: none; font-weight: 600; }
"""


def score_class(score):
    if score is None:
        return "score-missing"
    if score >= 8:
        return "score-high"
    if score >= 5:
        return "score-mid"
    return "score-low"


def esc(text):
    return html.escape(text or "")


def load_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_judgments(path):
    by_key = {}
    for row in load_jsonl(path):
        if row.get("score", -1) == -1:
            continue
        key = (row["model"], row["question_id"], row["turn"])
        by_key[key] = row
    return by_key


def render_turn_block(turn_num, question_text, answer_text, judgment_row):
    if judgment_row:
        score = judgment_row["score"]
        score_html = (
            f'<span class="score {score_class(score)}">{score}/10</span>'
        )
        judgment_text = judgment_row.get("judgment", "")
    else:
        score_html = '<span class="score score-missing">—</span>'
        judgment_text = ""

    is_error = answer_text and "$ERROR$" in answer_text
    content_cls = "content error" if is_error else "content"

    return f"""
<div class="turn">
  <div class="turn-title">
    <span>Turn {turn_num}</span>
    {score_html}
  </div>
  <div class="label-block">Question</div>
  <div class="content">{esc(question_text)}</div>
  <div class="label-block">Model response</div>
  <div class="{content_cls}">{esc(answer_text.strip() if answer_text else "(empty)")}</div>
  {f'<div class="label-block">Judge ({esc(judgment_row["judge"][0])})</div><div class="judgment">{esc(judgment_text)}</div>' if judgment_text else ''}
</div>"""


def render_task(question, answer_row, judgments, model_id):
    qid = question["question_id"]
    category = question["category"]
    turns = question["turns"]
    answer_turns = answer_row["choices"][0]["turns"]

    blocks = []
    for i, q_text in enumerate(turns):
        turn_num = i + 1
        ans_text = answer_turns[i] if i < len(answer_turns) else ""
        j_row = judgments.get((model_id, qid, turn_num))
        blocks.append(render_turn_block(turn_num, q_text, ans_text, j_row))

    scores = [
        judgments.get((model_id, qid, t + 1), {}).get("score")
        for t in range(len(turns))
    ]
    valid = [s for s in scores if s is not None]
    avg = f"{sum(valid) / len(valid):.1f}" if valid else "—"

    return f"""
<article class="task" data-category="{esc(category)}">
  <div class="task-header">
    <span class="id">Q{qid}</span>
    <span class="badge">{esc(category)}</span>
    <span class="badge">avg {avg}</span>
  </div>
  {''.join(blocks)}
</article>"""


def render_model_page(model_id, questions, answers, judgments, judge_model, all_models):
    model_answers = answers.get(model_id, {})
    scores = [
        row["score"]
        for (m, _q, _t), row in judgments.items()
        if m == model_id
    ]
    avg_score = sum(scores) / len(scores) if scores else 0

    cat_scores = defaultdict(list)
    qid_to_cat = {q["question_id"]: q["category"] for q in questions}
    for (m, qid, _t), row in judgments.items():
        if m == model_id:
            cat_scores[qid_to_cat.get(qid, "?")].append(row["score"])
    cat_avgs = {
        c: sum(v) / len(v) for c, v in cat_scores.items() if v
    }

    nav_links = []
    for m in all_models:
        cls = "active" if m == model_id else ""
        nav_links.append(f'<a class="{cls}" href="{esc(m)}.html">{esc(m)}</a>')

    filter_buttons = ['<button class="active" data-cat="all">All</button>']
    for cat in CATEGORY_ORDER:
        if cat in cat_avgs:
            filter_buttons.append(
                f'<button data-cat="{esc(cat)}">{esc(cat)} ({cat_avgs[cat]:.1f})</button>'
            )

    tasks = []
    for q in sorted(questions, key=lambda x: (CATEGORY_ORDER.index(x["category"]) if x["category"] in CATEGORY_ORDER else 99, x["question_id"])):
        qid = q["question_id"]
        if qid not in model_answers:
            continue
        tasks.append(render_task(q, model_answers[qid], judgments, model_id))

    cat_stat_html = "".join(
        f'<div class="stat"><div class="label">{esc(c)}</div>'
        f'<div class="value">{cat_avgs[c]:.2f}</div></div>'
        for c in CATEGORY_ORDER
        if c in cat_avgs
    )

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(model_id)} — MT-Bench Report</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>{esc(model_id)}</h1>
  <div class="meta">Judge: {esc(judge_model)} · {len(scores)} scored turns · avg {avg_score:.2f}</div>
  <nav>
    <a href="index.html">Index</a>
    {''.join(nav_links)}
  </nav>
</header>
<main>
  <div class="summary">
    <div class="stat"><div class="label">Overall</div><div class="value">{avg_score:.2f}</div></div>
    {cat_stat_html}
  </div>
  <div class="filters">{''.join(filter_buttons)}</div>
  {''.join(tasks)}
</main>
<script>
document.querySelectorAll('.filters button').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const cat = btn.dataset.cat;
    document.querySelectorAll('.task').forEach(task => {{
      task.style.display = (cat === 'all' || task.dataset.category === cat) ? '' : 'none';
    }});
  }});
}});
</script>
</body>
</html>"""


def render_index(models, judgments, questions, judge_model):
    qid_to_cat = {q["question_id"]: q["category"] for q in questions}
    rows = []
    for model_id in models:
        scores = [
            row["score"]
            for (m, _q, _t), row in judgments.items()
            if m == model_id
        ]
        avg = sum(scores) / len(scores) if scores else 0
        cat_scores = defaultdict(list)
        for (m, qid, _t), row in judgments.items():
            if m == model_id:
                cat_scores[qid_to_cat.get(qid, "?")].append(row["score"])
        cat_str = ", ".join(
            f"{c}: {sum(cat_scores[c]) / len(cat_scores[c]):.1f}"
            for c in CATEGORY_ORDER
            if c in cat_scores and cat_scores[c]
        )
        rows.append((avg, model_id, len(scores), cat_str))

    rows.sort(key=lambda x: -x[0])
    table_rows = "".join(
        f"<tr><td>{i+1}</td><td><a href='{esc(m)}.html'>{esc(m)}</a></td>"
        f"<td><strong>{avg:.2f}</strong></td><td>{n}</td>"
        f"<td style='font-size:.82rem;color:#5c6478'>{esc(cat_str)}</td></tr>"
        for i, (avg, m, n, cat_str) in enumerate(rows)
    )

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MT-Bench Reports</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>Polish MT-Bench — Model Reports</h1>
  <div class="meta">Judge: {esc(judge_model)} · {len(models)} models</div>
</header>
<main>
  <table class="index-table">
    <thead><tr><th>#</th><th>Model</th><th>Avg</th><th>Turns</th><th>Categories</th></tr></thead>
    <tbody>{table_rows}</tbody>
  </table>
</main>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench-name", default="mt_bench")
    parser.add_argument("--judge-model", default="google/gemma-4-31B")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--model-list", nargs="+", default=None)
    args = parser.parse_args()

    base = f"data/{args.bench_name}"
    output_dir = args.output_dir or f"{base}/html_reports"
    os.makedirs(output_dir, exist_ok=True)

    questions = load_jsonl(f"{base}/question.jsonl")
    judgment_file = f"{base}/model_judgment/{args.judge_model}_single.jsonl"
    judgments = load_judgments(judgment_file)

    answer_dir = f"{base}/model_answer"
    judged_models = {m for (m, _q, _t) in judgments}
    models = sorted(
        f[:-6]
        for f in os.listdir(answer_dir)
        if f.endswith(".jsonl") and f[:-6] in judged_models
    )
    if args.model_list:
        models = [m for m in models if m in args.model_list]

    answers = {}
    for model_id in models:
        answers[model_id] = {
            row["question_id"]: row
            for row in load_jsonl(os.path.join(answer_dir, f"{model_id}.jsonl"))
        }

    for fname in os.listdir(output_dir):
        if fname.endswith(".html") and fname != "index.html":
            model_name = fname[:-5]
            if model_name not in models:
                os.remove(os.path.join(output_dir, fname))

    for model_id in models:
        path = os.path.join(output_dir, f"{model_id}.html")
        html_content = render_model_page(
            model_id, questions, answers, judgments, args.judge_model, models
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Wrote {path}")

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(render_index(models, judgments, questions, args.judge_model))
    print(f"Wrote {index_path}")


if __name__ == "__main__":
    main()
