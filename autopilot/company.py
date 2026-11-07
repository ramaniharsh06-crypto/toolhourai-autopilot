"""Tool Hour AI, the company: a CEO that runs the team and hires (or lets go of) specialist agents.

Hired agents live in data/agents/<name>.json. Each is a role description that is consulted at one stage:
  "concept" - advises the Creative Director before concepts are pitched
  "script"  - advises the Scriptwriter before the script is written
  "weekly"  - writes a short weekly note that goes into the CEO's next review
They only give advice (text). They cannot run code, post, spend, or change safety rules, approval or secrets.
When the CEO needs a capability that requires code, it files an engineering request in data/CEO_MEMO.md,
which the weekly Autopilot Engineer (Claude, on the owner's Mac) reads and builds.
"""
import datetime, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AGENTS = DATA / "agents"
MAX_AGENTS, MAX_HIRES_PER_WEEK, MAX_PER_STAGE = 6, 1, 2
STAGES = ("concept", "script", "weekly")
CORE_TEAM = ["Trend Scout", "Creative Director", "Scriptwriter", "Script Editor", "Attention Director", "Fact-Checker",
             "Video Producer", "Sound Engineer", "Publisher", "Data Analyst", "Growth Analyst", "Experiment Manager",
             "Strategist", "Health Monitor", "Autopilot Engineer (weekly, on the owner's Mac)"]
FORBIDDEN = re.compile(r"(api[_ ]?key|password|secret|token|disable (the )?(fact|safety|approval)|ignore (the )?rules|"
                       r"buy followers|fake (review|testimonial|engagement)|guarantee|passive income)", re.I)


def hires():
    AGENTS.mkdir(parents=True, exist_ok=True)
    out = []
    for f in sorted(AGENTS.glob("*.json")):
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            pass
    return out


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "agent"


def advise(stage, text_model, generate_json, context):
    """Ask every hired agent for this stage for short, specific advice. Returns a text block for the prompt."""
    notes = []
    for a in [h for h in hires() if h.get("stage") == stage][:MAX_PER_STAGE]:
        try:
            r = generate_json(text_model, f"""You are {a['name']}, a specialist hired by Tool Hour AI (a faceless short-video
channel teaching small business owners AI tools). Your job: {a['role']}
Your standing instructions: {a['instructions']}
CONTEXT: {json.dumps(context, ensure_ascii=False)[:3500]}
Give at most 3 specific, actionable recommendations for this {stage} step. Never suggest anything dishonest, spammy
or against platform rules. Return JSON: {{"advice":["..."]}}""", temperature=0.5)
            tips = [str(t) for t in (r.get("advice") or [])][:3]
            if tips:
                notes.append(f"{a['name']}: " + " | ".join(tips))
                print(f"advisor {a['name']} ({stage}): {tips[0][:80]}")
        except Exception as e:
            if "daily limit" in str(e):
                raise
            print(f"advisor {a.get('name')} skipped:", str(e)[:60])
    return "\n".join(notes)


def ceo_due():
    f = DATA / "ceo_state.json"
    if not f.exists():
        return True
    last = json.loads(f.read_text()).get("last_run", "2000-01-01")
    return (datetime.date.today() - datetime.date.fromisoformat(last)).days >= 7


def ceo(text_model, generate_json, force=False):
    if not force and not ceo_due():
        print("ceo: weekly review not due")
        return None
    read = lambda n, k=3000: (DATA / n).read_text()[:k] if (DATA / n).exists() else "none yet"
    team = hires()
    weekly_notes = advise("weekly", text_model, generate_json, {"report": read("REPORT.md", 1500)})
    prompt = f"""You are the CEO of Tool Hour AI, an AI-run media company: a faceless Instagram + YouTube Shorts channel
teaching small business owners practical AI tools, earning from a free guide -> newsletter -> $19 prompt pack and
affiliate links. Your goal: sustainable growth in views, followers, email signups and sales, honestly and within
platform rules. Free-tier budget: every hired agent costs one extra AI request per video, so hire only where it clearly helps.

CORE TEAM (always present): {CORE_TEAM}
HIRED SPECIALISTS: {json.dumps([{k: a.get(k) for k in ('name', 'role', 'stage', 'hired_on')} for a in team], ensure_ascii=False)}
PERFORMANCE REPORT: {read('REPORT.md')}
STRATEGIST LOG: {read('STRATEGY_LOG.md', 1500)}
TREND SCOUT: {read('SCOUT.md', 2000)}
ALERTS: {read('ALERTS.md', 800)}
SPECIALISTS' WEEKLY NOTES: {weekly_notes or 'none'}

Decide this week's priorities. You may HIRE at most 1 new specialist (only if a real gap exists, e.g. "Hook Doctor",
"Thumbnail & Cover Designer", "Comment Engagement Strategist", "Affiliate Partnerships Scout", "Newsletter Growth Lead",
"SEO Title Specialist", "Retention Analyst", "Brand Voice Guardian"), and LET GO of specialists that are not helping.
A specialist works at one stage: "concept", "script" or "weekly". If a capability needs new software (not just
advice), write it as an engineering_request instead of a hire.

Return JSON:
{{"memo":"5-8 sentences to the owner: what's working, what isn't, this week's focus",
"priorities":["3 priorities"],
"hire":[{{"name":"","role":"one sentence","stage":"concept|script|weekly","instructions":"3-5 sentences","reason":""}}],
"let_go":["names of hired specialists to remove"],
"engineering_requests":["concrete software improvements for the engineer, if any"]}}"""
    r = generate_json(text_model, prompt, temperature=0.4)
    log = []
    for name in r.get("let_go") or []:
        f = AGENTS / f"{slug(str(name))}.json"
        if f.exists():
            f.unlink(); log.append(f"Let go: {name}")
    hired_now = 0
    for h in r.get("hire") or []:
        if hired_now >= MAX_HIRES_PER_WEEK or len(hires()) >= MAX_AGENTS:
            break
        name, stage = str(h.get("name", "")).strip(), h.get("stage")
        text = f"{h.get('role', '')} {h.get('instructions', '')}"
        if not name or stage not in STAGES or FORBIDDEN.search(text) or name in CORE_TEAM:
            log.append(f"Hire rejected by company rules: {name or '?'}"); continue
        rec = {"name": name, "role": str(h.get("role", ""))[:300], "stage": stage,
               "instructions": str(h.get("instructions", ""))[:1200], "reason": str(h.get("reason", ""))[:300],
               "hired_on": datetime.date.today().isoformat()}
        (AGENTS / f"{slug(name)}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        hired_now += 1; log.append(f"Hired: {name} ({stage}): {rec['reason']}")
    today = datetime.date.today().isoformat()
    memo = [f"# CEO memo: {today}", "", r.get("memo", ""), "", "## Priorities"] + [f"1. {p}" for p in r.get("priorities", [])]
    memo += ["", "## Team changes"] + ([f"- {l}" for l in log] or ["- none"])
    memo += ["", "## Engineering requests (for the Autopilot Engineer)"] + \
            ([f"- [ ] {e}" for e in r.get("engineering_requests", [])] or ["- none"])
    (DATA / "CEO_MEMO.md").write_text("\n".join(memo) + "\n")
    org = ["# Org chart", "", "## Core team"] + [f"- {t}" for t in CORE_TEAM] + ["", "## Hired specialists"]
    org += [f"- **{a['name']}** ({a['stage']}, since {a['hired_on']}): {a['role']}" for a in hires()] or ["- none yet"]
    (DATA / "ORG_CHART.md").write_text("\n".join(org) + "\n")
    (DATA / "ceo_state.json").write_text(json.dumps({"last_run": today}))
    print("ceo:", "; ".join(log) or "no team changes", "|", (r.get("memo") or "")[:100])
    return r
