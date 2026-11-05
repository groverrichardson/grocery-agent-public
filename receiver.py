"""Tiny local listener: the Chrome page POSTs parsed orders here; we append them to history.jsonl.
Read-only toward the stores. Dedupe by (source, order_id)."""
import json, os, time
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(HERE, "history.jsonl")
OPEN = os.path.join(HERE, "open.json")
RUNLOG = os.path.join(HERE, "runlog.jsonl")

def known():
    ids = set()
    if os.path.exists(HIST):
        for line in open(HIST):
            o = json.loads(line)
            ids.add((o["source"], o["order_id"]))
    return ids

# Helper window for sites whose page rules block talking to this Mac (Walmart).
# The store tab opens this window and sends it messages; it forwards them here.
RELAY = """<!doctype html><title>grocery relay</title><body>Grocery relay: leave open during the run.<script>
const OK=['https://www.walmart.com','https://www.instacart.com'];
addEventListener('message', async e=>{ if(!OK.includes(e.origin)) return;
  const {id,method,path,body}=e.data;
  try{ const r=await fetch(path,{method:method||'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
       e.source.postMessage({id,ok:true,data:await r.json()}, e.origin);}
  catch(err){ e.source.postMessage({id,ok:false,error:String(err)}, e.origin);} });
</script>"""

class H(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ("https://www.instacart.com", "https://www.walmart.com"):
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code); self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path.startswith("/relay"):
            body = RELAY.encode()
            self.send_response(200); self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            return self.wfile.write(body)
        if self.path.startswith("/js/"):  # collector source, so each run uses the saved file, not a hand-pasted copy
            name = os.path.basename(self.path[4:]) + ".js"
            return self._json(200, {"code": open(os.path.join(HERE, "collectors", name)).read()})
        if self.path.startswith("/saved?"):  # one saved order, for spot-checks against the live site
            src, oid = unquote(self.path.split("?", 1)[1]).split(":", 1)
            for line in open(HIST):
                o = json.loads(line)
                if o["source"] == src and o["order_id"] == oid:
                    return self._json(200, o)
            return self._json(404, {})
        if self.path.startswith("/openids"):
            src = self.path.split("source=")[-1]
            cur = json.load(open(OPEN)) if os.path.exists(OPEN) else {}
            return self._json(200, sorted({i.get("order_id") for i in cur.get(src, {}).get("items", []) if i.get("order_id")}))
        if self.path.startswith("/known"):
            src = self.path.split("source=")[-1]
            return self._json(200, sorted(i for s, i in known() if s == src))
        self._json(404, {})

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/order":
            key = (data["source"], data["order_id"])
            if key in known():
                return self._json(200, {"saved": False, "dup": True})
            raw = data.pop("raw", None)
            if raw:
                open(os.path.join(HERE, "raw", f'{data["source"]}_{data["order_id"]}.txt'), "w").write(raw)
            data["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            with open(HIST, "a") as f:
                f.write(json.dumps(data) + "\n")
            return self._json(200, {"saved": True})
        if self.path == "/open":
            cur = json.load(open(OPEN)) if os.path.exists(OPEN) else {}
            cur[data["source"]] = data
            json.dump(cur, open(OPEN, "w"), indent=1)
            return self._json(200, {"saved": True})
        if self.path == "/log":
            data["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            open(RUNLOG, "a").write(json.dumps(data) + "\n")
            return self._json(200, {"ok": True})
        self._json(404, {})

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
