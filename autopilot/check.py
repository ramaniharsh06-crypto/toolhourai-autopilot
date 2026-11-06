"""Connection check: proves both API keys work and shows what Buffer expects. Posts nothing."""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lib import gemini, buffer  # noqa: E402

ok = True
try:
    t, s = gemini.pick_models()
    print("✅ Gemini key works. text model:", t, "| voice model:", s)
except Exception as e:
    ok = False; print("❌ Gemini:", e)

try:
    org = buffer.organization_id()
    chans = buffer.channels(org)
    print("✅ Buffer key works. channels:", [(c["service"], c["name"], "disconnected" if c.get("isDisconnected") else "ok") for c in chans])
    for type_name in ("PostType", "YoutubePrivacy", "ShareMode", "SchedulingType", "YoutubeLicense"):
        d = buffer.gql('query($n:String!){ __type(name:$n){ name inputFields{ name type{ name kind ofType{ name kind } } } enumValues{ name } } }', {"n": type_name})
        tt = d["__type"]
        if tt:
            print(f"   {type_name}:", [e['name'] for e in (tt.get('enumValues') or [])])
except Exception as e:
    ok = False; print("❌ Buffer:", e)

sys.exit(0 if ok else 1)
