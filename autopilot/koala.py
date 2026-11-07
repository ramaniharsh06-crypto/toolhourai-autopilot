"""'Professor Koko', the Tool Hour AI teaching koala.

Drawn in SVG (original character, free, identical every video), rendered once into a few poses, then animated
over the finished video: the mouth follows the real loudness of the voice (lip-sync), eyes blink, the pointer
arm moves on the beat, the whole koala bobs to the music, and it gasps ("wow") on the result moment.
"""
import math, pathlib, subprocess, wave, array

W, H = 340, 380          # koala canvas (px)
FUR, FUR_L, BELLY, EAR_IN, EAR_IN2, NOSE, EYE, OL, ACC, STAR = (
    "#a7b1c2", "#cdd5e1", "#fff6ea", "#ffbfcc", "#ffdbe2", "#4a3e52", "#1c1d29", "#3c4152", "#ff7a3d", "#ffd23f")
LINE = f'stroke="{OL}" stroke-width="5" stroke-linejoin="round"'


def _star(cx, cy, r, fill=STAR):
    pts = []
    for k in range(10):
        ang = math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append(f"{cx + rr * math.cos(ang):.1f},{cy - rr * math.sin(ang):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="{OL}" stroke-width="3.5" stroke-linejoin="round"/>'


def svg(mouth="closed", eyes="open", arm="up"):
    """Chibi Professor Koko: big head, huge glossy eyes, fluffy ears, tilted cap, orange bow tie, star pointer."""
    def eye(cx, cy):
        if eyes == "blink":                       # happy closed eyes ^ ^
            return f'<path d="M{cx-19} {cy+4} q19 -20 38 0" stroke="{EYE}" stroke-width="7" fill="none" stroke-linecap="round"/>'
        rx, ry = (23, 29) if eyes == "wow" else (20, 25)
        e = (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{EYE}"/>'
             f'<ellipse cx="{cx}" cy="{cy+12}" rx="{rx-7}" ry="{ry-17}" fill="#3b3f63" opacity=".9"/>'
             f'<circle cx="{cx+7}" cy="{cy-10}" r="{9 if eyes == "wow" else 8}" fill="#fff"/>'
             f'<circle cx="{cx-7}" cy="{cy+9}" r="4" fill="#fff"/>')
        if eyes == "wow":
            e += _star(cx + 7, cy - 10, 8, "#fff")
        return e
    ey = eye(118, 172) + eye(222, 172)
    sparkles = (_star(40, 210, 16) + _star(300, 214, 13) + _star(292, 40, 10)) if eyes == "wow" else ""
    m = {"closed": f'<path d="M148 231 q11 11 22 0 q11 11 22 0" stroke="{EYE}" stroke-width="5.5" fill="none" stroke-linecap="round"/>',
         "half":   f'<path d="M156 230 q14 -3 28 0 q-2 14 -14 14 q-12 0 -14 -14z" fill="{EYE}"/>',
         "open":   f'<path d="M152 229 q18 -4 36 0 q-1 22 -18 22 q-17 0 -18 -22z" fill="{EYE}"/>'
                   '<ellipse cx="170" cy="243" rx="10" ry="6" fill="#ff7f98"/>',
         "wide":   f'<path d="M148 228 q22 -5 44 0 q0 30 -22 30 q-22 0 -22 -30z" fill="{EYE}"/>'
                   '<ellipse cx="170" cy="249" rx="13" ry="8" fill="#ff7f98"/>',
         }[mouth]
    rot = -20 if arm == "up" else -38
    pointer = (f'<g transform="rotate({rot} 92 300)">'
               f'<line x1="92" y1="300" x2="92" y2="196" stroke="{OL}" stroke-width="12" stroke-linecap="round"/>'
               f'<line x1="92" y1="300" x2="92" y2="196" stroke="#b9773f" stroke-width="6" stroke-linecap="round"/>'
               f'{_star(92, 186, 20)}</g>'
               f'<ellipse cx="90" cy="302" rx="23" ry="27" fill="{FUR}" {LINE} transform="rotate(-25 90 302)"/>')
    ear = lambda cx: (f'<circle cx="{cx}" cy="94" r="60" fill="{FUR}" {LINE}/>'
                      f'<circle cx="{cx + (-22 if cx < 170 else 22)}" cy="70" r="16" fill="{FUR_L}"/>'
                      f'<circle cx="{cx + (-34 if cx < 170 else 34)}" cy="98" r="12" fill="{FUR_L}"/>'
                      f'<circle cx="{cx}" cy="98" r="36" fill="{EAR_IN}"/><circle cx="{cx}" cy="102" r="22" fill="{EAR_IN2}"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs><radialGradient id="f" cx="42%" cy="32%" r="75%"><stop offset="0" stop-color="{FUR_L}"/><stop offset="1" stop-color="{FUR}"/></radialGradient></defs>
<ellipse cx="170" cy="372" rx="100" ry="8" fill="#000" opacity=".16"/>
<ellipse cx="128" cy="362" rx="27" ry="14" fill="{FUR}" {LINE}/><ellipse cx="212" cy="362" rx="27" ry="14" fill="{FUR}" {LINE}/>
<ellipse cx="170" cy="314" rx="86" ry="58" fill="url(#f)" {LINE}/>
<ellipse cx="170" cy="324" rx="52" ry="38" fill="{BELLY}"/>
<ellipse cx="252" cy="312" rx="22" ry="29" fill="{FUR}" {LINE} transform="rotate(-18 252 312)"/>
{ear(62)}{ear(278)}
<ellipse cx="170" cy="162" rx="128" ry="108" fill="url(#f)" {LINE}/>
<path d="M150 58 q8 -22 20 -4 q10 -20 22 2" fill="{FUR}" {LINE}/>
<g transform="rotate(-9 170 52)"><polygon points="170,14 256,42 170,70 84,42" fill="#25262f" {LINE}/>
<rect x="138" y="48" width="64" height="22" rx="6" fill="#25262f"/>
<path d="M170 42 L236 54 L236 92" stroke="{ACC}" stroke-width="5" fill="none" stroke-linecap="round"/>
<path d="M228 92 h16 l-3 18 h-10z" fill="{ACC}"/></g>
<ellipse cx="86" cy="214" rx="22" ry="12" fill="#ff9db1" opacity=".8"/><ellipse cx="254" cy="214" rx="22" ry="12" fill="#ff9db1" opacity=".8"/>
<circle cx="80" cy="210" r="3" fill="#fff" opacity=".9"/><circle cx="248" cy="210" r="3" fill="#fff" opacity=".9"/>
{ey}
<path d="M140 200 q0 -18 30 -18 q30 0 30 18 q0 18 -30 18 q-30 0 -30 -18z" fill="{NOSE}"/>
<ellipse cx="158" cy="193" rx="9" ry="5" fill="#fff" opacity=".55"/>
{m}
<path d="M170 278 l-30 -15 q-6 15 0 30z M170 278 l30 -15 q6 15 0 30z" fill="{ACC}" {LINE}/>
<circle cx="170" cy="278" r="8" fill="#e85f22" {LINE}/>
{sparkles}{pointer}
</svg>"""


POSES = [(m, e, a) for a in ("up", "mid") for e in ("open", "blink") for m in ("closed", "half", "open", "wide")] + \
        [(m, "wow", a) for a in ("up", "mid") for m in ("open", "wide")]


def pose_name(m, e, a):
    return f"k_{m}_{e}_{a}.png"


def render_poses(out, chrome):
    out = pathlib.Path(out)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"color=c=black@0.0:s={W}x{H},format=rgba", "-frames:v", "1", str(out / "k_blank.png")], check=True)
    for m, e, a in POSES:
        page = out / "koala.html"
        page.write_text(f'<!doctype html><html><body style="margin:0;background:transparent">{svg(m, e, a)}</body></html>')
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                        "--default-background-color=00000000", f"--window-size={W},{H}",
                        f"--screenshot={out / pose_name(m, e, a)}", page.as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


def loudness(wav_path, step):
    """RMS of a mono 16-bit wav every `step` seconds."""
    with wave.open(str(wav_path)) as w:
        sr = w.getframerate()
        a = array.array("h", w.readframes(w.getnframes()))
    n = max(1, int(sr * step))
    return [math.sqrt(sum(x * x for x in a[i:i + n]) / max(1, len(a[i:i + n]))) for i in range(0, len(a), n)]


def track(voice_wav, out, total, bpm=116, wow_times=(), step=1 / 15, hide=()):
    """Write a concat list of koala poses (lip-synced to voice_wav) and return its path."""
    out = pathlib.Path(out)
    rms = loudness(voice_wav, step)
    ref = sorted(rms)[int(len(rms) * 0.92)] or 1.0
    beat = 60.0 / bpm
    lines, prev = [], "closed"
    steps = int(total / step) + 1
    for k in range(steps):
        t = k * step
        lvl = (rms[k] if k < len(rms) else 0) / ref
        mouth = "closed" if lvl < 0.12 else "half" if lvl < 0.38 else "open" if lvl < 0.75 else "wide"
        if mouth != "closed" and prev == mouth == "wide":
            mouth = "open"                                     # keeps the jaw moving instead of frozen wide
        prev = mouth
        arm = "up" if int(t / beat) % 4 < 2 else "mid"
        wow = any(0 <= t - w < 0.9 for w in wow_times)
        if wow:
            eyes, mouth = "wow", ("wide" if mouth in ("open", "wide") else "open")
        else:
            eyes = "blink" if (t % 3.3) < 0.13 else "open"
        name = "k_blank.png" if any(a <= t < b for a, b in hide) else pose_name(mouth, eyes, arm)
        lines.append(f"file '{name}'\nduration {step:.4f}\n")
    lines.append(lines[-1].split("\n")[0] + "\n")              # concat demuxer needs the last file repeated
    lst = out / "koala.txt"
    lst.write_text("".join(lines))
    return lst


def overlay_args(bpm=116, clips=()):
    """ffmpeg filter: drawn koala bottom-right, bobbing on the beat; Veo clips (inputs 2..) keyed over it."""
    f = bpm / 60.0
    g = (f"[1:v]fps=30,format=rgba,scale=380:-1[k];"
         f"[0:v][k]overlay=x=W-w-18:y=H-h-22+abs(sin(PI*t*{f:.4f}))*-14:eval=frame:format=auto[v0]")
    for i, (t0, t1) in enumerate(clips):
        g += (f";[{i + 2}:v]fps=30,chromakey=0x00ff00:0.22:0.08,despill=type=green,scale=w=440:h=640:force_original_aspect_ratio=decrease,format=rgba,"
              f"setpts=PTS-STARTPTS+{t0:.3f}/TB[c{i}];"
              f"[v{i}][c{i}]overlay=x=W-w+20:y=H-h+10:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[v{i + 1}]")
    return g + f";[v{len(clips)}]null[v]"
