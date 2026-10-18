import json,sys
raw=open(sys.argv[1]).read(); i=raw.find("{")
try: d=json.loads(raw[i:])
except Exception: sys.exit(3)
def txt(d):
  r=d.get("result",d)
  p=r.get("payloads") if isinstance(r,dict) else None
  if p: return "\n".join(x.get("text","") for x in p if x.get("text"))
  for k in ("reply","text","output","message"):
    if isinstance(r,dict) and isinstance(r.get(k),str): return r[k]
  return ""
t=txt(d).strip()
if not t: sys.exit(4)
print(t)
