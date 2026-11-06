"""The learning loop: pull real post stats from Buffer, score what worked, steer the next videos."""
import json, pathlib, datetime, csv
from lib import buffer

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# how much each signal counts toward a video's score
WEIGHTS = {"views": 1, "impressions": 0.5, "reach": 0.5, "reactions": 8, "likes": 8,
           "comments": 20, "shares": 30, "saves": 30, "clicks": 40}


def score(metrics):
    s = 0.0
    for m in metrics or []:
        t = m["type"].lower()
        for k, w in WEIGHTS.items():
            if k in t and m.get("unit") != "percentage":
                s += w * float(m["value"])
    return s


def run():
    hist_f = DATA / "history.json"
    hist = json.loads(hist_f.read_text()) if hist_f.exists() else []
    rows = []
    for v in hist:
        total, seen = 0.0, False
        for svc, pid in (v.get("buffer_posts") or {}).items():
            try:
                p = buffer.post_metrics(pid)
            except Exception as e:
                print("metrics error", svc, e); continue
            v.setdefault("status", {})[svc] = p.get("status")
            if p.get("metrics"):
                seen = True
                v.setdefault("metrics", {})[svc] = {m["type"]: m["value"] for m in p["metrics"]}
                total += score(p["metrics"])
        if seen:
            v["score"] = round(total, 1)
            rows.append(v)
    hist_f.write_text(json.dumps(hist, indent=1))

    # aggregate -> weights.json (pillars, tools, hook styles), with a prior so one lucky post doesn't dominate
    agg = {"pillars": {}, "tools": {}, "hooks": {}, "formats": {}}
    overall = (sum(r["score"] for r in rows) / len(rows)) if rows else 0
    for r in rows:
        for bucket, key in (("pillars", r["pillar"]), ("tools", r["tool_name"]), ("hooks", r.get("hook_style", "?")),
                            ("formats", (r.get("format") or "?")[:60])):
            a = agg[bucket].setdefault(key, {"n": 0, "sum": 0.0})
            a["n"] += 1; a["sum"] += r["score"]
    for bucket in agg.values():
        for k, a in bucket.items():
            prior_n = 2
            a["score"] = round(((a["sum"] + prior_n * overall) / (a["n"] + prior_n)) / (overall or 1), 3)
    (DATA / "weights.json").write_text(json.dumps(agg, indent=1))

    # human-readable report
    rows.sort(key=lambda r: r["score"], reverse=True)
    lines = [f"# Tool Hour AI autopilot report — {datetime.date.today()}", "",
             f"Videos made: **{len(hist)}** · with stats: **{len(rows)}**", ""]
    if rows:
        lines += ["## Top videos", "| Score | Pillar | Tool | Topic |", "|---|---|---|---|"]
        lines += [f"| {r['score']} | {r['pillar']} | {r['tool_name']} | {r['topic']} |" for r in rows[:5]]
        lines += ["", "## What the next videos will lean toward"]
        for b in ("formats", "pillars", "hooks", "tools"):
            best = sorted(agg[b].items(), key=lambda kv: kv[1]["score"], reverse=True)[:3]
            lines.append(f"- **{b}**: " + ", ".join(f"{k} ({v['score']}×)" for k, v in best))
    else:
        lines.append("No stats yet: platforms report numbers a day or two after posting.")
    (DATA / "REPORT.md").write_text("\n".join(lines) + "\n")
    with open(DATA / "metrics.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "pillar", "tool", "hook", "score", "topic"])
        for r in rows:
            w.writerow([r["created"][:10], r["pillar"], r["tool_name"], r.get("hook_style"), r["score"], r["topic"]])
    print(f"learn: {len(rows)} videos scored")


if __name__ == "__main__":
    run()
