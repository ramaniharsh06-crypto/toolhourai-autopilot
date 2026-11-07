"""Veo Koala clip library: real animated clips of Professor Koko, made ONCE and reused in every video.

Zero-cost rules (the owner pays nothing beyond the Gemini Pro plan):
- Uses its own key (VEO_API_KEY) on the separate "toolhour-veo" project, which is on the free-trial billing
  account (never charged unless upgraded) and has a Google spend cap of Rs 700/month on the Gemini API.
- On top of that, this file keeps its own ledger and never generates more than MAX_SECONDS_PER_MONTH,
  which costs well under the free monthly credit. No key, an error, or a used-up budget -> it simply skips,
  and videos use the drawn koala instead.
"""
import base64, datetime, json, os, pathlib, subprocess, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIB = ROOT / "assets" / "koala"
LEDGER = ROOT / "data" / "veo_ledger.json"
API = "https://generativelanguage.googleapis.com/v1beta"
MAX_SECONDS_PER_MONTH = 24          # ~6 short clips; far below the free monthly credit
CLIP_SECONDS = 4
GREEN = "#00ff00"

STYLE = ("Cute 2D cartoon koala teacher character exactly like the reference image: grey fur, big round pink ears, "
         "big dark nose, rosy cheeks, black graduation cap with an orange tassel, holding a small wooden pointer stick "
         "with an orange tip. Flat vector cartoon style, smooth bouncy animation, the character stays fully in frame, "
         f"centered. Solid flat pure green background ({GREEN}), no shadows on the background, no text, no other objects.")
CLIPS = {   # name -> action
    "explain": "The koala explains a lesson, talking enthusiastically, nodding and gesturing with its paw and wand.",
    "hello": "The koala pops up, waves hello with a big happy smile and a little bounce.",
    "point": "The koala excitedly points the stick up and to the left, nodding as if explaining something.",
    "wow":   "The koala gasps in amazement, eyes sparkle, then claps its paws happily.",
    "bye":   "The koala waves goodbye cheerfully and does a small happy jump.",
    "think": "The koala taps its chin with the pointer, thinking, then smiles with an idea.",
    "dance": "The koala does a short cute happy dance, swaying side to side.",
}


def key():
    return os.environ.get("VEO_API_KEY")


def _call(method, path, body=None):
    url = path if path.startswith("http") else f"{API}/{path}"
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"x-goog-api-key": key(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read() or b"{}")


def pick_model():
    models = _call("GET", "models?pageSize=1000").get("models", [])
    names = [m["name"].split("/")[-1] for m in models if "veo" in m["name"].lower()]
    print("veo: video models on this key:", names or "none", f"({len(models)} models total)")
    if not names:
        return None
    rank = lambda n: (("lite" in n) * 3 + ("fast" in n) * 2 + ("3.1" in n), n)   # cheapest good model first
    return sorted(names, key=rank, reverse=True)[0]


def ledger():
    month = datetime.date.today().strftime("%Y-%m")
    d = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    return d, month


def seconds_left():
    d, month = ledger()
    return MAX_SECONDS_PER_MONTH - d.get(month, {}).get("seconds", 0)


def spend(seconds, clip):
    d, month = ledger()
    m = d.setdefault(month, {"seconds": 0, "clips": []})
    m["seconds"] += seconds; m["clips"].append(clip)
    LEDGER.write_text(json.dumps(d, indent=1))


def reference_png(chrome=None):
    """Gemini's Koko design (green background): the first frame, so Veo keeps the same character."""
    return LIB / "koko_design.png"


def generate(model, action, ref_png, out):
    body = {"instances": [{"prompt": f"{STYLE} {action}",
                           "image": {"bytesBase64Encoded": base64.b64encode(ref_png.read_bytes()).decode(),
                                     "mimeType": "image/png"}}],
            "parameters": {"aspectRatio": "9:16", "durationSeconds": CLIP_SECONDS, "sampleCount": 1}}
    op = _call("POST", f"models/{model}:predictLongRunning", body)
    for _ in range(60):                                  # up to ~10 minutes
        if op.get("done"):
            break
        time.sleep(10)
        op = _call("GET", op["name"])
    if not op.get("done") or op.get("error"):
        raise RuntimeError(f"veo failed: {str(op.get('error', 'timeout'))[:200]}")
    uri = op["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
    req = urllib.request.Request(uri, headers={"x-goog-api-key": key()})
    with urllib.request.urlopen(req, timeout=300) as r:
        out.write_bytes(r.read())


def build_library(chrome, max_new=2):
    """Make up to `max_new` missing clips this run, inside the monthly budget. Never raises."""
    if not key():
        print("veo: no VEO_API_KEY, using the drawn koala"); return []
    LIB.mkdir(parents=True, exist_ok=True)
    missing = [c for c in CLIPS if not (LIB / f"{c}.mp4").exists()]
    if not missing:
        return []
    made = []
    try:
        model = pick_model()
        if not model:
            print("veo: no Veo model available on this key"); return []
        ref = reference_png(chrome)
        for c in missing[:max_new]:
            if seconds_left() < CLIP_SECONDS:
                print("veo: monthly free budget reached, waiting for next month"); break
            spend(CLIP_SECONDS, c)                       # count it BEFORE calling, so a crash can't overspend
            generate(model, CLIPS[c], ref, LIB / f"{c}.mp4")
            print(f"veo: made koala clip '{c}' with {model}")
            made.append(c)
    except urllib.error.HTTPError as e:
        print("veo skipped:", e.code, e.read()[:200])
    except Exception as e:
        print("veo skipped:", str(e)[:200])
    return made


def clip(name):
    p = LIB / f"{name}.mp4"
    return p if p.exists() else None


if __name__ == "__main__":          # one test clip: python autopilot/veo.py
    import sys
    sys.path.insert(0, str(ROOT / "autopilot"))
    import render
    made = build_library(render.chrome(), max_new=1)
    print("made:", made or "nothing")
    sys.exit(0 if made else 1)
