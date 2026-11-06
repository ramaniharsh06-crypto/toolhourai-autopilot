"""Tiny Gemini REST client (no extra packages): text generation + text-to-speech."""
import base64, http.client, json, os, socket, time, urllib.request, urllib.error, wave

API = "https://generativelanguage.googleapis.com/v1beta"


def _key():
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        raise SystemExit("GEMINI_API_KEY is not set")
    return k


def _req(method, path, body=None, retries=3):
    url = f"{API}/{path}"
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"x-goog-api-key": _key(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except (TimeoutError, socket.timeout, urllib.error.URLError, http.client.HTTPException, ConnectionError, OSError) as e:
            if isinstance(e, urllib.error.HTTPError):
                raise_http = e
            else:
                if attempt < retries - 1:
                    print(f"Gemini timeout/network error, retrying ({attempt+1})"); time.sleep(10); continue
                raise RuntimeError(f"Gemini network error: {e}")
            e = raise_http
            msg = e.read().decode(errors="ignore")[:500]
            if e.code in (429, 500, 503) and attempt < retries - 1:
                time.sleep(15 * (attempt + 1))
                continue
            raise RuntimeError(f"Gemini {e.code}: {msg}")
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


def _ranked(names, keep):
    import re
    def ver(n):
        m = re.search(r"(\d+(?:\.\d+)?)", n)
        return (float(m.group(1)) if m else 0, "preview" not in n, -len(n))
    return sorted([n for n in names if keep(n)], key=ver, reverse=True)


TEXT_MODELS, TTS_MODELS = [], []


def pick_models(text_pref="auto", tts_pref="auto"):
    """Rank text + TTS models available on this key, newest first; the others are fallbacks."""
    global TEXT_MODELS, TTS_MODELS
    names = [m["name"].split("/", 1)[1] for m in list_models()
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    bad = ("tts", "image", "live", "audio", "exp", "embedding", "robotics", "computer", "thinking", "native")
    TEXT_MODELS = _ranked(names, lambda n: "flash" in n and not any(b in n for b in bad))
    TTS_MODELS = _ranked(names, lambda n: "tts" in n and "pro" not in n) + _ranked(names, lambda n: "tts" in n and "pro" in n)
    if text_pref != "auto":
        TEXT_MODELS.insert(0, text_pref)
    if tts_pref != "auto":
        TTS_MODELS.insert(0, tts_pref)
    if not TEXT_MODELS or not TTS_MODELS:
        raise RuntimeError(f"Could not find text/tts models. Available: {names}")
    return TEXT_MODELS[0], TTS_MODELS[0]


def _with_fallback(models, first, call):
    order = [first] + [m for m in models if m != first]
    last = None
    for m in order[:4]:
        try:
            return call(m)
        except RuntimeError as e:
            last = e
            if any(c in str(e) for c in ("503", "429", "500", "network", "404")):
                print(f"model {m} unavailable ({str(e)[:60]}), trying next")
                continue
            raise
    raise last


def generate_json(model, prompt, temperature=0.9):
    return _with_fallback(TEXT_MODELS, model, lambda m: _generate_json(m, prompt, temperature))


def _generate_json(model, prompt, temperature):
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json",
                                 "thinkingConfig": {"thinkingLevel": "low"}}}
    try:
        r = _req("POST", f"models/{model}:generateContent", body)
    except RuntimeError as e:
        if "400" not in str(e):
            raise
        body["generationConfig"].pop("thinkingConfig")   # model doesn't support it
        r = _req("POST", f"models/{model}:generateContent", body)
    txt = r["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(txt)


def tts_to_wav(model, text, voice, out_path, style=""):
    return _with_fallback(TTS_MODELS, model, lambda m: _tts(m, text, voice, out_path, style))


def _tts(model, text, voice, out_path, style):
    body = {"contents": [{"parts": [{"text": (f"{style} {text}" if style else text)}]}],
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
