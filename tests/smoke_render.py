"""Renders a full test video offline (stand-in beep voice, no API keys) and checks the MP4.
Run: python3 tests/smoke_render.py
"""
import json, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "autopilot"))
import render  # noqa: E402


def beep_tts(_model, text, _voice, out, style=None):
    secs = max(0.8, 0.36 * len(text.split()))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"sine=frequency=220:sample_rate=24000:duration={secs:.2f}", "-ac", "1", out], check=True)


script = json.loads((ROOT / "tests/sample_script.json").read_text())
out = pathlib.Path(tempfile.mkdtemp(prefix="smoke-"))
mp4, total = render.render(script, out, None, beep_tts)
info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                       "-of", "json", str(mp4)], capture_output=True, text=True, check=True).stdout
d = json.loads(info)
streams = {s["codec_type"]: s for s in d["streams"]}
dur = float(d["format"]["duration"])
ok = "video" in streams and "audio" in streams and streams["video"]["width"] == 1080 and \
     streams["video"]["height"] == 1920 and 8 < dur < 90
print(f"smoke render: {dur:.1f}s, video={'video' in streams}, audio={'audio' in streams} -> {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
