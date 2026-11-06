"""Real-life visual examples for each scene, animated in sync with the voice.

The scriptwriter gives each scene a "visual" like {"type": "email", "data": {...}}. Each frame is drawn with
p = how far through the scene's voice we are (0..1), so text types out, rows fill, replies stream in.
These are generic, unbranded app windows (no real logos) filled with realistic sample data.
"""
import html, math

INK, ACCENT, GREEN, BLUE = "#101014", "#ff7a3d", "#1f7a4d", "#2f6fe0"


def esc(t):
    return html.escape(str(t if t is not None else ""))


def typed(text, p, start=0.0, end=1.0):
    """Portion of text typed by progress p (between start and end of the scene)."""
    text = str(text or "")
    q = 0 if p <= start else 1 if p >= end else (p - start) / (end - start)
    n = math.ceil(len(text) * q)
    cur = '<span class="cur"></span>' if 0 < q < 1 else ""
    return esc(text[:n]) + cur


def reveal(items, p, start=0.0, end=1.0):
    q = 0 if p <= start else 1 if p >= end else (p - start) / (end - start)
    return items[:max(1 if q > 0 else 0, math.ceil(len(items) * q))]


CSS = """
.win{position:absolute;left:56px;right:56px;top:330px;height:900px;background:#fff;border-radius:28px;overflow:hidden;color:#16161a;font-family:Inter,sans-serif}
.win.short{height:760px}
.bar{height:74px;background:#f1f1f4;display:flex;align-items:center;gap:12px;padding:0 26px;font:700 28px Inter;color:#55555f}
.dot{width:20px;height:20px;border-radius:50%;background:#ff5f57}.dot:nth-child(2){background:#febc2e}.dot:nth-child(3){background:#28c840}
.bar b{margin-left:16px}
.pad{padding:34px 40px}
.cur{display:inline-block;width:4px;height:1em;background:#ff7a3d;vertical-align:-3px;margin-left:2px}
.row{display:flex;gap:18px;font:600 30px Inter;color:#6b6b76;padding:14px 0;border-bottom:2px solid #efeff2}
.row span{color:#16161a;font-weight:700}
.body{font:500 34px/1.45 Inter;margin-top:26px;white-space:pre-wrap}
.ai{display:inline-block;background:#ff7a3d;color:#fff;font:800 24px Inter;border-radius:10px;padding:6px 14px;margin-bottom:16px}
.btn{display:inline-block;margin-top:26px;background:#2f6fe0;color:#fff;font:800 30px Inter;border-radius:12px;padding:14px 30px}
.grid{border-collapse:collapse;width:100%;font:600 27px Inter}
.grid td,.grid th{border:2px solid #e3e3e8;padding:14px 14px;text-align:left;white-space:nowrap;overflow:hidden;max-width:300px}
.grid th{background:#f6f6f8;color:#8a8a94;font-weight:700;text-align:center}
.grid tr.h td{background:#e8f3ec;font-weight:800}
.grid td.hl{background:#fff2ea;color:#c2511c;font-weight:800}
.fx{display:flex;gap:16px;align-items:center;padding:14px 26px;font:600 28px Inter;border-bottom:2px solid #e3e3e8}
.fx i{font-style:normal;font-weight:800;color:#1f7a4d}
.msg{max-width:84%;padding:24px 28px;border-radius:26px;font:500 33px/1.4 Inter;margin:18px 0;white-space:pre-wrap}
.me{margin-left:auto;background:#2f6fe0;color:#fff;border-bottom-right-radius:8px}
.bot{background:#f1f1f4;border-bottom-left-radius:8px}
.who{font:800 24px Inter;color:#8a8a94;margin-bottom:8px}
.slide{position:absolute;left:40px;right:40px;top:110px;bottom:40px;background:#16161a;color:#fff;border-radius:18px;padding:50px}
.slide h2{font:900 64px/1.05 Inter;letter-spacing:-.03em}
.slide li{font:600 38px/1.4 Inter;margin-top:18px;list-style:none}
.slide li:before{content:"";display:inline-block;width:16px;height:16px;background:#ff7a3d;margin-right:20px;vertical-align:4px}
.cal{display:grid;grid-template-columns:90px repeat(5,1fr);font:700 24px Inter}
.cal div{border:1px solid #ececf0;height:92px;padding:8px}
.cal .d{height:56px;background:#f6f6f8;text-align:center;color:#8a8a94}
.ev{background:#2f6fe0;color:#fff;border-radius:10px;padding:8px;font:700 22px/1.2 Inter;height:100%}
.ev.n{background:#ff7a3d}
.q{border:3px solid #dadae0;border-radius:999px;padding:20px 30px;font:600 34px Inter}
.res{margin-top:30px}.res h4{font:700 32px Inter;color:#1a4fd0}.res p{font:500 28px/1.4 Inter;color:#55555f;margin:6px 0 26px}
.chk{font:600 36px/1.5 Inter;padding:12px 0;display:flex;gap:20px;align-items:center}
.box{width:44px;height:44px;border:4px solid #c8c8d0;border-radius:10px;flex:none}
.box.on{background:#1f7a4d;border-color:#1f7a4d;position:relative}
.box.on:after{content:"";position:absolute;left:11px;top:3px;width:12px;height:24px;border:solid #fff;border-width:0 6px 6px 0;transform:rotate(45deg)}
.inv td{font:600 30px Inter;padding:14px 4px;border-bottom:2px solid #efeff2}
.big{font:900 96px Inter;letter-spacing:-.03em}
.post{display:flex;gap:18px;align-items:center;font:800 30px Inter}
.av{width:70px;height:70px;border-radius:50%;background:#ff7a3d}
.stat{display:flex;gap:40px;margin-top:20px;font:700 30px Inter;color:#55555f}
.inbox .m{display:flex;justify-content:space-between;padding:18px 0;border-bottom:2px solid #efeff2;font:600 30px Inter}
.inbox .m.u{font-weight:800}
.badge{background:#e5484d;color:#fff;border-radius:999px;padding:4px 16px;font:800 26px Inter}
"""


def window(app, inner, short=False):
    return (f'<div class="win{" short" if short else ""}"><div class="bar"><i class="dot"></i><i class="dot"></i>'
            f'<i class="dot"></i><b>{esc(app)}</b><span style="margin-left:auto;font:600 24px Inter;color:#9a9aa4">example</span></div>{inner}</div>')


def email(d, p):
    ai = '<div class="ai">AI draft</div>' if d.get("ai_written", True) else ""
    inner = (f'<div class="pad"><div class="row">To <span>{esc(d.get("to"))}</span></div>'
             f'<div class="row">Subject <span>{typed(d.get("subject"), p, 0, .25)}</span></div>'
             f'<div class="body">{ai}{typed(d.get("body"), p, .2, .95)}</div>'
             f'{"<div class=btn>Send</div>" if p > .9 else ""}</div>')
    return window("Mail", inner)


def inbox(d, p):
    items = d.get("emails") or []
    rows = "".join(f'<div class="m {"u" if e.get("unread", True) else ""}"><span>{esc(e.get("from"))}</span>'
                   f'<span style="color:#6b6b76;font-weight:500">{esc(e.get("subject"))}</span></div>'
                   for e in reveal(items, p, 0, .6))
    inner = (f'<div class="pad"><div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">'
             f'<div style="font:900 40px/1.3 Inter">Inbox</div><span class="badge">{esc(d.get("unread_count", len(items)))} unread</span></div>'
             f'<div class="inbox" style="margin-top:20px">{rows}</div></div>')
    return window("Mail", inner)


def spreadsheet(d, p):
    cols = d.get("columns") or []
    rows = d.get("rows") or []
    hl = d.get("highlight_column")
    shown = reveal(rows, p, .1, .85)
    letters = "".join(f"<th>{chr(65+i)}</th>" for i in range(len(cols)))
    head = "<tr class=h><td style='background:#f6f6f8;color:#8a8a94'>1</td>" + "".join(f"<td>{esc(c)}</td>" for c in cols) + "</tr>"
    body = ""
    for r_i, r in enumerate(shown, 2):
        cells = ""
        for c_i, v in enumerate(r[:len(cols)]):
            cls = ' class="hl"' if hl is not None and (c_i == hl or (isinstance(hl, str) and cols[c_i] == hl)) else ""
            cells += f"<td{cls}>{esc(v)}</td>"
        body += f"<tr><td style='background:#f6f6f8;color:#8a8a94;text-align:center'>{r_i}</td>{cells}</tr>"
    fx = d.get("formula") or ""
    inner = (f'<div class="fx"><i>fx</i>{typed(fx, p, 0, .3) if fx else ""}</div>'
             f'<div style="padding:0 0 0 0"><table class="grid"><tr><th></th>{letters}</tr>{head}{body}</table></div>'
             + (f'<div class="pad" style="font:800 34px Inter;color:#1f7a4d">{typed(d.get("result_note"), p, .8, 1)}</div>'
                if d.get("result_note") else ""))
    return window(d.get("title") or "Spreadsheet", inner)


def chat(d, p):
    inner = (f'<div class="pad"><div class="who" style="text-align:right">You</div>'
             f'<div class="msg me">{typed(d.get("user"), p, 0, .35)}</div>'
             + (f'<div class="who">{esc(d.get("assistant_name") or "AI")}</div><div class="msg bot">{typed(d.get("ai"), p, .38, .98)}</div>'
                if p > .36 else "") + "</div>")
    return window(d.get("app") or "AI chat", inner)


def document(d, p):
    paras = d.get("paragraphs") or [d.get("text", "")]
    joined = "\n\n".join(paras)
    inner = (f'<div class="pad"><div style="font:900 50px/1.1 Inter;letter-spacing:-.02em">{esc(d.get("title"))}</div>'
             f'<div class="body">{typed(joined, p, .1, .95)}</div></div>')
    return window("Document", inner)


def slides(d, p):
    bullets = d.get("bullets") or []
    li = "".join(f"<li>{esc(b)}</li>" for b in reveal(bullets, p, .25, .9))
    inner = f'<div class="slide"><h2>{typed(d.get("title"), p, 0, .25)}</h2><ul style="padding:0;margin-top:30px">{li}</ul></div>'
    return window("Slides", inner, short=True)


def calendar(d, p):
    days = d.get("days") or ["Mon", "Tue", "Wed", "Thu", "Fri"]
    hours = d.get("hours") or ["9", "10", "11", "12", "1", "2", "3"]
    evs = reveal(d.get("events") or [], p, .1, .9)
    cells = "<div class='d'></div>" + "".join(f"<div class='d'>{esc(x)}</div>" for x in days[:5])
    for h_i, h in enumerate(hours[:7]):
        cells += f"<div style='color:#8a8a94'>{esc(h)}</div>"
        for d_i in range(5):
            e = next((e for e in evs if int(e.get("day", 0)) == d_i and int(e.get("slot", 0)) == h_i), None)
            cells += (f"<div><div class='ev {'n' if e.get('new') else ''}'>{esc(e.get('title'))}</div></div>" if e else "<div></div>")
    return window("Calendar", f'<div class="pad"><div class="cal">{cells}</div></div>')


def search(d, p):
    res = reveal(d.get("results") or [], p, .35, .95)
    out = "".join(f'<h4>{esc(r.get("title"))}</h4><p>{esc(r.get("snippet"))}</p>' for r in res)
    inner = f'<div class="pad"><div class="q">{typed(d.get("query"), p, 0, .3)}</div><div class="res">{out}</div></div>'
    return window(d.get("app") or "Search", inner)


def checklist(d, p):
    items = d.get("items") or []
    done_upto = math.ceil(len(items) * min(1, max(0, (p - .15) / .8)))
    rows = "".join(f'<div class="chk"><i class="box {"on" if i < done_upto else ""}"></i>{esc(t)}</div>' for i, t in enumerate(items))
    return window(d.get("title") or "To-do", f'<div class="pad">{rows}</div>')


def invoice(d, p):
    items = reveal(d.get("items") or [], p, .1, .7)
    rows = "".join(f"<tr><td>{esc(i.get('name'))}</td><td style='text-align:right'>{esc(i.get('amount'))}</td></tr>" for i in items)
    inner = (f'<div class="pad"><div style="font:900 56px Inter">Invoice {esc(d.get("number", "#104"))}</div>'
             f'<div class="row">Client <span>{esc(d.get("client"))}</span></div>'
             f'<table class="inv" style="width:100%;margin-top:20px">{rows}</table>'
             + (f'<div style="margin-top:30px;font:900 52px Inter">Total {esc(d.get("total"))}</div>' if p > .75 else "") + "</div>")
    return window("Invoice", inner)


def social(d, p):
    inner = (f'<div class="pad"><div class="post"><i class="av"></i>{esc(d.get("account", "yourbusiness"))}</div>'
             f'<div class="body">{typed(d.get("caption"), p, .05, .8)}</div>'
             f'<div class="stat"><span>♥ {esc(d.get("likes", ""))}</span><span>💬 {esc(d.get("comments", ""))}</span></div></div>')
    return window("Social post", inner)


def stat(d, p):
    q = min(1, max(0, (p - .1) / .7))
    before, after = d.get("before", ""), d.get("after", "")
    inner = (f'<div class="pad" style="display:flex;flex-direction:column;gap:50px;justify-content:center;height:780px">'
             f'<div><div style="font:700 36px Inter;color:#8a8a94">{esc(d.get("before_label", "Before"))}</div>'
             f'<div class="big" style="color:#e5484d">{esc(before)}</div></div>'
             + (f'<div><div style="font:700 36px Inter;color:#8a8a94">{esc(d.get("after_label", "After"))}</div>'
                f'<div class="big" style="color:#1f7a4d">{esc(after)}</div></div>' if q > .4 else "") + "</div>")
    return window(d.get("title") or "Time spent", inner)


KINDS = {"email": email, "inbox": inbox, "spreadsheet": spreadsheet, "chat": chat, "document": document,
         "slides": slides, "calendar": calendar, "search": search, "checklist": checklist, "invoice": invoice,
         "social": social, "stat": stat}


PHONE_KINDS = {"chat", "social", "inbox", "checklist"}

DEVICE_CSS = """
.laptop{position:absolute;left:74px;right:74px;top:370px;transform:scale(.94);transform-origin:50% 0}
.lid{position:relative;background:#1b1b1d;border:3px solid #3b3b3f;border-radius:30px 30px 6px 6px;padding:26px 24px 24px}
.cam{position:absolute;top:9px;left:50%;margin-left:-5px;width:10px;height:10px;border-radius:50%;background:#33343a}
.screen{position:relative;width:938px;height:588px;overflow:hidden;background:#eef0f4;border-radius:4px}
.menubar{position:absolute;left:0;right:0;top:0;height:30px;background:#f5f5f7;display:flex;align-items:center;gap:22px;padding:0 16px;font:700 17px Inter;color:#222;z-index:2}
.menubar .r{margin-left:auto;font-weight:600}
.screen .win{position:absolute;left:0;top:30px;width:1054px;height:627px;transform:scale(.89);transform-origin:0 0;border-radius:0}
.base{position:relative;height:30px;margin:0 -44px;background:#c9cad0;border-radius:2px 2px 26px 26px;border-top:2px solid #e2e3e8}
.base:after{content:"";position:absolute;left:50%;top:0;width:150px;margin-left:-75px;height:11px;background:#aeb0b7;border-radius:0 0 12px 12px}
.ptr{position:absolute;width:34px;height:34px;z-index:5}
.click{position:absolute;width:56px;height:56px;margin:-28px 0 0 -28px;border-radius:50%;border:5px solid #ff7a3d;z-index:4}
.phone{position:absolute;left:50%;margin-left:-285px;top:300px;width:570px;height:1150px;background:#121214;border:4px solid #3b3b3f;border-radius:88px;padding:18px}
.pscreen{position:relative;width:100%;height:100%;border-radius:70px;overflow:hidden;background:#fff}
.island{position:absolute;top:18px;left:50%;margin-left:-76px;width:152px;height:44px;background:#000;border-radius:24px;z-index:3}
.status{position:absolute;left:0;right:0;top:0;height:78px;display:flex;justify-content:space-between;align-items:center;padding:6px 44px 0;font:800 25px Inter;color:#111;z-index:2}
.pscreen .win{position:absolute;left:0;right:0;top:78px;bottom:0;width:auto;height:auto;border-radius:0}
.pscreen .bar{height:62px;font-size:27px;background:#fff;border-bottom:2px solid #eee}
.pscreen .dot{display:none}
.pscreen .bar b{margin-left:0}
.pscreen .pad{padding:26px 28px}
.pscreen .msg{font-size:30px;max-width:90%}
"""

POINTER = ('<svg class="ptr" style="left:{x}px;top:{y}px" viewBox="0 0 24 24"><path d="M3 2 L3 20 L8 15.5 L11.5 22 '
           'L14.5 20.6 L11 14 L18 14 Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>')
TARGETS = {"email": (150, 520), "spreadsheet": (640, 150), "slides": (470, 330), "document": (470, 420),
           "calendar": (560, 300), "search": (470, 120), "invoice": (700, 520), "stat": (470, 470)}


def laptop(inner, kind, p, clock="10:24"):
    tx, ty = TARGETS.get(kind, (470, 330))
    q = min(1.0, p * 1.15)
    x, y = 820 + (tx - 820) * q, 520 + (ty - 520) * q
    click = f'<div class="click" style="left:{tx}px;top:{ty}px"></div>' if p > .9 else ""
    return (f'<div class="laptop"><div class="lid"><i class="cam"></i><div class="screen">'
            f'<div class="menubar"><b>{esc(kind.title() if kind != "stat" else "Report")}</b><span>File</span><span>Edit</span>'
            f'<span>View</span><span class="r">Thu {clock}</span></div>{inner}{click}{POINTER.format(x=x, y=y)}'
            f'</div></div><div class="base"></div></div>')


def phone(inner, clock="10:24"):
    return (f'<div class="phone"><div class="pscreen"><i class="island"></i>'
            f'<div class="status"><span>{clock}</span><span>5G ▮▮▮</span></div>{inner}</div></div>')


def render_visual(v, p):
    """HTML for one visual at progress p, shown on a realistic laptop or phone, or '' if none/unknown."""
    if not v or v.get("type") not in KINDS:
        return ""
    kind = v["type"]
    try:
        inner = KINDS[kind](v.get("data") or {}, p)
    except Exception as e:
        print("visual skipped:", kind, e)
        return ""
    device = (v.get("data") or {}).get("device") or v.get("device") or ("phone" if kind in PHONE_KINDS else "laptop")
    return phone(inner) if device == "phone" else laptop(inner, kind, p)


CSS = CSS + DEVICE_CSS

SCHEMA_HELP = """Each scene (except "cta") gets a "visual": a REAL-LIFE example of exactly what the voice is talking about
in that moment, so viewers SEE it, not just read captions. Pick the type that matches what is being said:
- "email":       {"to":"", "subject":"", "body":"the actual email text", "ai_written":true}
- "inbox":       {"unread_count":47, "emails":[{"from":"","subject":"","unread":true}]}   (4-6 emails)
- "spreadsheet": {"title":"Sales.xlsx", "columns":["Month","Sales","Leads"], "rows":[["Jan","4,200","38"]], "formula":"=AVERAGE(B2:B7)", "highlight_column":1, "result_note":"Best month: March"}   (4-6 rows, 2-4 columns)
- "chat":        {"app":"<tool name>", "user":"the exact prompt you type", "ai":"the tool's answer, realistic and short"}
- "document":    {"title":"", "paragraphs":["",""]}
- "slides":      {"title":"", "bullets":["","",""]}
- "calendar":    {"events":[{"day":0-4,"slot":0-6,"title":"","new":false}]}
- "search":      {"app":"<tool name>", "query":"", "results":[{"title":"","snippet":""}]}   (2-3 results)
- "checklist":   {"title":"", "items":["","","",""]}
- "invoice":     {"client":"", "number":"#104", "items":[{"name":"","amount":""}], "total":""}
- "social":      {"account":"", "caption":"", "likes":"", "comments":""}
- "stat":        {"title":"Time spent", "before_label":"By hand", "before":"3 hours", "after_label":"With AI", "after":"10 min"}
Use believable sample data for a small business (a bakery, salon, agency, shop, consultant...). Keep text short
enough to read on a phone. For the "tool" scene use {"type":"none"} (the real website is shown). Never use real
people's names or real company data. Visuals are shown on a realistic laptop (email, spreadsheet, document,
slides, calendar, search, invoice, stat) or phone (chat, social, inbox, checklist); add "device":"phone" or
"device":"laptop" inside data to override."""
