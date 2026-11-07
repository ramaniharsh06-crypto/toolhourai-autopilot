"""Safety Governor: keeps the channels from ever getting flagged, limited or banned.

Platforms punish: posting too much (especially from new accounts), duplicate/unoriginal content, spammy captions
and hashtags, undisclosed AI or ads, misleading claims, and repeated failed uploads. This module enforces limits on
all of those and can PAUSE posting automatically. It overrides every other agent, including the CEO and Strategist.
"""
import datetime, difflib, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PAUSE = DATA / "PAUSED.json"

MAX_PER_DAY = 2               # absolute cap per platform account, whatever the Strategist wants
WARMUP_DAYS = 14              # new accounts: 1 post/day for the first two weeks
MAX_HASHTAGS = 5
MIN_HOURS_BETWEEN_RUNS = 18


def paused():
    if PAUSE.exists():
        p = json.loads(PAUSE.read_text())
        until = p.get("until")
        if until and datetime.date.today() >= datetime.date.fromisoformat(until):
            PAUSE.unlink(); return None
        return p
    return None


def pause(reason, days=3):
    until = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
    PAUSE.write_text(json.dumps({"reason": reason, "since": datetime.date.today().isoformat(), "until": until}, indent=1))
    (DATA / "ALERTS.md").write_text((DATA / "ALERTS.md").read_text() if (DATA / "ALERTS.md").exists() else "")
    with open(DATA / "ALERTS.md", "a") as f:
        f.write(f"- Posting PAUSED until {until}: {reason}\n")
    print("governor: PAUSED posting:", reason)


def videos_allowed(cfg, hist):
    first = next((h.get("created", "")[:10] for h in hist if h.get("buffer_posts")), None)
    age = (datetime.date.today() - datetime.date.fromisoformat(first)).days if first else 0
    want = int(cfg.get("videos_per_run", 1))
    cap = 1 if age < WARMUP_DAYS else MAX_PER_DAY
    today = datetime.date.today().isoformat()
    already = sum(1 for h in hist if h.get("buffer_posts") and h.get("created", "")[:10] == today)
    n = max(0, min(want, cap) - already)
    print(f"governor: account age {age}d, allowed {n} video(s) now (cap {cap}/day, {already} already today)")
    return n


def clean_caption(caption):
    """Max 5 hashtags, no repeated hashtags, no link spam, always the AI + not-sponsored disclosure."""
    tags = list(dict.fromkeys(re.findall(r"#\w+", caption)))[:MAX_HASHTAGS]
    body = re.sub(r"#\w+", "", caption)
    body = re.sub(r"https?://\S+", "", body)          # links in Reels captions look spammy and aren't clickable
    body = re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", body)).strip()
    if "ai voiceover" not in body.lower():
        body += "\n\nAI voiceover · not sponsored"
    return body + ("\n\n" + " ".join(tags) if tags else "")


def too_similar(script, hist):
    """Reject near-duplicates of recent videos (platforms treat repeated content as spam)."""
    me = " ".join(s.get("voice", "") for s in script["scenes"]).lower()
    for h in hist[-60:]:
        other = " ".join(s.get("voice", "") for s in h.get("scenes", [])).lower()
        if other and difflib.SequenceMatcher(None, me, other).ratio() > 0.6:
            return h.get("id")
    return None


def gate(script):
    """Return (auto_publish_ok, reasons). Anything not clearly safe goes to Buffer as a draft instead."""
    reasons = []
    fc = (script.get("fact_check") or {}).get("verdict")
    if fc not in ("pass", "fixable"):
        reasons.append(f"fact-check {fc or 'missing'}")
    snd = script.get("sound_check") or {}
    if snd.get("verdict") != "pass":
        reasons.append(f"sound check {snd.get('verdict', 'missing')}")
    ed = (script.get("editor") or {}).get("scores") or {}
    if ed and min(v for v in ed.values() if isinstance(v, (int, float))) < 6:
        reasons.append("editor score below 6")
    return (not reasons), reasons


def review_health(hist):
    """Auto-pause on danger signals: repeated failed uploads, or several recent posts with ~zero views (possible limit)."""
    week = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    failed = sum(1 for h in hist if h.get("created", "")[:10] >= week
                 for st in (h.get("status") or {}).values() if str(st).lower() in ("error", "failed"))
    if failed >= 2:
        pause(f"{failed} posts failed to publish this week; checking before posting more", days=2)
        return
    old_enough = [h for h in hist if h.get("metrics") and h.get("created", "")[:10] <=
                  (datetime.date.today() - datetime.timedelta(days=2)).isoformat()][-3:]
    if len(old_enough) == 3:
        def views(h):
            return max([float(v) for m in h["metrics"].values() for k, v in m.items()
                        if any(x in k.lower() for x in ("view", "impression", "reach"))] or [0])
        if all(views(h) < 5 for h in old_enough):
            pause("last 3 posts got almost no views (possible reach limit); resting the account", days=3)
