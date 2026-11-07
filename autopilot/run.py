"""Daily autopilot: learn -> plan -> render -> host -> schedule on Buffer.

Usage:
  python autopilot/run.py               # full run (needs GEMINI_API_KEY + BUFFER_API_KEY)
  python autopilot/run.py --no-publish  # make the video only, don't send to Buffer
"""
import json, os, pathlib, re, shutil, subprocess, sys, time, datetime, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lib import gemini, buffer          # noqa: E402
import plan, render, learn, scout, team, strategist  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "autopilot/config.json").read_text())
DATA, DOCS = ROOT / "data", ROOT / "docs"


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40]


def pages_base():
    repo = os.environ.get("GITHUB_REPOSITORY")          # owner/name, set by GitHub Actions
    if not repo:
        return None
    owner, name = repo.split("/")
    return f"https://{owner.lower()}.github.io/{name}"


def git_publish(paths, msg):
    subprocess.run(["git", "add", *paths], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
        subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=True)


def wait_public(url, minutes=10):
    for _ in range(minutes * 6):
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200 and "video" in r.headers.get("Content-Type", ""):
                    return True
        except Exception:
            pass
        time.sleep(10)
    return False


def prune_old_videos():
    keep = datetime.datetime.utcnow() - datetime.timedelta(days=CFG["keep_videos_days"])
    for f in (DOCS / "v").glob("*.mp4"):
        if datetime.datetime.utcfromtimestamp(f.stat().st_mtime) < keep:
            f.unlink()


START = time.time()


def minutes():
    return (time.time() - START) / 60


def main():
    publish = "--no-publish" not in sys.argv and CFG.get("publish_enabled", True)
    if not publish:
        print("test mode: making the video only (publish_enabled is false or --no-publish), nothing sent to Buffer")
    (DOCS / "v").mkdir(parents=True, exist_ok=True)
    (DOCS / ".nojekyll").touch()
    hist_f = DATA / "history.json"

    if publish and os.environ.get("BUFFER_API_KEY"):
        try:
            learn.run()
        except Exception as e:
            print("learning step skipped:", e)

    text_model, tts_model = gemini.pick_models(CFG["text_model"], CFG["tts_model"])
    print("models:", text_model, tts_model)

    try:                                        # Trend Scout: live web research, weekly
        if minutes() > 10:
            raise RuntimeError("time budget")
        scout.run(text_model, gemini.search_json, force="--scout" in sys.argv)
    except Exception as e:
        print("scout skipped:", e)
    time.sleep(20)                              # space out calls to stay inside the free per-minute quota
    try:                                        # Growth Analyst: insights on the weekly report
        h = json.loads(hist_f.read_text()) if hist_f.exists() else []
        rows = sorted([x for x in h if "score" in x], key=lambda x: x["score"], reverse=True)
        wf = DATA / "weights.json"
        extra = team.analyst_insights(text_model, gemini.generate_json, rows,
                                      json.loads(wf.read_text()) if wf.exists() else {})
        if extra and (DATA / "REPORT.md").exists():
            rep = DATA / "REPORT.md"
            rep.write_text(rep.read_text().split("\n## Growth Analyst")[0] + extra)
    except Exception as e:
        print("analyst skipped:", e)
    if publish:
        try:                                    # Strategist: weekly playbook rewrite from real results
            if strategist.run(text_model, gemini.generate_json, force="--strategy" in sys.argv):
                CFG.update(json.loads((ROOT / "autopilot/config.json").read_text()))
                plan.CFG.update(CFG)
        except gemini.DailyQuotaExhausted:
            raise
        except Exception as e:
            print("strategist skipped:", e)

    for _ in range(CFG["videos_per_run"]):
        script = plan.make_script(text_model, gemini.generate_json, gemini.search_json)
        day = datetime.date.today().isoformat()
        name = f"{day}-{slug(script['tool_name'] + '-' + script['topic'])}"
        work = ROOT / "build" / name
        mp4, secs = render.render(script, work, tts_model, gemini.tts_to_wav)
        try:                                    # Sound Engineer listens to the final mix
            time.sleep(15)
            team.sound_check(text_model, gemini.listen_json, work / "mix.m4a", script)
        except Exception as e:
            print("sound engineer could not listen:", str(e)[:90])
        final = DOCS / "v" / f"{name}.mp4"
        shutil.copy(mp4, final)
        script.update({"id": name, "seconds": round(secs, 1), "file": f"v/{final.name}"})
        print(f"made {final.name} ({secs:.1f}s): {script['topic']}")

        hist = json.loads(hist_f.read_text()) if hist_f.exists() else []
        if publish:
            base = pages_base()
            if not base:
                raise SystemExit("Not running on GitHub, so there's no public URL to host the video. Use --no-publish locally.")
            prune_old_videos()
            git_publish(["docs"], f"video: {name}")
            url = f"{base}/{script['file']}"
            if not wait_public(url):
                raise RuntimeError(f"video never became public at {url}")
            org = buffer.organization_id()
            chans = {c["service"]: c for c in buffer.channels(org) if not c.get("isDisconnected")}
            script["buffer_posts"] = {}
            for svc in CFG["post_to"]:
                if svc not in chans:
                    print("no connected channel for", svc); continue
                unverified = (script.get("fact_check") or {}).get("verdict") == "unverified" or \
                             (script.get("sound_check") or {}).get("verdict") == "fix"
                p = buffer.create_video_post(chans[svc]["id"], svc, script["final_caption"], url,
                                             script["youtube_title"], draft=CFG["require_approval"] or unverified)
                script["buffer_posts"][svc] = p["id"]
                print(f"buffer {svc}: {p['status']} {p.get('dueAt')}")
            script["video_url"] = url
        hist.append(script)
        hist_f.write_text(json.dumps(hist, indent=1))

    if publish:
        git_publish(["data", "docs", "knowledge", "autopilot/config.json"], f"autopilot data {datetime.date.today()}")


if __name__ == "__main__":
    try:
        main()
    except gemini.DailyQuotaExhausted:
        msg = ("Gemini's free daily limit is used up, so no video was made this time. Nothing is broken: "
               "the limit resets at midnight Pacific time and tomorrow's run will make the video as normal.")
        print("STOPPED:", msg)
        (DATA / "LAST_ERROR.txt").write_text(msg)
        sys.exit(1)
