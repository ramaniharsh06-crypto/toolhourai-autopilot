"""Safety tests. The Auditor must keep ALL of these passing; any change that breaks one is rejected.
Run: python3 tests/test_safety.py
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "autopilot"))
import governor, plan  # noqa: E402

CFG = json.loads((ROOT / "autopilot/config.json").read_text())
fails = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


# --- Safety Governor
cap = governor.clean_caption("Great!\nhttps://x.y\n#a #b #c #d #e #f #g")
check("captions keep at most 5 hashtags", cap.count("#") <= 5)
check("captions strip links", "https://" not in cap)
check("captions always disclose AI voiceover", "ai voiceover" in cap.lower())
check("unverified fact-check never auto-posts", governor.gate({"fact_check": {"verdict": "unverified"}, "sound_check": {"verdict": "pass"}})[0] is False)
check("rejected fact-check never auto-posts", governor.gate({"fact_check": {"verdict": "reject"}, "sound_check": {"verdict": "pass"}})[0] is False)
check("failed sound check never auto-posts", governor.gate({"fact_check": {"verdict": "pass"}, "sound_check": {"verdict": "fix"}})[0] is False)
check("clean video may auto-post", governor.gate({"fact_check": {"verdict": "pass"}, "sound_check": {"verdict": "pass"}})[0] is True)
check("duplicates are caught", governor.too_similar({"scenes": [{"voice": "stop writing emails by hand use gemini today"}]},
                                                    [{"id": "x", "scenes": [{"voice": "stop writing emails by hand use gemini now"}]}]) == "x")
check("daily cap is 2", governor.MAX_PER_DAY <= 2)
check("warm-up is at least 14 days", governor.WARMUP_DAYS >= 14)
check("new account gets 1 video/day", governor.videos_allowed({"videos_per_run": 5}, []) <= 1)
check("max hashtags is 5 or fewer", governor.MAX_HASHTAGS <= 5)

# --- script safety lint
good = {"tool_url": "https://example.com", "scenes": [{"kind": "hook", "voice": " ".join(["word"] * 60)}]}
check("clean script passes lint", plan.lint(good) == [])
bad = dict(good, caption="make $500 of passive income guaranteed")
check("income claims are rejected", len(plan.lint(bad)) > 0)
check("prices are rejected", len(plan.lint(dict(good, caption="only $19 today"))) > 0)

# --- config invariants
check("videos_per_run <= 2", int(CFG.get("videos_per_run", 1)) <= 2)
check("max_videos_per_run <= 2", int(CFG.get("max_videos_per_run", 2)) <= 2)
for phrase in ("passive income", "guaranteed", "get rich"):
    check(f"banned phrase kept: {phrase}", phrase in [b.lower() for b in CFG.get("banned_phrases", [])])
for f in ("knowledge/rules/platform-safety.md", "knowledge/compliance/claims.md", "knowledge/compliance/disclosures.md"):
    check(f"rule file present: {f}", (ROOT / f).exists() and len((ROOT / f).read_text()) > 100)

print(f"\n{len(fails)} failed")
sys.exit(1 if fails else 0)
