"""Writes the next video script with Gemini, steered by the learning loop (data/weights.json)."""
import json, random, re, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "autopilot/config.json").read_text())
CURRENT_LEN = (55, 75, "about 30 seconds")


def _read(p):
    f = ROOT / "knowledge" / p
    return f.read_text() if f.exists() else ""


def history():
    f = ROOT / "data/history.json"
    return json.loads(f.read_text()) if f.exists() else []


def weights():
    f = ROOT / "data/weights.json"
    return json.loads(f.read_text()) if f.exists() else {"pillars": {}, "tools": {}, "hooks": {}}


def choose_pillar(w):
    pillars = CFG["pillars"]
    recent = [h["pillar"] for h in history()[-2:]]
    options = [p for p in pillars if p not in recent] or pillars
    if random.random() < CFG["explore_rate"] or not w["pillars"]:
        return random.choice(options), "explore"
    scored = sorted(options, key=lambda p: w["pillars"].get(p, {"score": 1.0})["score"], reverse=True)
    return scored[0], "exploit"


def scout_brief():
    try:
        import scout
        return scout.brief()
    except Exception:
        return "no scout research yet"


def brainstorm(text_model, generate_json, pillar):
    """Creative director: 4 concepts in different formats, scored hard, best one wins."""
    h = history()
    recent = [f"{x.get('format','?')} / {x['tool_name']} / {x['topic']}" for x in h[-12:]]
    w = weights()
    best_formats = sorted(w.get("formats", {}).items(), key=lambda kv: kv[1]["score"], reverse=True)[:3]
    bf = ROOT / "data/blocked_sites.json"
    blocked = json.loads(bf.read_text()) if bf.exists() else []
    prompt = f"""You are the creative director of a fast-growing faceless short-video channel, "{CFG['brand']}",
teaching small business owners practical AI tools. Content pillar today: "{pillar}".

Pitch 4 DIFFERENT concepts. Each uses a different format from this list:
{json.dumps(CFG['creative_formats'], ensure_ascii=False, indent=1)}
Each concept must use one real, well-known AI tool with a free plan or free tier and a public homepage
(not on this blocked list: {blocked or 'none'}), and must not repeat these recent videos:
{recent or 'none yet'}
Formats that performed best so far (favour them, but keep variety): {[k for k,_ in best_formats] or 'no data yet'}

TREND SCOUT RESEARCH FROM THIS WEEK (live web; prefer rising tools and hot questions, respect "avoid"):
{scout_brief()}

Then judge every concept like a strict viral-video editor, 1-10 each:
stop_scroll (would a thumb stop in the first second?), curiosity (must I watch to the end?),
emotion (relief, surprise, laughter, "finally!"), clarity (instantly understandable), freshness (unlike recent videos).
Be harsh; average ideas get 5s.

Return ONLY JSON:
{{"concepts":[{{"format":"...","tool_name":"...","tool_url":"https://...","hook_line":"the first spoken sentence, max 10 words",
"story":"2 sentences: setup -> twist -> payoff","emotion":"...",
"scores":{{"stop_scroll":0,"curiosity":0,"emotion":0,"clarity":0,"freshness":0}}}}],
"winner_index":0,"why":"one sentence"}}"""
    r = generate_json(text_model, prompt, temperature=1.0)
    cs = r.get("concepts") or []
    if not cs:
        return None
    for c in cs:
        c["total"] = sum(int(v) for v in (c.get("scores") or {}).values())
    best = max(cs, key=lambda c: c["total"])
    print(f"creative director picked: {best.get('format','?')[:40]} | {best.get('tool_name')} | {best['total']}/50 | {best.get('hook_line')}")
    return best


def build_prompt(pillar, concept=None):
    h = history()
    used_tools = sorted({x["tool_name"] for x in h[-30:]})
    bf = ROOT / "data/blocked_sites.json"
    blocked = json.loads(bf.read_text()) if bf.exists() else []
    w = weights()
    best = sorted(w["tools"].items(), key=lambda kv: kv[1]["score"], reverse=True)[:5]
    best_hooks = sorted(w["hooks"].items(), key=lambda kv: kv[1]["score"], reverse=True)[:3]
    return f"""You write 28-32 second faceless short videos (Instagram Reels + YouTube Shorts) for the brand "{CFG['brand']}".
Audience: small business owners who are busy and a bit overwhelmed by AI.

BRAND VOICE:
{_read('voice/tone.md')}
NEVER SAY:
{_read('voice/never-say.md')}
PLATFORM SAFETY RULES (must follow):
{_read('rules/platform-safety.md')}
{_read('compliance/claims.md')}
HOOK IDEAS THAT WORK:
{_read('content/hooks.md')}

TODAY'S CONTENT PILLAR: "{pillar}"
{("THE APPROVED CONCEPT (write exactly this video): " + json.dumps(concept, ensure_ascii=False)) if concept else ""}
Pick ONE real, well-known AI tool that has a public website and a free plan or free tier
(examples: Gemini, ChatGPT, Claude, Perplexity, NotebookLM, Canva, CapCut, Gamma, Notion AI, Otter.ai, Grammarly, Descript, Zapier, Make, Tally, Google Sheets with Gemini).
Do NOT use any of these tools that were used recently: {used_tools or 'none yet'}.
Do NOT use tools whose website is on this list (their sites block screenshots): {blocked or 'none'}.
Tools that performed best so far (prefer similar ones, but do not repeat the exact tool): {[t for t,_ in best] or 'no data yet'}
Hooks that performed best: {[k for k,_ in best_hooks] or 'no data yet'}

ENERGY (write like the world's best salesman pitching to one person, this is what makes people watch to the end):
- Open with a pattern interrupt: "Wait.", "Stop.", "Okay, this is crazy.", or a sharp question that hits a real pain.
- Use contrast and stakes: the painful old way vs the effortless new way. Make them FEEL the time they're wasting.
- Tease the payoff ("and here's the crazy part...") so they need the ending. Deliver it big.
- Short sentences. Punchy verbs. Talk to "you". Genuine excitement, never fake hype or fake urgency.
- You may add ONE or TWO vocal bursts inside voice lines where natural: <gasp>, <laugh>, <chuckle>, <sigh>.
- The hook is a pattern interrupt in the first 2 seconds: a surprising claim, a "stop doing X", or a relatable frustration. Talk to "you".
- Sound like a real excited friend sharing a discovery: short punchy sentences, a little humour, one moment of "wait, what?".
- Build curiosity: the payoff (result) comes at the end, so viewers stay.
- Headlines are bold statements in plain words. NO emoji anywhere.

HARD RULES:
- Be factually safe: only describe stable, well-known features. NO prices, NO exact plan limits, NO income claims, NO made-up statistics.
- Say "free plan" only if the tool is widely known to have one; otherwise say "try it".
- One practical tip the viewer can do today, in plain English. No jargon.
- Voice lines must be short spoken sentences. Total spoken words {CURRENT_LEN[0]}-{CURRENT_LEN[1]} (the video must be {CURRENT_LEN[2]}).
- The tool_url must be the tool's real official homepage (https://...).

VISUAL LEARNING (very important):
{__import__("visuals").SCHEMA_HELP}

Return ONLY JSON with exactly this shape:
{{
  "pillar": "{pillar}",
  "tool_name": "...",
  "tool_url": "https://...",
  "topic": "one-line topic",
  "hook_style": "curiosity | stop-doing | numbers | myth | before-after",
  "format": "the format used, copied from the concept",
  "scenes": [
    {{"kind": "hook",   "headline": "max 6 words, no emoji", "sub": "max 8 words", "voice": "...", "visual": {{"type": "...", "data": {{}}}}}},
    {{"kind": "tool",   "headline": "max 5 words", "sub": "max 8 words", "voice": "..."}},
    {{"kind": "step",   "number": 1, "headline": "max 6 words", "body": "max 18 words", "voice": "...", "visual": {{"type": "...", "data": {{}}}}}},
    {{"kind": "step",   "number": 2, "headline": "max 6 words", "body": "max 18 words", "voice": "...", "visual": {{"type": "...", "data": {{}}}}}},
    {{"kind": "result", "headline": "max 6 words", "body": "max 18 words", "voice": "...", "visual": {{"type": "...", "data": {{}}}}}},
    {{"kind": "cta",    "voice": "Follow {CFG['brand']} for one AI shortcut every day."}}
  ],
  "caption": "Instagram caption, 60-110 words, line breaks, ends with a question, mention the free guide in bio",
  "youtube_title": "max 60 characters, no clickbait lies",
  "hashtags": ["5 relevant hashtags"]
}}"""


def lint(script):
    """Reject scripts that break the safety rules."""
    text = json.dumps(script).lower()
    problems = [p for p in CFG["banned_phrases"] if p.lower() in text]
    if re.search(r"[$₹€£]\s?\d", text):
        problems.append("contains a price/money amount")
    if not str(script.get("tool_url", "")).startswith("https://"):
        problems.append("tool_url is not https")
    words = sum(len(s.get("voice", "").split()) for s in script.get("scenes", []))
    lo, hi, _ = CURRENT_LEN
    if not lo - 8 <= words <= hi + 8:
        problems.append(f"voiceover length {words} words out of range")
    if [s.get("kind") for s in script.get("scenes", [])][:1] != ["hook"]:
        problems.append("first scene is not a hook")
    return problems


LENGTHS = {"short": (40, 55, "about 22 seconds"), "normal": (55, 75, "about 30 seconds")}


def choose_settings():
    """Experiment Manager: half the videos test ONE production variable against the current default."""
    d = dict(CFG.get("defaults") or {})
    d.setdefault("voice", CFG.get("voice_name", "Fenrir")); d.setdefault("music_bpm", 116); d.setdefault("length", "normal")
    exp = None
    if random.random() < CFG.get("experiment_rate", 0.5) and CFG.get("experiments"):
        dim = random.choice(list(CFG["experiments"]))
        opts = [o for o in CFG["experiments"][dim] if o != d.get(dim)]
        if opts:
            d[dim] = random.choice(opts); exp = {"dim": dim, "value": d[dim]}
    return d, exp


def make_script(text_model, generate_json, search_json=None):
    w = weights()
    pillar, mode = choose_pillar(w)
    settings, experiment = choose_settings()
    lo, hi, secs = LENGTHS.get(settings["length"], LENGTHS["normal"])
    global CURRENT_LEN
    CURRENT_LEN = (lo, hi, secs)
    print(f"settings: {settings}" + (f" | experiment: {experiment}" if experiment else " | no experiment"))
    try:
        concept = brainstorm(text_model, generate_json, pillar)
    except Exception as e:
        print("brainstorm skipped:", e); concept = None
    for attempt in range(3):
        s = generate_json(text_model, build_prompt(pillar, concept))
        problems = lint(s)
        if not problems:
            import team, time as _t
            try:
                team.edit(text_model, generate_json, s)
                _t.sleep(5)
            except Exception as e:
                print("editor skipped:", e)
            try:
                team.attention_director(text_model, generate_json, s)
                _t.sleep(5)
            except Exception as e:
                print("editor skipped:", e)
            if search_json:
                try:
                    if not team.fact_check(text_model, search_json, s):
                        problems = ["fact-checker rejected the script"]
                except Exception as e:
                    print("fact-checker could not run:", str(e)[:80], "-> marked UNVERIFIED (stays a draft for your review)")
                    s["fact_check"] = {"verdict": "unverified", "problems": [str(e)[:120]]}
            problems = problems or lint(s)
        if not problems:
            s["mode"] = mode
            s["settings"], s["experiment"] = settings, experiment
            if concept:
                s["concept"] = {k: concept.get(k) for k in ("format", "story", "emotion", "total")}
                s.setdefault("format", concept.get("format"))
            s["created"] = datetime.datetime.utcnow().isoformat() + "Z"
            tags = list(dict.fromkeys(CFG["hashtags_base"] + s.get("hashtags", [])))[:9]
            s["final_caption"] = (s["caption"].strip() + "\n\n🎁 Free guide: link in bio\n" +
                                  "AI voiceover · not sponsored\n\n" + " ".join(tags))
            return s
        print(f"script rejected ({attempt+1}/3): {problems}")
    raise RuntimeError(f"Could not produce a safe script: {problems}")
