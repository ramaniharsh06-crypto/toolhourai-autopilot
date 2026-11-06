"""Turns a script into a 1080x1920 MP4: real website screenshot + branded scenes + per-scene AI voice."""
import html, json, os, pathlib, shutil, subprocess, wave, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "autopilot/config.json").read_text())
TEMPLATE = (ROOT / "autopilot/templates/scene.html").read_text()


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


def esc(t):
    return html.escape(str(t or ""))


def scene_body(s, tool_png, script):
    k = s["kind"]
    if k == "hook":
        return f'<div class="h">{esc(s["headline"])}</div><div class="s">{esc(s.get("sub"))}</div>'
    if k == "tool":
        img = f'<div class="shot"><img src="{tool_png.name}"></div>' if tool_png else ""
        host = esc(script["tool_url"].split("//")[1].split("/")[0].replace("www.", ""))
        return (f'<div class="h">{esc(s["headline"])}</div><div class="s">{esc(s.get("sub"))}</div>'
                f'{img}<div class="url">{host}</div>')
    if k == "step":
        return (f'<div class="num">{int(s.get("number", 1))}</div><div class="h" style="font-size:80px">'
                f'{esc(s["headline"])}</div><div class="card">{esc(s.get("body"))}</div>')
    if k == "result":
        return (f'<div class="h" style="font-size:80px">✅ {esc(s["headline"])}</div>'
                f'<div class="card res">{esc(s.get("body"))}</div>')
    if k == "cta":
        return (f'<svg width="230" height="230" viewBox="0 0 1080 1080"><circle cx="540" cy="575" r="330" fill="none" '
                f'stroke="#ff7a3d" stroke-width="60"/><rect x="490" y="150" width="100" height="70" rx="18" fill="#ff7a3d"/>'
                f'<path d="M600 330 L430 610 L545 610 L490 820 L670 520 L555 520 Z" fill="#fff"/></svg>'
                f'<div class="h" style="margin-top:50px">1 AI shortcut.<br><em>Every day.</em></div>'
                f'<div class="pill">Follow {esc(CFG["instagram_handle"])}</div>'
                f'<div class="s" style="margin-top:50px">🎁 Free guide: 7 AI tools → link in bio</div>')
    raise ValueError(k)


def wav_len(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def render(script, outdir, tts_model, tts_fn):
    out = pathlib.Path(outdir); out.mkdir(parents=True, exist_ok=True)
    # 1. real screenshot of the tool's public website (phone-sized, crisp)
    tool_png = None
    try:
        tool_png = pathlib.Path(shoot(script["tool_url"], str(out / "tool.png"), 430, 760, 9000, 2.5))
        if tool_png.stat().st_size < 15000:   # blank / blocked page
            tool_png = None
    except Exception as e:
        print("tool screenshot failed:", e)
    # 2. scenes + voice per scene (exact timing)
    parts = []
    for i, s in enumerate(script["scenes"], 1):
        page = out / f"scene{i}.html"
        page.write_text(TEMPLATE.replace("{{BRAND}}", esc(CFG["brand"])).replace("{{HANDLE}}", esc(CFG["instagram_handle"]))
                        .replace("{{BODY}}", scene_body(s, tool_png, script)))
        png = shoot(page.as_uri(), str(out / f"scene{i}.png"), 1080, 1920, 4000)
        wav = out / f"voice{i}.wav"
        tts_fn(tts_model, s["voice"], CFG["voice_name"], str(wav))
        parts.append((png, wav, wav_len(wav) + 0.35))
    # 3. assemble: subtle zoom per scene, audio padded per scene
    args, vf, af = [], "", ""
    for i, (png, wav, d) in enumerate(parts):
        f = int(round(d * 30))
        args += ["-i", png]
        vf += (f"[{i}:v]scale=2160:3840,zoompan=z='1+0.035*on/{f}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
               f"d={f}:s=1080x1920:fps=30,setsar=1,format=yuv420p[v{i}];")
    n = len(parts)
    for i, (png, wav, d) in enumerate(parts):
        args += ["-i", str(wav)]
        af += f"[{n+i}:a]aresample=48000,apad=whole_dur={d:.3f}[a{i}];"
    fc = vf + af + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v];" + \
        "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    mp4 = out / "video.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args, "-filter_complex", fc,
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(mp4)],
                   check=True)
    total = sum(p[2] for p in parts)
    return mp4, total


if __name__ == "__main__":
    # local smoke test: python autopilot/render.py sample_script.json outdir  (uses macOS 'say' instead of Gemini)
    script = json.loads(pathlib.Path(sys.argv[1]).read_text())

    def say_tts(_m, text, _v, outp):
        aiff = outp.replace(".wav", ".aiff")
        subprocess.run(["say", "-o", aiff, text], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", aiff, "-ar", "24000", "-ac", "1", outp], check=True)
        os.remove(aiff)
    mp4, total = render(script, sys.argv[2], None, say_tts)
    print(mp4, round(total, 2), "s")
