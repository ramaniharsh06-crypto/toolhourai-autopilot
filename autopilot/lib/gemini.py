"""Tiny Gemini REST client (no extra packages): text generation + text-to-speech."""
import base64, json, os, time, urllib.request, urllib.error, wave

API = "https://generativelanguage.googleapis.com/v1beta"


def _key():
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        raise SystemExit("GEMINI_API_KEY is not set")
    return k


def _req(method, path, body=None, retries=4):
    url = f"{API}/{path}"
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"x-goog-api-key": _key(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="ignore")[:500]
            if e.code in (429, 500, 503) and attempt < retries - 1:
                time.sleep(15 * (attempt + 1))
                continue
            raise RuntimeError(f"Gemini {e.code}: {msg}")


def list_models():
    out, token = [], None
    while True:
        r = _req("GET", "models?pageSize=200" + (f"&pageToken={token}" if token else ""))
        out += r.get("models", [])
        token = r.get("nextPageToken")
        if not token:
            return out


def pick_models(text_pref="auto", tts_pref="auto"):
    """Choose the newest 'flash' text model and newest TTS model available on this key."""
    names = [m["name"].split("/", 1)[1] for m in list_models()
             if "generateContent" in m.get("supportedGenerationMethods", [])]

    def newest(cands):
        def ver(n):
            import re
            m = re.search(r"(\d+(?:\.\d+)?)", n)
            return (float(m.group(1)) if m else 0, "preview" not in n, -len(n))
        return sorted(cands, key=ver, reverse=True)[0] if cands else None

    text = text_pref if text_pref != "auto" else newest(
        [n for n in names if "flash" in n and "tts" not in n and "image" not in n
         and "live" not in n and "audio" not in n and "lite" not in n and "exp" not in n])
    tts = tts_pref if tts_pref != "auto" else newest([n for n in names if "tts" in n and "pro" not in n]) \
        or newest([n for n in names if "tts" in n])
    if not text or not tts:
        raise RuntimeError(f"Could not find text/tts models. Available: {names}")
    return text, tts


def generate_json(model, prompt, temperature=0.9):
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"}}
    r = _req("POST", f"models/{model}:generateContent", body)
    txt = r["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(txt)


def tts_to_wav(model, text, voice, out_path, style="Say this in a clear, friendly, upbeat tone, like a helpful creator:"):
    body = {"contents": [{"parts": [{"text": f"{style} {text}"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    r = _req("POST", f"models/{model}:generateContent", body)
    part = r["candidates"][0]["content"]["parts"][0]["inlineData"]
    pcm = base64.b64decode(part["data"])
    rate = 24000
    mt = part.get("mimeType", "")
    if "rate=" in mt:
        rate = int(mt.split("rate=")[1].split(";")[0])
    with wave.open(out_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    return out_path
