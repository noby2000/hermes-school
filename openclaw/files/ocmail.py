#!/usr/bin/env python3
"""oc-mail server side. Usage: ocmail.py ME CMD ...
  ME send --to owner|guest --from NAME --subject S   (body on stdin)
  ME inbox [--all] | ME read ID | ME reply ID --from NAME  (body on stdin)"""
import sys, os, json, re, time, secrets, base64
ROOT = os.path.expanduser("~/oc-mail"); SIDES = ("owner", "guest"); MAXB = 100 * 1024
def die(m, c=2): print("oc-mail: " + m, file=sys.stderr); sys.exit(c)
NAME = re.compile(r"^[A-Za-z0-9 ._@-]{1,64}$"); ID = re.compile(r"^m-\d{8}-\d{6}-[0-9a-f]{6}$")
def body():
    b = sys.stdin.buffer.read(MAXB + 1)
    if len(b) > MAXB: die("body over 100KB")
    t = b.decode("utf-8", "replace")
    if not t.strip(): die("empty body")
    return t
def opts(a, allowed):
    o = {}
    while a:
        k = a.pop(0)
        if k not in allowed or not a: die("bad option " + k[:20])
        o[k] = a.pop(0)
    return o
def save(to, frm, side, subj, text, reply_to=None):
    if not NAME.match(frm): die("bad --from")
    subj = subj.replace("\n", " ").strip()[:200] or "(no subject)"
    mid = "m-" + time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + "-" + secrets.token_hex(3)
    d = os.path.join(ROOT, to); os.makedirs(d, exist_ok=True)
    m = dict(id=mid, time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), from_side=side, to=to,
             **{"from": frm}, subject=subj, reply_to=reply_to, read=False, body=text)
    tmp = os.path.join(d, "." + mid); json.dump(m, open(tmp, "w"), ensure_ascii=False, indent=1); os.rename(tmp, os.path.join(d, mid + ".json"))
    print(mid)
def load(me, mid):
    if not ID.match(mid): die("bad id")
    p = os.path.join(ROOT, me, mid + ".json")
    if not os.path.isfile(p): die("no such message")
    return p, json.load(open(p))
a = sys.argv[1:]
if len(a) < 2 or a[0] not in SIDES: die(__doc__)
me, cmd, a = a[0], a[1], a[2:]
other = "guest" if me == "owner" else "owner"
for s in SIDES: os.makedirs(os.path.join(ROOT, s), exist_ok=True)
if cmd == "send":
    o = opts(a, ("--to", "--from", "--subject", "--subject-b64"))
    if "--subject-b64" in o:
        try: o["--subject"] = base64.b64decode(o["--subject-b64"], validate=True).decode("utf-8", "replace")
        except Exception: die("bad --subject-b64")
    to = o.get("--to", other)
    if to not in SIDES: die("bad --to")
    if me == "guest" and to != "owner": die("guest side may only send to owner")
    save(to, o.get("--from", me), me, o.get("--subject", ""), body())
elif cmd == "inbox":
    allm = a == ["--all"]
    if a and not allm: die("bad args")
    d = os.path.join(ROOT, me); n = 0
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"): continue
        m = json.load(open(os.path.join(d, f)))
        if m.get("read") and not allm: continue
        n += 1; print(f'{m["id"]}\t{m["time"]}\t{m["from"]}\t{"" if not m.get("read") else "[read] "}{m["subject"]}')
    if not n: print("(no unread messages)")
elif cmd == "read":
    if len(a) != 1: die("usage: read ID")
    p, m = load(me, a[0]); m["read"] = True; json.dump(m, open(p, "w"), ensure_ascii=False, indent=1)
    print(f'id: {m["id"]}\ntime: {m["time"]}\nfrom: {m["from"]} ({m["from_side"]})\nsubject: {m["subject"]}\nreply_to: {m["reply_to"]}\n\n{m["body"]}')
elif cmd == "reply":
    if not a: die("usage: reply ID --from NAME")
    mid = a.pop(0); o = opts(a, ("--from",)); p, m = load(me, mid)
    s = m["subject"]; s = s if s.startswith("Re: ") else "Re: " + s
    save(m["from_side"], o.get("--from", me), me, s, body(), reply_to=mid)
else: die("unknown command")
