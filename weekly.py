"""Weekly grocery run, all from the one shared Reminders list (see RUNBOOK.md).
  python3 weekly.py candidates [--carts FILE]   Likely history matches for each open item, plus this week's suggestions.
  python3 weekly.py queue RESOLVED.json         Turn Claude's matches into fill-queue.json.
  python3 weekly.py done RESULTS.json           Check off what's now in a cart.
The only change this ever makes to the list is checking off items once they're in a cart. It never touches a cart;
the fill is done by the Claude task in Chrome, and the main shopper reviews the carts afterward."""
import json, os, re, subprocess, sys
from collections import defaultdict
from datetime import date, timedelta
import suggest as S
import plan_fill as P
from textmatch import tokens

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.environ.get("GROCERY_QUEUE") or os.path.join(HERE, "fill-queue.json")
LIST = os.environ.get("GROCERY_LIST", "Shopping")  # the household's one shared list
NEW_ORDER = ["ALDI", "Walmart", "Costco"]          # where a first-time item is tried, in order

def rem(cmd, data=None):
    """rem/rem: small EventKit helper (AppleScript takes 90+ s on the big Shopping list)."""
    r = subprocess.run([os.path.join(HERE, "rem", "rem"), cmd, LIST], input=json.dumps(data) if data is not None else "",
                       capture_output=True, text=True, timeout=60)
    if r.returncode: raise RuntimeError(f"rem {cmd}: {r.stderr.strip()}")
    return json.loads(r.stdout or "null")

def read_open():
    r = subprocess.run([os.path.join(HERE, "rem", "rem"), "read", LIST, "--open"], capture_output=True, text=True, timeout=60)
    if r.returncode: raise RuntimeError(f"rem read: {r.stderr.strip()}")
    return json.loads(r.stdout or "[]") or []

def week_of(today):
    """The Thursday this run belongs to (today on a Thursday)."""
    return today + timedelta(days=(3 - today.weekday()) % 7)

def stem(w): return w[:-1] if w.endswith("s") and len(w) > 4 else w

def maybe_same(short, long_tokens):
    """Wide net only: every typed word starts a product word. Claude decides what actually matches
    ("butter" also catches peanut butter and pork butt, so this can't choose on its own)."""
    words = [stem(w) for w in short]
    return bool(words) and all(any(stem(p).startswith(w) or (w.startswith(stem(p)) and len(stem(p)) >= 4) for p in long_tokens) for w in words)

def history_matches(name, rows, today, limit=25):
    t, trips = tokens(name), defaultdict(set)
    for s_, d, n, q, oid in rows:
        if maybe_same(t, tokens(n)): trips[(s_, n)].add(d)
    soon = today - timedelta(days=90)
    out = [{"store": s_, "product": n, "trips_90d": sum(d >= soon for d in ds), "trips_all": len(ds), "last": str(max(ds))}
           for (s_, n), ds in trips.items()]
    return sorted(out, key=lambda c: (-c["trips_90d"], -c["trips_all"]))[:limit]

def usual_store(name, rows, today):
    """For a suggestion's exact product name: store bought from most in the last 90 days, ties to the most recent."""
    t, trips, last = tokens(name), defaultdict(set), {}
    for s_, d, n, q, oid in rows:
        if d >= today - timedelta(days=90) and P.same_item(n, name, None, t):
            trips[s_].add(d); last[s_] = max(last.get(s_, d), d)
    return max(trips, key=lambda s_: (len(trips[s_]), last[s_])) if trips else None

def in_cart_names(path):
    """Cart snapshot (snapshots/carts-*.json) -> {store: [item names]}."""
    if not path: return {}
    snap = json.load(open(path))
    names = lambda xs: [x.rsplit(" x", 1)[0] if isinstance(x, str) else x[0] for x in xs]
    return {s_: names(snap[s_].get("items") or snap[s_].get("first_lines") or []) for s_ in S.STORES if s_ in snap}

def candidates(carts=None):
    today, rows, shop = date.today(), S.load(), read_open()
    cart = in_cart_names(carts)
    seen = [tokens(r["name"]) for r in shop]
    sugg = []
    for p in P.build_picks(today)["picks"]:            # already skips anything on an open order
        t = tokens(p["item"])
        s_ = usual_store(p["item"], rows, today) or p["store"]
        if any(maybe_same(x, t) for x in seen) or any(P.same_item(c, p["item"], None, t) for c in cart.get(s_, [])): continue
        sugg.append({"store": s_, "product": p["item"], "qty": p["qty"]})
    print(json.dumps({"items": [{"id": r["id"], "item": r["name"], "matches": history_matches(r["name"], rows, today)} for r in shop],
                      "suggestions": sugg, "in_carts": cart}, indent=1))

def queue(path):
    """RESOLVED.json = {"items": [{id, item, store, product, qty}], "suggestions": [{store, product, qty}]}.
    store and product are null when nothing in history is really that item."""
    res = json.load(open(path))
    items = [{"reminder": x["id"], "item": x["item"], "store": x.get("store"), "product": x.get("product"), "qty": x.get("qty") or 1,
              "try_order": [x["store"]] if x.get("store") else NEW_ORDER} for x in res["items"]]
    items += [{"reminder": None, "item": x["product"], "store": x["store"], "product": x["product"], "qty": x.get("qty") or 1,
               "try_order": [x["store"]], "suggested": True} for x in res["suggestions"]]
    json.dump({"week": str(week_of(date.today())), "items": items}, open(QUEUE, "w"), indent=1)
    print(f"{len(items)} items queued ({len(res['items'])} from the list, {len(res['suggestions'])} suggested)")

def done(path):
    """RESULTS.json = {"added": [{reminder, ...}], "skipped": [...], "not_found": [...]}. Added or already in a cart
    gets checked off. Not found stays open, so it comes up again next week."""
    res = json.load(open(path))
    ok = [r["reminder"] for r in res.get("added", []) + res.get("skipped", []) if r.get("reminder")]
    if ok: rem("complete", data=ok)
    print(f"checked off {len(ok)}, left {sum(1 for r in res.get('not_found', []) if r.get('reminder'))} open as not found")

if __name__ == "__main__":
    cmd, flags = sys.argv[1], sys.argv[2:]
    if cmd == "candidates": candidates(flags[flags.index("--carts") + 1] if "--carts" in flags else None)
    elif cmd == "queue": queue(flags[0])
    elif cmd == "done": done(flags[0])
