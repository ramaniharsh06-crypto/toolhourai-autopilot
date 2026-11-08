"""'Professor Koko', the Tool Hour AI teaching koala (designed with Google Gemini).

Koko really says the words: his mouth is driven by the loudness of the actual voiceover ~15 times a second
(closed in pauses, "oh" for medium sounds, "ah" for loud ones), he blinks naturally and bobs to the music.

assets/koala/koko_design.png       Gemini's character design (green background)
assets/koala/koko_mouth_<m>.png    the same image edited by Gemini with only the mouth changed (closed / oh / ah)
assets/koala/koko_blink.png        the same image with only the eyes closed
Only the changed region (found automatically) is pasted onto the design, so Koko never jitters.
"""
import array, math, pathlib, re, subprocess, wave

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIB = ROOT / "assets" / "koala"
DESIGN = LIB / "koko_design.png"
KEY = "chromakey=0x22e61b:0.17:0.07,despill=type=green"
BOX_W, BOX_H = 560, 995
MOUTHS = ("closed", "oh", "ah")


def _ff(*a):
    return subprocess.run(["ffmpeg", "-hide_banner", "-y", *map(str, a)], capture_output=True, text=True)


def _size(img):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(img)],
                       capture_output=True, text=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def changed_box(base, var, pad=28):
    """Bounding box of what Gemini changed (mouth or eyes); None if the whole picture moved."""
    W, H = _size(base)
    sw, sh = 384, int(384 * H / W)                  # analyse a small difference map
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(base), "-i", str(var), "-filter_complex",
                        f"[1:v]scale={W}:{H}[b];[0:v][b]blend=all_mode=difference,format=gray,boxblur=2,scale={sw}:{sh}",
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    px = r.stdout
    if len(px) < sw * sh:
        return None
    hot = [[px[y * sw + x] > 40 for x in range(sw)] for y in range(sh)]
    rows = [y for y in range(sh) if sum(hot[y]) >= 4]          # ignore scattered fur noise
    cols = [x for x in range(sw) if sum(hot[y][x] for y in rows) >= 4] if rows else []
    if not rows or not cols:
        return None
    # keep the densest cluster of rows (the mouth / eyes), not stray noise far away
    best, cur = [], [rows[0]]
    for y in rows[1:]:
        if y - cur[-1] <= 6:
            cur.append(y)
        else:
            best = max(best, cur, key=len); cur = [y]
    rows = max(best, cur, key=len)
    cols = [x for x in range(sw) if sum(hot[y][x] for y in rows) >= 3]
    x0, x1, y0, y1 = min(cols), max(cols), min(rows), max(rows)
    k = W / sw
    x, y, w, h = int(x0 * k), int(y0 * k), int((x1 - x0 + 1) * k), int((y1 - y0 + 1) * k)
    if w > W * 0.6 or h > H * 0.35:
        return None
    x, y = max(0, x - pad), max(0, y - pad)
    return x, y, min(W - x, w + 2 * pad), min(H - y, h + 2 * pad)


def _patch(base, var, box, out):
    W, H = _size(base)
    x, y, w, h = box
    f = max(6, min(w, h) // 8)                      # soft feathered edge
    _ff("-i", base, "-i", var, "-filter_complex",
        f"[1:v]scale={W}:{H},crop={w}:{h}:{x}:{y},format=rgba[p];"
        f"color=c=black:s={w}x{h},format=gray,drawbox=x={f}:y={f}:w={w - 2 * f}:h={h - 2 * f}:color=white:t=fill,"
        f"boxblur={f // 2}[m];[p][m]alphamerge[pm];[0:v][pm]overlay={x}:{y}",
        "-frames:v", "1", out)


def build(out):
    """Make the 6 Koko states (3 mouths x eyes open/blink), keyed and sized. Returns {state: png} or {}."""
    out = pathlib.Path(out)
    if not DESIGN.exists():
        return {}
    srcs = {}
    for m in MOUTHS:
        p = LIB / f"koko_mouth_{m}.png"
        img = out / f"kk_{m}.png"
        box = changed_box(DESIGN, p) if p.exists() else None
        if box:
            _patch(DESIGN, p, box, img)
        else:
            _ff("-i", DESIGN, "-frames:v", "1", img)
        srcs[m] = img
    blink = LIB / "koko_blink.png"
    bbox = changed_box(DESIGN, blink) if blink.exists() else None
    states = {}
    for m, img in srcs.items():
        for b in (False, True):
            src = img
            if b:
                if not bbox:
                    continue
                src = out / f"kk_{m}_bl.png"
                _patch(img, blink, bbox, src)
            name = f"k_{m}{'_b' if b else ''}.png"
            _ff("-i", src, "-vf", f"format=rgba,{KEY},scale=w={BOX_W}:h={BOX_H}:force_original_aspect_ratio=decrease",
                "-frames:v", "1", out / name)
            states[(m, b)] = name
    return states


def loudness(wav_path, step):
    with wave.open(str(wav_path)) as w:
        sr = w.getframerate()
        a = array.array("h", w.readframes(w.getnframes()))
    n = max(1, int(sr * step))
    return [math.sqrt(sum(x * x for x in a[i:i + n]) / max(1, len(a[i:i + n]))) for i in range(0, len(a), n)]


def track(voice_wav, out, total, states, step=1 / 15):
    """Concat list: Koko's mouth follows the voice; blinks every ~3.3 s."""
    rms = loudness(voice_wav, step)
    ref = sorted(rms)[int(len(rms) * 0.92)] or 1.0
    can_blink = any(b for _, b in states)
    lines, prev = [], "closed"
    for k in range(int(total / step) + 1):
        t = k * step
        lvl = (rms[k] if k < len(rms) else 0) / ref
        m = "closed" if lvl < 0.14 else "oh" if lvl < 0.5 else "ah"
        if m == prev == "ah":
            m = "oh"                                 # keep the jaw moving, never frozen open
        prev = m
        blink = can_blink and (t % 3.3) < 0.14
        lines.append(f"file '{states[(m, blink)]}'\nduration {step:.4f}\n")
    lines.append(lines[-1].split("\n")[0] + "\n")
    lst = pathlib.Path(out) / "koko.txt"
    lst.write_text("".join(lines))
    return lst


def overlay_args(bpm=116):
    f = bpm / 60.0
    return (f"[1:v]fps=30,format=rgba[k];"
            f"[0:v][k]overlay=x=W-w+50:y=H-h+210+abs(sin(PI*t*{f:.4f}))*-14:eval=frame[v]")
