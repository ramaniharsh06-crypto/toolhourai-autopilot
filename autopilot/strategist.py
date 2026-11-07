"""Strategist: once a week, rewrites the channel's own playbook from real results.

What it may change (and only these):
  knowledge/content/hooks.md        - adds hooks that performed, drops ones that flopped
  knowledge/content/past-winners.md - why the winners won, in plain words
  knowledge/content/next-week-plan.md
  config.json -> creative_formats   - adds formats the Trend Scout found, retires formats that keep losing
  config.json -> defaults           - promotes an experiment winner (voice / music tempo / length) with clear evidence
  config.json -> videos_per_run     - 1 or 2 (never more: platforms punish mass posting)
It never touches code, safety rules, compliance, banned phrases, or approval settings.
Every change is written to data/STRATEGY_LOG.md and committed, so it can be read or undone.
"""
import datetime, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, KNOW = ROOT / "data", ROOT / "knowledge"
CFG_F = ROOT / "autopilot/config.json"


def due():
    f = DATA / "strategy_state.json"
    if not f.exists():
        return True
    last = json.loads(f.read_text()).get("last_run", "2000-01-01")
    every = json.loads(CFG_F.read_text()).get("strategist", {}).get("every_days", 7)
    return (datetime.date.today() - datetime.date.fromisoformat(last)).days >= every


def _promote_experiments(cfg, weights, log):
    st = cfg.get("strategist", {})
    min_n, lift = st.get("min_samples", 3), st.get("min_lift", 0.15)
    exps = weights.get("experiments", {})
    for dim in (cfg.get("experiments") or {}):
        cur = str(cfg["defaults"].get(dim))
        options = {k.split("=", 1)[1]: v for k, v in exps.items() if k.startswith(dim + "=")}
        base = options.get(cur)
        if not base or base["n"] < min_n:
            continue
        best_val, best = max(options.items(), key=lambda kv: kv[1]["score"])
        if best_val != cur and best["n"] >= min_n and best["score"] >= base["score"] * (1 + lift):
            new = int(best_val) if dim == "music_bpm" else best_val
            log.append(f"Experiment winner: {dim} {cur} → {new} ({best['score']:.2f}× vs {base['score']:.2f}×, {best['n']} videos)")
            cfg["defaults"][dim] = new
            if dim == "voice":
                cfg["voice_name"] = new


def _formats(cfg, weights, ideas, log):
    st = cfg.get("strategist", {})
    fw = weights.get("formats", {})
    keep = []
    for f in cfg["creative_formats"]:
        w = fw.get(f[:60])
        if w and w["n"] >= max(4, st.get("min_samples", 3) + 1) and w["score"] < 0.7 and len(cfg["creative_formats"]) > 6:
            log.append(f"Retired format (kept losing: {w['score']:.2f}× over {w['n']} videos): {f}")
            continue
        keep.append(f)
    for f in (ideas.get("add_formats") or [])[:2]:
        if isinstance(f, str) and 15 < len(f) < 160 and f not in keep and len(keep) < 12:
            keep.append(f); log.append(f"New format added: {f}")
    cfg["creative_formats"] = keep


def _posting_pace(cfg, hist, log):
    recent = [h for h in hist if "score" in h][-14:]
    if len(recent) < 10:
        return
    first, second = recent[:7], recent[7:]
    avg = lambda xs: sum(x["score"] for x in xs) / max(1, len(xs))
    growing = avg(second) > avg(first) * 1.2
    target = 2 if growing else 1
    target = min(target, cfg.get("max_videos_per_run", 2))
    if target != cfg.get("videos_per_run", 1):
        log.append(f"Posting pace: {cfg.get('videos_per_run', 1)} → {target} videos/day "
                   f"({'performance rising' if growing else 'performance flat, focus on quality'})")
        cfg["videos_per_run"] = target


def run(text_model, generate_json, force=False):
    if not force and not due():
        print("strategist: not due this week")
        return []
    cfg = json.loads(CFG_F.read_text())
    weights = json.loads((DATA / "weights.json").read_text()) if (DATA / "weights.json").exists() else {}
    hist = json.loads((DATA / "history.json").read_text()) if (DATA / "history.json").exists() else []
    scout = json.loads((DATA / "trends.json").read_text()) if (DATA / "trends.json").exists() else {}
    scored = sorted([h for h in hist if "score" in h], key=lambda h: h["score"], reverse=True)
    top = [{k: h.get(k) for k in ("format", "tool_name", "hook_style", "topic", "score")} | {"hook": h["scenes"][0]["voice"]}
           for h in scored[:6]]
    flop = [{k: h.get(k) for k in ("format", "tool_name", "topic", "score")} | {"hook": h["scenes"][0]["voice"]}
            for h in scored[-4:]] if len(scored) > 6 else []
    prompt = f"""You are the head of strategy for a fast-growing faceless short-video channel about AI tools for small
business owners. Using ONLY the data below, update the playbook. Be specific and practical.

TOP VIDEOS: {json.dumps(top, ensure_ascii=False)}
WORST VIDEOS: {json.dumps(flop, ensure_ascii=False)}
WEIGHTS: {json.dumps({k: v for k, v in weights.items() if k != 'tools'}, ensure_ascii=False)[:3000]}
TREND SCOUT: {json.dumps({k: scout.get(k) for k in ('winning_formats', 'hot_questions', 'avoid', 'one_big_opportunity')}, ensure_ascii=False)[:2500]}
CURRENT FORMATS: {json.dumps(cfg['creative_formats'], ensure_ascii=False)}
CURRENT HOOKS FILE: {(KNOW / 'content/hooks.md').read_text()[:1500]}

Return JSON:
{{"hooks":["8-12 hook lines in the channel voice; keep proven winners, add new ones modelled on them"],
"winner_notes":["4-6 bullet lessons: WHY winners won / losers lost, based on the data"],
"add_formats":["0-2 new formats worth testing, each one sentence like the current list"],
"next_week_plan":["5 concrete video ideas for next week"],
"summary":"2 sentences for the owner"}}
If there is not enough data yet, say so in summary and keep changes small."""
    ideas = generate_json(text_model, prompt, temperature=0.5)
    log = []
    if ideas.get("hooks"):
        (KNOW / "content/hooks.md").write_text("# Hooks that work\n(Updated weekly by the Strategist from real results.)\n\n" +
                                               "\n".join(f"- {h}" for h in ideas["hooks"][:12]) + "\n")
        log.append(f"hooks.md rewritten ({len(ideas['hooks'][:12])} hooks)")
    if ideas.get("winner_notes"):
        pw = KNOW / "content/past-winners.md"
        prev = pw.read_text() if pw.exists() else "# Past winners\n"
        pw.write_text(prev.rstrip() + f"\n\n## Lessons {datetime.date.today()}\n" +
                      "\n".join(f"- {n}" for n in ideas["winner_notes"][:6]) + "\n")
        log.append("past-winners.md: new lessons added")
    if ideas.get("next_week_plan"):
        (KNOW / "content/next-week-plan.md").write_text(f"# Next week's plan ({datetime.date.today()})\n\n" +
                                                         "\n".join(f"- {x}" for x in ideas["next_week_plan"][:7]) + "\n")
        log.append("next-week-plan.md updated")
    _formats(cfg, weights, ideas, log)
    _promote_experiments(cfg, weights, log)
    _posting_pace(cfg, hist, log)
    CFG_F.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    entry = f"## {datetime.date.today()}\n{ideas.get('summary', '')}\n" + "\n".join(f"- {l}" for l in log) + "\n\n"
    lf = DATA / "STRATEGY_LOG.md"
    lf.write_text(entry + (lf.read_text() if lf.exists() else ""))
    (DATA / "strategy_state.json").write_text(json.dumps({"last_run": datetime.date.today().isoformat()}))
    print("strategist:", "; ".join(log) or "no changes")
    return log
