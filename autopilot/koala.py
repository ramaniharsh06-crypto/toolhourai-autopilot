"""'Professor Koko', the Tool Hour AI teaching koala.

Drawn in SVG (original character, free, identical every video), rendered once into a few poses, then animated
over the finished video: the mouth follows the real loudness of the voice (lip-sync), eyes blink, the pointer
arm moves on the beat, the whole koala bobs to the music, and it gasps ("wow") on the result moment.
"""
import math, pathlib, subprocess, wave, array

W, H = 340, 380          # koala canvas (px)
FUR, FUR_D, BELLY, EAR_IN, NOSE, INK, ACC = "#a9b3bd", "#8a95a1", "#f1ece3", "#f6d3d6", "#2c2c35", "#16161c", "#ff7a3d"


def svg(mouth="closed", eyes="open", arm="up"):
    # eyes
    if eyes == "blink":
        ey = ('<path d="M100 150 q14 10 28 0" stroke="{i}" stroke-width="6" fill="none" stroke-linecap="round"/>'
              '<path d="M212 150 q14 10 28 0" stroke="{i}" stroke-width="6" fill="none" stroke-linecap="round"/>')
    elif eyes == "wow":
        ey = ('<circle cx="114" cy="148" r="19" fill="{i}"/><circle cx="226" cy="148" r="19" fill="{i}"/>'
              '<circle cx="120" cy="141" r="7" fill="#fff"/><circle cx="232" cy="141" r="7" fill="#fff"/>'
              '<circle cx="108" cy="156" r="3" fill="#fff"/><circle cx="220" cy="156" r="3" fill="#fff"/>'
              '<path d="M60 92 l8 -16 l8 16 l16 8 l-16 8 l-8 16 l-8 -16 l-16 -8z" fill="#ffd34d"/>'
              '<path d="M282 86 l6 -12 l6 12 l12 6 l-12 6 l-6 12 l-6 -12 l-12 -6z" fill="#ffd34d"/>')
    else:
        ey = ('<circle cx="114" cy="150" r="14" fill="{i}"/><circle cx="226" cy="150" r="14" fill="{i}"/>'
              '<circle cx="119" cy="145" r="5" fill="#fff"/><circle cx="231" cy="145" r="5" fill="#fff"/>')
    ey = ey.format(i=INK)
    # mouth (under the big nose)
    m = {"closed": '<path d="M150 226 q20 14 40 0" stroke="{i}" stroke-width="6" fill="none" stroke-linecap="round"/>',
         "half":   '<ellipse cx="170" cy="230" rx="15" ry="8" fill="{i}"/>',
         "open":   '<ellipse cx="170" cy="234" rx="18" ry="15" fill="{i}"/><ellipse cx="170" cy="242" rx="11" ry="6" fill="#ff8fa0"/>',
         "wide":   '<ellipse cx="170" cy="236" rx="22" ry="21" fill="{i}"/><ellipse cx="170" cy="247" rx="13" ry="8" fill="#ff8fa0"/>',
         }[mouth].format(i=INK)
    # pointer arm (left side of the koala, pointing up-left at the lesson)
    if arm == "up":
        arm_svg = ('<g transform="rotate(-26 92 300)"><line x1="92" y1="300" x2="92" y2="176" stroke="#7a4a2a" stroke-width="9" stroke-linecap="round"/>'
                   f'<circle cx="92" cy="176" r="10" fill="{ACC}"/></g>'
                   f'<ellipse cx="86" cy="300" rx="30" ry="40" fill="{FUR}" transform="rotate(-30 86 300)"/>')
    else:
        arm_svg = ('<g transform="rotate(-44 92 306)"><line x1="92" y1="306" x2="92" y2="186" stroke="#7a4a2a" stroke-width="9" stroke-linecap="round"/>'
                   f'<circle cx="92" cy="186" r="10" fill="{ACC}"/></g>'
                   f'<ellipse cx="84" cy="306" rx="30" ry="40" fill="{FUR}" transform="rotate(-55 84 306)"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs><radialGradient id="f" cx="40%" cy="35%" r="70%"><stop offset="0" stop-color="#bcc5ce"/><stop offset="1" stop-color="{FUR}"/></radialGradient></defs>
<ellipse cx="172" cy="370" rx="110" ry="10" fill="#000" opacity=".18"/>
<path d="M78 380 Q70 250 172 238 Q274 250 266 380 Z" fill="{FUR}"/>
<ellipse cx="172" cy="330" rx="62" ry="56" fill="{BELLY}"/>
<ellipse cx="250" cy="318" rx="28" ry="36" fill="{FUR_D}" transform="rotate(20 250 318)"/>
<circle cx="66" cy="96" r="60" fill="{FUR}"/><circle cx="66" cy="96" r="36" fill="{EAR_IN}"/>
<circle cx="278" cy="96" r="60" fill="{FUR}"/><circle cx="278" cy="96" r="36" fill="{EAR_IN}"/>
<circle cx="40" cy="70" r="12" fill="#fff" opacity=".7"/><circle cx="304" cy="70" r="12" fill="#fff" opacity=".7"/>
<ellipse cx="172" cy="160" rx="112" ry="100" fill="url(#f)"/>
<ellipse cx="96" cy="196" rx="20" ry="12" fill="#ffb3b8" opacity=".8"/><ellipse cx="248" cy="196" rx="20" ry="12" fill="#ffb3b8" opacity=".8"/>
{ey}
<ellipse cx="170" cy="186" rx="34" ry="42" fill="{NOSE}"/><ellipse cx="158" cy="170" rx="9" ry="13" fill="#fff" opacity=".35"/>
{m}
<polygon points="172,14 262,44 172,74 82,44" fill="{INK}"/><rect x="132" y="50" width="80" height="34" rx="6" fill="{INK}"/>
<path d="M172 44 L240 56 L240 98" stroke="{ACC}" stroke-width="5" fill="none"/><circle cx="240" cy="104" r="9" fill="{ACC}"/>
{arm_svg}
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
        g += (f";[{i + 2}:v]fps=30,chromakey=0x00ff00:0.22:0.08,despill=type=green,scale=-1:640,format=rgba,"
              f"setpts=PTS-STARTPTS+{t0:.3f}/TB[c{i}];"
              f"[v{i}][c{i}]overlay=x=W-w+20:y=H-h+10:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[v{i + 1}]")
    return g + f";[v{len(clips)}]null[v]"
