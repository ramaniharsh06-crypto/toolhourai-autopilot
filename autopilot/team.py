"""The rest of the team, each a focused Gemini pass:

- Fact-Checker: verifies every claim in the script against live Google Search results and fixes or rejects.
- Script Editor: scores the script for retention (hook, pacing, payoff, emotion) and rewrites weak lines.
- Growth Analyst: turns the weekly numbers into plain-English insights and next moves.
"""
import json


def fact_check(text_model, search_json, script):
    prompt = f"""You are a meticulous fact-checker for a short video about the AI tool "{script['tool_name']}"
({script['tool_url']}). Search the web and verify EVERY factual claim in this script: that the tool exists at that
url, that it has a free plan/free tier if the script implies it, and that each feature described really exists
today. Ignore opinions and jokes.

SCRIPT: {json.dumps(script['scenes'], ensure_ascii=False)}
CAPTION: {script.get('caption','')}

Return JSON:
{{"verdict":"pass" | "fixable" | "reject",
  "problems":["each false or unverifiable claim"],
  "fixed_scenes": [the full scenes array with ONLY the false claims rewritten to be true; same keys; null if verdict is pass or reject],
  "fixed_caption": "caption with false claims fixed, or null"}}"""
    r, sources = search_json(text_model, prompt, temperature=0.1)
    verdict = r.get("verdict", "pass")
    print(f"fact-checker: {verdict} {r.get('problems') or ''} ({len(sources)} sources)")
    if verdict == "fixable" and r.get("fixed_scenes"):
        script["scenes"] = r["fixed_scenes"]
        if r.get("fixed_caption"):
            script["caption"] = r["fixed_caption"]
    script["fact_check"] = {"verdict": verdict, "problems": r.get("problems", []), "sources": sources[:8]}
    return verdict != "reject"


def edit(text_model, generate_json, script):
    prompt = f"""You are the head editor of a viral short-video channel. Score this 25-35s script 1-10 on:
hook (first 2 seconds), pacing (no dead words), payoff (satisfying ending), emotion (fun, surprise, relief),
clarity. Then, if any score is below 8, rewrite ONLY the weak "voice"/"headline"/"body" lines to be punchier,
more conversational and more exciting, keeping the facts identical, the same scene kinds and order, total
spoken words 55-75, and no emoji, no prices, no income claims.

SCRIPT: {json.dumps(script['scenes'], ensure_ascii=False)}

Return JSON: {{"scores":{{"hook":0,"pacing":0,"payoff":0,"emotion":0,"clarity":0}},
"scenes":[the full scenes array, improved or unchanged], "note":"what you changed"}}"""
    r = generate_json(text_model, prompt, temperature=0.7)
    sc = r.get("scores", {})
    new = r.get("scenes")
    if new and len(new) == len(script["scenes"]) and [s.get("kind") for s in new] == [s.get("kind") for s in script["scenes"]]:
        script["scenes"] = new
    script["editor"] = {"scores": sc, "note": r.get("note", "")}
    print(f"editor: {sc} - {r.get('note','')[:90]}")
    return script


def analyst_insights(text_model, generate_json, rows, weights):
    if not rows:
        return ""
    slim = [{k: r.get(k) for k in ("created", "format", "pillar", "tool_name", "hook_style", "topic", "score", "metrics")}
            for r in rows[:40]]
    prompt = f"""You are a growth analyst for a faceless short-video channel. Here is real performance data
(score = weighted views/likes/comments/shares/saves). Write 5 short, specific, plain-English insights and
3 concrete next moves. Only claim what the data shows; say when a sample is too small.
DATA: {json.dumps(slim, ensure_ascii=False)}
WEIGHTS: {json.dumps(weights, ensure_ascii=False)}
Return JSON: {{"insights":["..."],"next_moves":["..."]}}"""
    r = generate_json(text_model, prompt, temperature=0.3)
    out = ["", "## Growth Analyst"] + [f"- {i}" for i in r.get("insights", [])]
    out += ["", "**Next moves:**"] + [f"1. {m}" for m in r.get("next_moves", [])]
    return "\n".join(out) + "\n"
