"""Writes the next video script with Gemini, steered by the learning loop (data/weights.json)."""
import json, random, re, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "autopilot/config.json").read_text())


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


def build_prompt(pillar):
    h = history()
    used_tools = sorted({x["tool_name"] for x in h[-30:]})
    bf = ROOT / "data/blocked_sites.json"
    blocked = json.loads(bf.read_text()) if bf.exists() else []
    w = weights()
    best = sorted(w["tools"].items(), key=lambda kv: kv[1]["score"], reverse=True)[:5]
    best_hooks = sorted(w["hooks"].items(), key=lambda kv: kv[1]["score"], reverse=True)[:3]
    return f"""You write 25-35 second faceless short videos (Instagram Reels + YouTube Shorts) for the brand "{CFG['brand']}".
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
Pick ONE real, well-known AI tool that has a public website and a free plan or free tier
(examples: Gemini, ChatGPT, Claude, Perplexity, NotebookLM, Canva, CapCut, Gamma, Notion AI, Otter.ai, Grammarly, Descript, Zapier, Make, Tally, Google Sheets with Gemini).
Do NOT use any of these tools that were used recently: {used_tools or 'none yet'}.
Do NOT use tools whose website is on this list (their sites block screenshots): {blocked or 'none'}.
Tools that performed best so far (prefer similar ones, but do not repeat the exact tool): {[t for t,_ in best] or 'no data yet'}
Hooks that performed best: {[k for k,_ in best_hooks] or 'no data yet'}

HARD RULES:
- Be factually safe: only describe stable, well-known features. NO prices, NO exact plan limits, NO income claims, NO made-up statistics.
- Say "free plan" only if the tool is widely known to have one; otherwise say "try it".
- One practical tip the viewer can do today, in plain English. No jargon.
- Voice lines must be short spoken sentences. Total spoken words 60-85.
- The tool_url must be the tool's real official homepage (https://...).

Return ONLY JSON with exactly this shape:
{{
  "pillar": "{pillar}",
  "tool_name": "...",
  "tool_url": "https://...",
  "topic": "one-line topic",
  "hook_style": "curiosity | stop-doing | numbers | myth | before-after",
  "scenes": [
    {{"kind": "hook",   "headline": "max 7 words, can end with 1 emoji", "sub": "max 8 words", "voice": "..."}},
    {{"kind": "tool",   "headline": "max 5 words", "sub": "max 8 words", "voice": "..."}},
    {{"kind": "step",   "number": 1, "headline": "max 6 words", "body": "max 18 words", "voice": "..."}},
    {{"kind": "step",   "number": 2, "headline": "max 6 words", "body": "max 18 words", "voice": "..."}},
    {{"kind": "result", "headline": "max 6 words", "body": "max 18 words", "voice": "..."}},
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
    if not 45 <= words <= 110:
        problems.append(f"voiceover length {words} words out of range")
    if [s.get("kind") for s in script.get("scenes", [])][:1] != ["hook"]:
        problems.append("first scene is not a hook")
    return problems


def make_script(text_model, generate_json):
    w = weights()
    pillar, mode = choose_pillar(w)
    for attempt in range(3):
        s = generate_json(text_model, build_prompt(pillar))
        problems = lint(s)
        if not problems:
            s["mode"] = mode
            s["created"] = datetime.datetime.utcnow().isoformat() + "Z"
            tags = list(dict.fromkeys(CFG["hashtags_base"] + s.get("hashtags", [])))[:9]
            s["final_caption"] = (s["caption"].strip() + "\n\n🎁 Free guide: link in bio\n" +
                                  "AI voiceover · not sponsored\n\n" + " ".join(tags))
            return s
        print(f"script rejected ({attempt+1}/3): {problems}")
    raise RuntimeError(f"Could not produce a safe script: {problems}")
