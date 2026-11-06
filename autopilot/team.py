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
  "fixed_scenes": [the full scenes array with ONLY the false claims rewritten to be true; same keys incl. "visual"; null if verdict is pass or reject],
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
more conversational and more exciting, keeping the facts identical, the same scene kinds and order, every "visual" object unchanged, total
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


def sound_check(text_model, listen_json, audio_path, script):
    """Sound Engineer: actually listens to the final mix and reports problems."""
    spoken = " ".join(s["voice"] for s in script["scenes"])
    prompt = f"""You are a professional sound engineer for short-form social videos. LISTEN to this audio carefully.
The voiceover should say exactly: "{spoken}"
Check and rate 1-10:
- voice_clarity: is every word clear and natural?
- script_match: does it say the script, with NO extra words (e.g. reading out instructions like "say this excitedly")?
- noise: any crackle, clicks, distortion, hiss or glitches? (10 = perfectly clean)
- music_balance: background music supports but never fights the voice?
- transitions: are the scene-change sound effects pleasant, not harsh or annoying?
- energy: does it sound exciting and fun to listen to?
Return JSON: {{"scores":{{"voice_clarity":0,"script_match":0,"noise":0,"music_balance":0,"transitions":0,"energy":0}},
"transcript":"what you actually heard","problems":["specific problems with timestamps"],"verdict":"pass" | "fix"}}"""
    r = listen_json(text_model, str(audio_path), prompt)
    sc = r.get("scores", {})
    low = {k: v for k, v in sc.items() if isinstance(v, (int, float)) and v < 7}
    verdict = "fix" if low or r.get("verdict") == "fix" else "pass"
    script["sound_check"] = {"verdict": verdict, "scores": sc, "problems": r.get("problems", [])[:6],
                             "heard": (r.get("transcript") or "")[:400]}
    print(f"sound engineer: {verdict} {sc} {r.get('problems', [])[:3]}")
    return verdict


def attention_director(text_model, generate_json, script):
    """Attention Director: plans a 'can't look away' beat map for every scene.

    Uses the same principles that hold even a toddler's attention (a change every ~1-2 seconds, faces,
    surprise, rhythm, bright contrast, sound cues tied to motion) but keeps the message for adults.
    """
    prompt = f"""You are the Attention Director of a viral short-video channel. Your job: a viewer must be unable to
look away for 30 seconds, the way a toddler can't stop watching a great cartoon. You control the edit, not the facts.

Principles you apply:
- Something visibly changes every 1-2 seconds (new word punch, zoom, visual step, mascot reaction).
- Emphasise the 1-3 most emotional or surprising words per scene (numbers, "free", "stop", the payoff word).
- The mascot "Tick" (a friendly stopwatch with a face) reacts: "happy", "wow" (mouth open) on surprises.
- Pattern interrupt in the first second; a curiosity tease mid-way; a satisfying payoff at the end.
- Sound cues: "pop" on emphasis, "ding" on the payoff.
- Never change facts. You MAY shorten or punch up a voice line by a few words if it drags (keep the meaning).

SCRIPT SCENES: {json.dumps(script['scenes'], ensure_ascii=False)}

Return JSON:
{{"scenes":[{{"emphasis":["word","word"],"mascot":"happy|wow","voice":"same or slightly punchier line"}}],
"retention_score":0,"biggest_risk":"where a viewer might swipe away and what you did about it"}}
(one entry per scene, same order)"""
    r = generate_json(text_model, prompt, temperature=0.6)
    plan = r.get("scenes") or []
    if len(plan) == len(script["scenes"]):
        for sc, a in zip(script["scenes"], plan):
            sc["attention"] = {"emphasis": [str(w) for w in (a.get("emphasis") or [])][:3],
                               "mascot": a.get("mascot", "happy")}
            v = (a.get("voice") or "").strip()
            if v and 0.6 <= len(v.split()) / max(1, len(sc["voice"].split())) <= 1.15:
                sc["voice"] = v
    script["attention_plan"] = {"retention_score": r.get("retention_score"), "biggest_risk": r.get("biggest_risk")}
    print(f"attention director: retention {r.get('retention_score')}/10, risk: {str(r.get('biggest_risk'))[:90]}")
    return script
