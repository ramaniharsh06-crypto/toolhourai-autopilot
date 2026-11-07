"""The Auditor: runs on GitHub after every daily run (laptop closed).

1. Rollback guard - if the last daily run failed on a commit the Auditor made, revert it.
2. Health audit    - compile everything, validate the workflow, safety tests, offline smoke render.
3. Bug fixing      - reads the failed run's error, asks Gemini for a minimal patch, re-runs ALL tests,
                     pushes only if everything passes; otherwise undoes it and opens an issue.
4. CEO requests    - at most one small engineering request per week, under the same test gate.
Protected (never edited by the Auditor): governor.py, tests/, knowledge/, the workflow files, config.json.
"""
import datetime, json, os, pathlib, py_compile, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "autopilot"))
from lib import gemini  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "ramaniharsh06-crypto/toolhourai-autopilot")
EDITABLE = re.compile(r"^autopilot/(?!governor\.py$)[\w/]+\.py$")
LOG = []


def sh(*cmd, check=False, cwd=ROOT):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(cmd)} failed: {r.stderr[-800:]}")
    return r


def log(msg):
    print("auditor:", msg); LOG.append(msg)


def issue(title, body):
    sh("gh", "issue", "create", "-R", REPO, "--title", title, "--body", body)


# ---------------- tests ----------------
def run_tests(smoke=True):
    problems = []
    for f in list((ROOT / "autopilot").rglob("*.py")) + list((ROOT / "tests").glob("*.py")):
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            problems.append(f"compile error in {f.relative_to(ROOT)}: {str(e)[:300]}")
    try:
        import yaml
        for wf in (ROOT / ".github/workflows").glob("*.yml"):
            yaml.safe_load(wf.read_text())
    except ImportError:
        pass
    except Exception as e:
        problems.append(f"workflow YAML invalid: {e}")
    try:
        json.loads((ROOT / "autopilot/config.json").read_text())
    except Exception as e:
        problems.append(f"config.json invalid: {e}")
    r = sh(sys.executable, "tests/test_safety.py")
    if r.returncode:
        problems.append("safety tests failed:\n" + "\n".join(l for l in r.stdout.splitlines() if l.startswith("FAIL")))
    if smoke and not problems:
        r = sh(sys.executable, "tests/smoke_render.py")
        if r.returncode:
            problems.append("smoke render failed:\n" + (r.stdout + r.stderr)[-1500:])
    return problems


# ---------------- GitHub helpers ----------------
def last_daily_run():
    r = sh("gh", "run", "list", "-R", REPO, "-w", "autopilot.yml", "-L", "1",
           "--json", "databaseId,conclusion,headSha,status,event")
    runs = json.loads(r.stdout or "[]")
    return runs[0] if runs else None


def failed_log(run_id):
    r = sh("gh", "run", "view", str(run_id), "-R", REPO, "--log-failed")
    lines = [re.sub(r"^.*?Z ", "", l) for l in r.stdout.splitlines()]
    tb = [i for i, l in enumerate(lines) if "Traceback" in l or "Error" in l]
    start = max(0, (tb[0] if tb else len(lines)) - 10)
    return "\n".join(lines[start:start + 120])[-5000:]


# ---------------- rollback guard ----------------
def rollback_guard(run):
    if not run or run.get("conclusion") != "failure":
        return False
    msg = sh("git", "log", "-1", "--format=%s", run["headSha"]).stdout.strip()
    if not msg.startswith("auditor:"):
        return False
    log(f"daily run failed on my own commit '{msg}', reverting it")
    sh("git", "revert", "--no-edit", run["headSha"], check=True)
    sh("git", "push", check=True)
    issue("Auditor reverted its own change", f"The daily run failed after: {msg}. The change was reverted automatically.")
    return True


# ---------------- AI patching ----------------
def file_blob(paths):
    out = []
    for p in paths:
        f = ROOT / p
        if f.exists() and EDITABLE.match(p):
            out.append(f"===== {p} =====\n{f.read_text()[:14000]}")
    return "\n\n".join(out)


def relevant_files(text):
    found = re.findall(r"(autopilot/[\w/]+\.py)", text)
    base = ["autopilot/run.py", "autopilot/render.py", "autopilot/plan.py"]
    return list(dict.fromkeys([f for f in found if EDITABLE.match(f)] + base))[:5]


def try_patch(goal, context, files, model=None):
    prompt = f"""You are a careful senior Python engineer maintaining an automated video pipeline.
GOAL: {goal}
CONTEXT:
{context}

FILES YOU MAY EDIT (only these; never governor.py, tests, knowledge, workflows or config.json):
{file_blob(files)}

Make the SMALLEST change that achieves the goal. Do not weaken any safety check, quota handling or posting limit.
Return JSON: {{"summary":"one line","edits":[{{"file":"autopilot/...py","find":"exact existing text (unique)","replace":"new text"}}]}}
If you are not confident, return {{"summary":"not confident","edits":[]}}"""
    r = gemini.generate_json(model_name(), prompt, temperature=0.2)
    edits = r.get("edits") or []
    if not edits:
        return False, r.get("summary", "no edits proposed")
    for e in edits:
        p = e.get("file", "")
        if not EDITABLE.match(p):
            return False, f"refused: tried to edit protected file {p}"
        src = (ROOT / p).read_text()
        if src.count(e.get("find", "")) != 1:
            return False, f"refused: 'find' text not unique/absent in {p}"
        (ROOT / p).write_text(src.replace(e["find"], e["replace"], 1))
    problems = run_tests()
    if problems:
        sh("git", "checkout", "--", ".")
        return False, "patch failed tests: " + problems[0][:300]
    sh("git", "add", "-A", "autopilot")
    sh("git", "commit", "-m", f"auditor: {r.get('summary', goal)[:70]}\n\nCo-Authored-By: Gemini (Tool Hour AI Auditor)", check=True)
    sh("git", "push", check=True)
    return True, r.get("summary", goal)


# ---------------- CEO requests ----------------
def ceo_request():
    st_f = DATA / "audit_state.json"
    st = json.loads(st_f.read_text()) if st_f.exists() else {}
    last = st.get("last_request", "2000-01-01")
    if (datetime.date.today() - datetime.date.fromisoformat(last)).days < 7:
        return None
    memo = DATA / "CEO_MEMO.md"
    if not memo.exists():
        return None
    reqs = re.findall(r"^- \[ \] (.+)$", memo.read_text(), re.M)
    st["last_request"] = datetime.date.today().isoformat()
    st_f.write_text(json.dumps(st))
    return reqs[0] if reqs else None


_MODEL = []


def model_name():
    """Ask Gemini for a model only when a fix is actually needed (checks never spend quota)."""
    if not _MODEL:
        _MODEL.append(gemini.pick_models()[0])
    return _MODEL[0]


def main():
    run = last_daily_run()
    if rollback_guard(run):
        write_log(); return

    problems = run_tests()
    for p in problems:
        log("health problem: " + p.splitlines()[0][:200])

    if run and run.get("conclusion") == "failure":
        err = failed_log(run["databaseId"])
        if "free daily limit" in err or "exceeded your current quota" in err:
            log("last run stopped on Gemini's free daily quota: not a bug, nothing to fix")
        else:
            ok, msg = try_patch("Fix the error that made the last daily run fail.", err, relevant_files(err), model)
            log(("FIXED and pushed: " if ok else "could not fix automatically: ") + msg)
            if not ok:
                issue("Auditor: daily run failed and needs a human look", f"{msg}\n\n```\n{err[-2500:]}\n```")
    elif problems:
        ok, msg = try_patch("Fix these health-check problems.", "\n".join(problems), relevant_files("\n".join(problems)), model)
        log(("FIXED and pushed: " if ok else "could not fix automatically: ") + msg)

    req = ceo_request()
    if req:
        ok, msg = try_patch(f"Implement this request from the CEO, safely and minimally: {req}", "CEO engineering request",
                            ["autopilot/run.py", "autopilot/render.py", "autopilot/visuals.py", "autopilot/plan.py"], model)
        log(f"CEO request '{req[:80]}': " + ("built and pushed" if ok else "not built: " + msg))
        if ok:
            memo = DATA / "CEO_MEMO.md"
            memo.write_text(memo.read_text().replace(f"- [ ] {req}", f"- [x] {req} (built by Auditor)", 1))
    if not LOG:
        log("all checks passed, nothing to do")
    write_log()


def write_log():
    f = DATA / "AUDIT_LOG.md"
    entry = f"## {datetime.datetime.utcnow():%Y-%m-%d %H:%M} UTC\n" + "\n".join(f"- {l}" for l in LOG) + "\n\n"
    f.write_text(entry + (f.read_text() if f.exists() else ""))
    sh("git", "add", "data")
    if sh("git", "diff", "--cached", "--quiet").returncode:
        sh("git", "commit", "-m", f"audit log {datetime.date.today()}")
        sh("git", "pull", "--rebase")
        sh("git", "push")


if __name__ == "__main__":
    try:
        main()
    except gemini.DailyQuotaExhausted:
        log("Gemini's free daily limit is used up; audit will retry after the next run")
        write_log()
