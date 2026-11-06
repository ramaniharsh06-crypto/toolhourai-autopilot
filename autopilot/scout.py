"""Trend Scout: researches the live web (Google Search via Gemini) once a week.

Finds what is rising RIGHT NOW in the AI-tools-for-small-business niche: new tools and features,
questions people are asking, short-video formats and hooks that are working for creators in this
space, and things to avoid. The planner and creative director read data/trends.json every day.
"""
import datetime, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TRENDS = DATA / "trends.json"


def is_stale(days=6):
    if not TRENDS.exists():
        return True
    t = json.loads(TRENDS.read_text()).get("researched_at", "2000-01-01")
    return (datetime.date.today() - datetime.date.fromisoformat(t[:10])).days >= days


def run(text_model, search_json, force=False):
    if not force and not is_stale():
        print("scout: trends are fresh, skipping research")
        return json.loads(TRENDS.read_text())
    today = datetime.date.today().isoformat()
    prompt = f"""Today is {today}. You are a senior market researcher and trend scout for a faceless
short-video channel that teaches small business owners free/cheap AI tools (Reels + YouTube Shorts).
Search the web for what happened in the LAST 14 DAYS and report:

1. rising_tools: 6 AI tools or new features that launched or got popular recently and are useful to
   small business owners (have a free plan or free tier). For each: name, official homepage url, what
   it does in one line, why it is trending now, the source url you found it on.
2. hot_questions: 6 questions small business owners are actively asking about AI right now
   (forums, Reddit, search trends).
3. winning_formats: 5 short-video formats/hook patterns that are performing well for AI-tool
   creators right now, each with a one-line example hook.
4. avoid: 4 things to avoid right now (oversaturated topics, controversies, platform rule changes,
   tools with recent outages, pricing changes or bad press).
5. one_big_opportunity: one sentence on the single best content opportunity this week.

Only include things you actually found in search results. Never invent tools, numbers or sources.

JSON shape:
{{"rising_tools":[{{"name":"","url":"https://","what":"","why_now":"","source":""}}],
"hot_questions":[""],"winning_formats":[{{"format":"","example_hook":""}}],"avoid":[""],
"one_big_opportunity":""}}"""
    data, sources = search_json(text_model, prompt)
    data["researched_at"] = today
    data["sources"] = sources[:20]
    TRENDS.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    md = [f"# Trend Scout report: {today}", "", f"**Biggest opportunity:** {data.get('one_big_opportunity','')}", "",
          "## Rising tools"]
    md += [f"- **{t.get('name')}** ({t.get('url')}): {t.get('what')} *Why now:* {t.get('why_now')} [source]({t.get('source')})"
           for t in data.get("rising_tools", [])]
    md += ["", "## What small business owners are asking"] + [f"- {q}" for q in data.get("hot_questions", [])]
    md += ["", "## Formats working right now"] + [f"- **{f.get('format')}**: \"{f.get('example_hook')}\""
                                                  for f in data.get("winning_formats", [])]
    md += ["", "## Avoid this week"] + [f"- {a}" for a in data.get("avoid", [])]
    (DATA / "SCOUT.md").write_text("\n".join(md) + "\n")
    print(f"scout: {len(data.get('rising_tools', []))} rising tools, {len(sources)} sources")
    return data


def brief():
    """Short text the planner/creative director can read."""
    if not TRENDS.exists():
        return "no scout research yet"
    d = json.loads(TRENDS.read_text())
    tools = [f"{t.get('name')} ({t.get('url')}): {t.get('why_now')}" for t in d.get("rising_tools", [])]
    return json.dumps({"rising_tools": tools, "hot_questions": d.get("hot_questions", []),
                       "winning_formats": d.get("winning_formats", []), "avoid": d.get("avoid", []),
                       "opportunity": d.get("one_big_opportunity")}, ensure_ascii=False)
