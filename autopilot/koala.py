"""'Professor Koko', the Tool Hour AI teaching koala (designed with Google Gemini, animated with Veo).

assets/koala/koko_design.png  - Gemini's character design (green background), the source of every clip
assets/koala/<action>.mp4     - Veo clips of Koko teaching (hello, explain, point, wow, think, bye ...)

Koko stands big beside the lesson like a teacher at a board. Each scene plays the Veo clip that fits it,
keyed off its green background. If a clip is missing, the Gemini design itself is shown, bobbing to the beat.
"""
import pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
DESIGN = ROOT / "assets" / "koala" / "koko_design.png"
KEY = "chromakey=0x22e61b:0.17:0.07,despill=type=green"
BOX_W, BOX_H = 560, 995             # Koko's area, bottom-right


def still(out):
    """Gemini design keyed to a transparent PNG (cached per render)."""
    p = pathlib.Path(out) / "koko_still.png"
    if not DESIGN.exists():
        return None
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(DESIGN), "-vf",
                    f"format=rgba,{KEY},scale=w={BOX_W}:h={BOX_H}:force_original_aspect_ratio=decrease",
                    "-frames:v", "1", str(p)], check=True)
    return p


def overlay_args(bpm=116, clips=(), has_still=True):
    """Filter graph: input 0 = lesson video, 1 = Koko still (looped), 2.. = Veo clips for the (t0, t1) windows."""
    f = bpm / 60.0
    off = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in clips) or "0"
    g, cur = "", "[0:v]"
    if has_still:
        g += (f"[1:v]fps=30,format=rgba[k];"
              f"{cur}[k]overlay=x=W-w+50:y=H-h+210+abs(sin(PI*t*{f:.4f}))*-16:eval=frame:enable='not({off})'[s];")
        cur = "[s]"
    for i, (t0, t1) in enumerate(clips):
        g += (f"[{i + 2}:v]fps=30,format=rgba,{KEY},scale=w={BOX_W}:h={BOX_H}:force_original_aspect_ratio=decrease,"
              f"setpts=PTS-STARTPTS+{t0:.3f}/TB[c{i}];"
              f"{cur}[c{i}]overlay=x=W-w+50:y=H-h+210:eof_action=pass:enable='between(t,{t0:.3f},{t1:.3f})'[v{i}];")
        cur = f"[v{i}]"
    return g + f"{cur}null[v]"
