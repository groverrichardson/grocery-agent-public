"""Dry-run fill plan. Step 1 (this file, offline): pick this week's Likely items, give each one store, and skip
anything already in a cart. Step 2 (in Chrome, collectors/find_instacart.js and find_walmart.js): look up the exact past product.
Step 3 (this file, --write): turn the lookups into fill-plan.md. Nothing here ever adds to or changes a cart."""
import json, os, sys
from collections import defaultdict
from datetime import date
import suggest as S
from textmatch import tokens, jacc

HERE = os.path.dirname(os.path.abspath(__file__))
PICKS = os.path.join(HERE, "fill-picks.json")
FOUND = os.path.join(HERE, "fill-found.json")
CART_STORE = {"ALDI": "cart_instacart", "Costco": "cart_instacart", "Walmart": "cart_walmart"}

def same_item(a, b, ta=None, tb=None):
    ta = tokens(a) if ta is None else ta; tb = tokens(b) if tb is None else tb
    return jacc(ta, tb) >= 0.5 or (ta and ta <= tb) or (tb and tb <= ta)

def build_picks(asof):
    due, rows, label, _ = S.due_for(asof)
    times = defaultdict(int)                       # how often each item was bought at each store
    for s_, d, n, q, oid in rows: times[(s_, label[(s_, n)])] += 1
    toks = {k: tokens(k[1]) for k in times}
    carts = json.load(open(os.path.join(HERE, "open.json")))
    picks, skipped = [], []
    for s_, items in due["likely"].items():
        for lab, v in items:
            tl = tokens(lab)
            others = [(o, times[(o, l)]) for (o, l) in times if o != s_ and same_item(l, lab, toks[(o, l)], tl)]
            best = max(others, key=lambda x: x[1], default=(None, 0))
            if best[1] > times[(s_, lab)]:
                skipped.append({"store": s_, "item": lab, "why": f"usually bought at {best[0]} instead"}); continue
            in_cart = [c for c in carts.get(CART_STORE[s_], {}).get("items", [])
                       if (CART_STORE[s_] != "cart_instacart" or c.get("store") == s_) and same_item(c["name"], lab)]
            if in_cart:
                skipped.append({"store": s_, "item": lab, "why": f"already in the cart as \"{in_cart[0]['name']}\""}); continue
            picks.append({"store": s_, "item": lab, "qty": max(1, round(v["qty"])), "chance": round(v["chance"], 2),
                          "reason": S.reason(v)})
    maybe = [{"store": s_, "item": lab, "chance": round(v["chance"], 2)} for s_, items in due["maybe"].items() for lab, v in items]
    out = {"asof": str(asof), "picks": picks, "skipped": skipped, "maybe": maybe, "notes": due["notes"],
           "carts": {k: carts.get(k, {}).get("counts", "") for k in ("cart_instacart", "cart_walmart")}}
    json.dump(out, open(PICKS, "w"), indent=1)
    return out

def write_plan():
    """Turn fill-picks.json + fill-found.json into fill-plan.md. Every pick ends up either matched or 'not found' with a reason."""
    o = json.load(open(PICKS)); found = {(f["store"], f["item"]): f for f in json.load(open(FOUND))["found"]}
    L = [f"# Fill plan (dry run) — {o['asof']}", "",
         "Nothing has been added to any cart. Approve this and a later step can add it. The family's own cart items are never touched.",
         f"Carts when read: Instacart Family Carts {o['carts'].get('cart_instacart') or '(none)'}; Walmart {o['carts'].get('cart_walmart') or '(not read)'}.", ""]
    if o["notes"]: L += ["Your feedback was used:"] + [f"- {n}" for n in o["notes"]] + [""]
    missing = 0
    for s_ in S.STORES:
        ps = [p for p in o["picks"] if p["store"] == s_]; sk = [k for k in o["skipped"] if k["store"] == s_]
        if not ps and not sk: continue
        L.append(f"## {s_}" + (" (Instacart Family Cart)" if s_ in ("ALDI", "Costco") else " (walmart.com cart)"))
        L.append("### Would add")
        if not ps: L.append("Nothing.")
        for i, p in enumerate(ps, 1):
            f = found.get((s_, p["item"]))
            if f: L.append(f"{i}. {f['product']} x{p['qty']}, {f['price']}, {f['stock']}. Why: {p['reason']}. [product]({f['link']})")
            else: missing += 1; L.append(f"{i}. {p['item']} x{p['qty']}: NOT FOUND on the store site. Why it's here: {p['reason']}")
        if sk:
            L.append("### Skipped")
            for k in sk: L.append(f"- {k['item']}: {k['why']}")
        L.append("")
    L.append(f"Maybe list for the main shopper: {len(o['maybe'])} items, in the shared doc (see link in chat).")
    open(os.path.join(HERE, "fill-plan.md"), "w").write("\n".join(L))
    return missing

if __name__ == "__main__":
    if "--write" in sys.argv:
        print("not found:", write_plan()); sys.exit()
    asof = date.fromisoformat(sys.argv[sys.argv.index("--asof") + 1]) if "--asof" in sys.argv else date.today()
    o = build_picks(asof)
    print(len(o["picks"]), "picks;", len(o["skipped"]), "skipped;", len(o["maybe"]), "maybe")
    for p in o["picks"]: print(" +", p["store"], "|", p["item"], "| x", p["qty"])
    for k in o["skipped"]: print(" -", k["store"], "|", k["item"], "|", k["why"])
