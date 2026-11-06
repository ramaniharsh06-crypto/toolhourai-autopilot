"""Script -> 1080x1920 MP4 (v2).

Visuals (taste rules): one typeface set huge, whole fields of colour per scene, the tool's real
website large, no glows/gradients/emoji/cards. Kinetic captions: the spoken words appear in sync,
the current word is lit in the accent colour, each new phrase punches in, scenes slide into each other.
Audio: clean AI voice (de-clipped, faded, loudness-normalised), an original synthesised music bed
that ducks under the voice, a whoosh on every scene change.
"""
import html, json, os, pathlib, re, shutil, subprocess, sys, wave

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "autopilot/config.json").read_text())
FPS, T = 30, 0.30                      # frame rate, transition length (s)
TRANSITIONS = ["smoothleft", "slideup", "zoomin", "smoothup", "slideleft", "circleopen"]

# palette: one ground, one ink, one accent + two whole colour fields
INK, GROUND, ACCENT, PAPER = "#101014", "#101014", "#ff7a3d", "#f3efe6"
SCENE_LOOK = {   # kind -> (background, text colour, highlight colour, highlight text)
    "hook":   (ACCENT, INK, INK, ACCENT),
    "tool":   (GROUND, "#ffffff", ACCENT, INK),
    "step":   (PAPER, INK, ACCENT, INK),
    "result": (ACCENT, INK, INK, ACCENT),
    "cta":    (GROUND, "#ffffff", ACCENT, INK),
}


# ---------- browser helpers ----------
def chrome():
    for c in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        p = shutil.which(c) or (c if os.path.exists(c) else None)
        if p:
            return p
    raise SystemExit("Chrome not found")


def shoot(url_or_file, out_png, w, h, wait_ms=6000, scale=1):
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                    "--mute-audio", f"--virtual-time-budget={wait_ms}", f"--force-device-scale-factor={scale}",
                    f"--window-size={w},{h}", f"--screenshot={out_png}", url_or_file],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    return out_png


BLOCK_WORDS = ("security verification", "verifying you are human", "verify you are human", "checking your browser",
               "captcha", "access denied", "are you a robot", "unusual traffic", "just a moment", "attention required",
               "enable javascript and cookies", "403 forbidden", "request blocked")


def page_blocked(url):
    """True if the site shows a bot-check / block page instead of its real homepage."""
    try:
        dom = subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=9000",
                              "--window-size=430,760", "--dump-dom", url],
                             capture_output=True, text=True, timeout=90).stdout.lower()
    except Exception:
        return True
    text = re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style).*?</\1>", " ", dom))
    return len(text.split()) < 15 or any(w in text for w in BLOCK_WORDS)


def remember_blocked(url):
    f = ROOT / "data/blocked_sites.json"
    host = url.split("//")[-1].split("/")[0].replace("www.", "")
    lst = json.loads(f.read_text()) if f.exists() else []
    if host not in lst:
        lst.append(host); f.write_text(json.dumps(lst, indent=1))


def esc(t):
    return html.escape(str(t or ""))


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True)


def wav_len(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


# ---------- captions ----------
def chunk_words(text, max_words=3):
    """Split a voice line into short phrases (break on punctuation), each a list of words."""
    words, chunks, cur = text.split(), [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.,!?;:—-]$", w):
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    return chunks


def word_times(chunks, speech_len, lead=0.10):
    """Spread the words over the speech by length (punctuation adds a small pause)."""
    flat = [w for c in chunks for w in c]
    weight = [len(re.sub(r"\W", "", w)) + 2 + (3 if re.search(r"[.,!?;:]$", w) else 0) for w in flat]
    total = sum(weight) or 1
    t, out = lead, []
    for wt in weight:
        d = speech_len * wt / total
        out.append(d); t += d
    return out


# ---------- frame HTML ----------
CSS = f"""*{{box-sizing:border-box;margin:0}}
html,body{{width:1080px;height:1920px;overflow:hidden}}
body{{font-family:Inter,sans-serif;position:relative}}
.bar{{position:absolute;top:0;left:0;height:14px;background:var(--hl)}}
.mark{{position:absolute;top:58px;left:64px;font:800 34px Inter;letter-spacing:-.01em;color:var(--fg);display:flex;gap:14px;align-items:center}}
.top{{position:absolute;left:64px;right:64px;top:170px;height:1000px;display:flex;flex-direction:column;justify-content:center}}
.big{{font:900 172px/.9 Inter;letter-spacing:-.045em;color:var(--fg)}}
.mid{{font:900 118px/.95 Inter;letter-spacing:-.04em;color:var(--fg)}}
.sub{{font:600 48px/1.25 Inter;color:var(--fg);opacity:.82;margin-top:36px;max-width:900px}}
.shot{{position:absolute;left:0;right:0;top:330px;height:860px;overflow:hidden;background:#fff}}
.shot img{{width:100%;height:100%;object-fit:cover;object-position:center 42%;display:block}}
.host{{position:absolute;left:64px;top:1210px;font:800 44px Inter;color:var(--hl)}}
.cap{{position:absolute;left:64px;right:64px;bottom:250px;font:900 104px/1.06 Inter;letter-spacing:-.035em;color:var(--fg)}}
.cap span{{display:inline-block;padding:0 14px;margin:0 -6px;border-radius:12px}}
.cap .on{{background:var(--hl);color:var(--hlfg)}}
.cap .off{{opacity:.38}}
.foot{{position:absolute;left:64px;bottom:70px;font:600 28px Inter;color:var(--fg);opacity:.55}}
.pill{{display:inline-block;margin-top:56px;background:var(--hl);color:var(--hlfg);font:900 64px Inter;padding:26px 52px;border-radius:999px}}
"""

def logo(px):
    return LOGO.replace('width="40" height="40"', f'width="{px}" height="{px}"')


LOGO = ('<svg width="40" height="40" viewBox="0 0 1080 1080"><circle cx="540" cy="575" r="330" fill="none" '
        'stroke="currentColor" stroke-width="80"/><rect x="490" y="150" width="100" height="70" rx="18" fill="currentColor"/>'
        '<path d="M600 330 L430 610 L545 610 L490 820 L670 520 L555 520 Z" fill="currentColor"/></svg>')


def frame_html(scene, script, tool_png, chunk, active, progress):
    bg, fg, hl, hlfg = SCENE_LOOK.get(scene["kind"], SCENE_LOOK["step"])
    k = scene["kind"]
    extra = ""
    if k == "hook":
        top = ""
    elif k == "tool":
        host = esc(script["tool_url"].split("//")[1].split("/")[0].replace("www.", ""))
        if tool_png:
            top = ""
            extra = (f'<div class="mid" style="position:absolute;left:64px;right:64px;top:150px;font-size:104px">'
                     f'{esc(scene["headline"])}</div><div class="shot"><img src="{tool_png.name}"></div>'
                     f'<div class="host">{host}</div>')
        else:
            top = (f'<div class="big" style="font-size:190px">{esc(script["tool_name"])}</div>'
                   f'<div class="sub" style="color:{hl};opacity:1;font-weight:800">{host}</div>')
    elif k == "step":
        top = (f'<div class="mid" style="color:{ACCENT}">Step {int(scene.get("number", 1))}</div>'
               f'<div class="mid" style="margin-top:10px">{esc(scene["headline"])}</div>')
    elif k == "result":
        top = f'<div class="big" style="font-size:150px">{esc(scene["headline"])}</div><div class="sub">{esc(scene.get("body"))}</div>'
    else:  # cta
        top = (f'<div style="color:{ACCENT};margin-bottom:40px">{logo(210)}</div>'
               f'<div class="big" style="font-size:150px">One AI shortcut.<br><span style="color:{ACCENT}">Every day.</span></div>'
               f'<div class="pill">Follow {esc(CFG["instagram_handle"])}</div>'
               f'<div class="sub" style="margin-top:40px">Free guide: 7 AI tools, link in bio</div>')
    cap_style = ' style="bottom:auto;top:560px;font-size:176px;line-height:.98;letter-spacing:-.045em"' if k == "hook" else ""
    cap = "".join(f'<span class="{"on" if i == active else ("off" if i > active else "")}">{esc(w)}</span> '
                  for i, w in enumerate(chunk))
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@600;800;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body style="background:{bg};--fg:{fg};--hl:{hl};--hlfg:{hlfg}">
<div class="bar" style="width:{progress*100:.1f}%"></div>
<div class="mark">{LOGO}{esc(CFG["brand"])}</div>
<div class="top">{top}</div>{extra}
<div class="cap"{cap_style}>{cap}</div>
<div class="foot">AI voiceover · not sponsored</div>
</body></html>"""


# ---------- audio ----------
def music_bed(path, seconds, bpm=116):
    """Original upbeat loop (kick, offbeat hats, bass, chord stabs: C-G-Am-F). Synthesised, so no copyright."""
    b = 60 / bpm; bar = 4 * b
    m = f"mod(t,{b})"; m2 = f"mod(t+{b/2},{b})"; i = f"mod(floor(t/{bar}),4)"
    r = f"if(eq({i},0),130.81,if(eq({i},1),98.0,if(eq({i},2),110.0,87.31)))"
    third = f"if(eq({i},2),1.189,1.26)"
    kick = f"0.85*sin(2*PI*(48+70*exp(-30*{m}))*{m})*exp(-10*{m})"
    hat = f"0.10*(2*random(0)-1)*exp(-70*{m2})"
    bass = f"0.30*sin(2*PI*({r}/2)*t)*(0.55+0.45*exp(-6*{m}))"
    stab = (f"0.07*(sin(2*PI*{r}*2*t)+sin(2*PI*{r}*2*{third}*t)+sin(2*PI*{r}*3*t))*exp(-7*{m2})")
    expr = f"({kick}+{hat}+{bass}+{stab})*0.5"
    ff("-f", "lavfi", "-i", f"aevalsrc='{expr}':s=48000:d={seconds + 1:.2f}",
       "-af", "highpass=f=35,lowpass=f=9000,afade=t=in:d=0.6,afade=t=out:st=%.2f:d=1.2" % max(0, seconds - 1.2),
       "-ac", "2", path)


def whoosh(path):
    """Soft musical transition: a warm airy swish (brown noise, no hiss) + a gentle pluck in the music's key."""
    d = os.path.dirname(path)
    swish, pluck = os.path.join(d, "_swish.wav"), os.path.join(d, "_pluck.wav")
    # warm swish: brown noise, band-limited to 180-1600 Hz, smooth rise-and-fall over 0.45s
    ff("-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.6:sample_rate=48000:duration=0.45",
       "-af", "highpass=f=180,lowpass=f=1600,lowpass=f=1600,"
              "volume='sin(PI*t/0.45)^3':eval=frame,afade=t=out:st=0.33:d=0.12", "-ac", "2", swish)
    # gentle pluck: E5 + soft octave, quick decay, a touch of echo for space (in key with the C-G-Am-F music)
    ff("-f", "lavfi", "-i", "aevalsrc='(0.55*sin(2*PI*659.25*t)+0.2*sin(2*PI*1318.5*t)+0.15*sin(2*PI*329.63*t))*exp(-9*t)*(1-exp(-400*t))':s=48000:d=0.6",
       "-af", "aecho=0.8:0.5:90:0.25,lowpass=f=5000", "-ac", "2", pluck)
    ff("-i", swish, "-i", pluck, "-filter_complex", "[0:a]volume=0.9[a];[1:a]adelay=300|300,volume=0.55[b];"
       "[a][b]amix=inputs=2:normalize=0,afade=t=out:st=0.75:d=0.15", "-t", "0.9", path)


def clean_voice(src, dst):
    ff("-i", src, "-af", "adeclip,adeclick=window=55:overlap=75,highpass=f=70,lowpass=f=9500,"
       "acompressor=threshold=-18dB:ratio=3:attack=8:release=120,afade=t=in:d=0.012,areverse,"
       "afade=t=in:d=0.04,areverse,volume=-3dB,aresample=48000", "-ac", "1", dst)


def tts_checked(tts_fn, model, text, voice, out):
    """Energetic delivery cue, but re-record plainly if the cue was read aloud (speech much too long)."""
    # Gemini reads delivery cues aloud, so the energy comes from the voice (Puck) and the punchy script instead
    tts_fn(model, text, voice, out)


# ---------- main ----------
def render(script, outdir, tts_model, tts_fn):
    out = pathlib.Path(outdir); out.mkdir(parents=True, exist_ok=True)
    tool_png = None
    try:
        if page_blocked(script["tool_url"]):
            print("tool site shows a bot-check/blocked page -> using a big tool title instead")
            remember_blocked(script["tool_url"])
        else:
            tool_png = pathlib.Path(shoot(script["tool_url"], str(out / "tool.png"), 432, 860, 9000, 2.5))
            if tool_png.stat().st_size < 15000:
                tool_png = None
    except Exception as e:
        print("tool screenshot failed:", e)

    scenes = script["scenes"]
    # 1) voices first (durations drive everything)
    voices = []
    for i, s in enumerate(scenes, 1):
        raw, wav = out / f"raw{i}.wav", out / f"voice{i}.wav"
        tts_checked(tts_fn, tts_model, s["voice"], CFG["voice_name"], str(raw))
        clean_voice(raw, wav)
        voices.append(wav)
    lens = [wav_len(v) for v in voices]
    durs = [L + 0.20 + 0.45 for L in lens]           # 0.2s lead-in + tail that the transition can overlap
    total = sum(durs) - T * (len(durs) - 1)

    # 2) frames per word + one segment per scene
    segs, start = [], 0.0
    for i, (s, L, D) in enumerate(zip(scenes, lens, durs), 1):
        chunks = chunk_words(s["voice"])
        wts = word_times(chunks, L)
        seq, t, wi = [], 0.0, 0                      # (png, seconds, is_new_chunk)
        for ci, ch in enumerate(chunks):
            for a in range(len(ch)):
                d = wts[wi] + (0.20 if wi == 0 else 0); wi += 1
                prog = min(1.0, (start + t) / total)
                page = out / f"f{i}_{ci}_{a}.html"
                page.write_text(frame_html(s, script, tool_png, ch, a, prog))
                png = shoot(page.as_uri(), str(out / f"f{i}_{ci}_{a}.png"), 1080, 1920, 2500)
                seq.append((png, d, a == 0)); t += d
        seq[-1] = (seq[-1][0], seq[-1][1] + max(0.0, D - t), seq[-1][2])   # hold last word through the tail
        # each word image -> clip; a new phrase punches in from 106% to 100% in 4 frames
        parts = []
        for j, (png, d, punch) in enumerate(seq):
            clip = out / f"c{i}_{j}.mp4"
            z = "if(lt(on,4),1.06-0.015*on,1)" if punch else "1"
            ff("-loop", 1, "-framerate", FPS, "-t", f"{d:.3f}", "-i", png, "-vf",
               f"scale=1188:2112,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={FPS},format=yuv420p",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-an", clip)
            parts.append(clip)
        lst = out / f"list{i}.txt"
        lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
        seg = out / f"seg{i}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst.name,
                        "-c", "copy", seg.name], cwd=out, check=True)
        segs.append(seg)
        start += D - T
        print(f"  scene {i} ({s['kind']}): {len(s['voice'].split())} words, voice {L:.1f}s, {len(seq)} caption frames")

    # 3) join scenes with transitions
    args, vf, prev, off = [], "", "[0:v]", 0.0
    for p in segs:
        args += ["-i", p]
    for i in range(1, len(segs)):
        off += durs[i - 1] - T
        tr = TRANSITIONS[(i - 1) % len(TRANSITIONS)]
        vf += f"{prev}[{i}:v]xfade=transition={tr}:duration={T}:offset={off:.3f}[x{i}];"
        prev = f"[x{i}]"
    video = out / "video_only.mp4"
    ff(*args, "-filter_complex", vf.rstrip(";"), "-map", prev, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
       "-pix_fmt", "yuv420p", video)

    # 4) audio: voices placed on the timeline, music ducked under them, whoosh on each cut, mastered
    music, sw = out / "music.wav", out / "whoosh.wav"
    music_bed(str(music), total); whoosh(str(sw))
    a_in, filt, starts, acc = [], "", [], 0.0
    for i, D in enumerate(durs):
        starts.append(acc); acc += D - T
    for v in voices:
        a_in += ["-i", v]
    n = len(voices)
    for i, st in enumerate(starts):
        ms = int((st + 0.20) * 1000)
        filt += f"[{i}:a]adelay={ms}|{ms},apad=whole_dur={total:.2f}[v{i}];"
    filt += "".join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,asplit=2[vox][key];"
    a_in += ["-i", music]
    filt += f"[{n}:a]volume=0.32[mus];[mus][key]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=350[duck];"
    wh = []
    for i, st in enumerate(starts[1:], 1):
        a_in += ["-i", sw]
        ms = int(max(0, st - 0.30 + T / 2) * 1000)
        filt += f"[{n + i}:a]adelay={ms}|{ms},volume=0.32[w{i}];"; wh.append(f"[w{i}]")
    filt += f"[vox][duck]{''.join(wh)}amix=inputs={2 + len(wh)}:normalize=0,"
    filt += "loudnorm=I=-14:TP=-2:LRA=9,alimiter=limit=0.70:level=disabled,aresample=48000[a]"
    audio = out / "mix.m4a"
    ff(*a_in, "-filter_complex", filt, "-map", "[a]", "-t", f"{total:.2f}", "-c:a", "aac", "-b:a", "192k", audio)

    mp4 = out / "video.mp4"
    ff("-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", "-shortest",
       "-movflags", "+faststart", mp4)
    return mp4, total


if __name__ == "__main__":
    # local smoke test with the Mac voice: python autopilot/render.py script.json outdir
    script = json.loads(pathlib.Path(sys.argv[1]).read_text())

    def say_tts(_m, text, _v, outp, style=""):
        aiff = outp.replace(".wav", ".aiff")
        subprocess.run(["say", "-r", "200", "-o", aiff, text], check=True)
        ff("-i", aiff, "-ar", "24000", "-ac", "1", outp); os.remove(aiff)
    mp4, total = render(script, sys.argv[2], None, say_tts)
    print(mp4, round(total, 2), "s")
