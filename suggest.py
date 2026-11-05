"""Build next-week.md from history.jsonl (+ open.json), and backtest the last 4 weeks.
Usage: python3 suggest.py [--asof YYYY-MM-DD]   |   python3 suggest.py --backtest"""
import json, os, re, sys, statistics
from bisect import bisect_left
import model
import feedback

from collections import defaultdict
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
STORES = ["ALDI", "Costco", "Walmart"]

def store_of(o):
    s = o["store"]
    return "ALDI" if s.startswith("ALDI") else s

from textmatch import tokens, jacc

def load(path=os.path.join(HERE, "history.jsonl")):
    rows = []  # (store, date, name, qty)
    for line in open(path):
        o = json.loads(line)
        for it in o["items"]:
            if it.get("substitution"): continue  # Walmart's pre-approved backup items; not what was delivered
            rows.append((store_of(o), date.fromisoformat(o["date"]), it["name"], float(it.get("qty") or 1), o["order_id"]))
    return rows

def cluster(rows):
    """Group renamed versions of the same item per store. Returns {(store, name): group_label}."""
    by_store = defaultdict(lambda: defaultdict(int))
    for s, d, n, q, oid in rows:
        by_store[s][n] += 1
    label = {}
    for s, names in by_store.items():
        anchors = []  # (tokens, label)
        for n in sorted(names, key=lambda x: -names[x]):
            t = tokens(n)
            best = max(anchors, key=lambda a: jacc(a[0], t), default=None)
            if best and jacc(best[0], t) >= 0.6:
                label[(s, n)] = best[1]
            else:
                anchors.append((t, n)); label[(s, n)] = n
    return label

def stats(rows, label, asof):
    g = defaultdict(lambda: {"dates": set(), "qty": []})
    for s, d, n, q, oid in rows:
        if d >= asof: continue
        k = (s, label[(s, n)])
        g[k]["dates"].add(d); g[k]["qty"].append(q)
    out = {}
    for k, v in g.items():
        ds = sorted(v["dates"])
        gaps = [(b - a).days for a, b in zip(ds, ds[1:])]
        out[k] = {"times": len(ds), "gap": statistics.median(gaps) if gaps else None, "last": ds[-1],
                  "since": (asof - ds[-1]).days, "qty": round(sum(v["qty"]) / len(ds), 1)}
    return out

def trips_by_store(rows, before):
    t = defaultdict(set)
    for s, d, n, q, oid in rows:
        if d < before: t[s].add(d)
    return {s: sorted(v) for s, v in t.items()}

def item_dates(rows, label, before):
    g = defaultdict(set)
    for s, d, n, q, oid in rows:
        if d < before: g[(s, label[(s, n)])].add(d)
    return {k: sorted(v) for k, v in g.items()}

def chance(dates, trips, since_now, prior_weight=2):
    """How often did you re-buy this item on past trips when about this many days had passed since you last bought it?
    Only trips with a similar gap count (within 30% or 3 days); blended lightly with the item's overall buy rate."""
    past, bought = [], set(dates)
    for t in trips:
        i = bisect_left(dates, t)
        if i == 0: continue
        past.append(((t - dates[i - 1]).days, t in bought))
    if len(past) < 3: return 0.0
    base = sum(b for _, b in past) / len(past)
    win = max(3, 0.3 * since_now)
    near = [b for gap, b in past if abs(gap - since_now) <= win]
    if len(near) < 2: return 0.0          # never been in this situation enough times to judge
    return (sum(near) + prior_weight * base) / (len(near) + prior_weight)

# Cutoffs picked on the older 8 of the 12 backtest weeks per store.
LIKELY_AT = {"default": 0.50, "Walmart": 0.60}
MAYBE_AT = 0.25

def cutoff(c, store):
    return c.get(store, c["default"]) if isinstance(c, dict) else c

def predict(st, asof, open_keys=frozenset(), rows=None, label=None, likely_at=None, maybe_at=None, feedback_on=None):
    """Every repeat item (bought 2+ times at that store, Regular or occasional buy) gets a score: the lower of two
    estimates that it's bought in the next 7 days (similar past trips, and the small learned model). Likely = score at
    or above the store's Likely cutoff; Maybe = above the Maybe cutoff. Items in an open order are left off.
    feedback_on = a date: apply saved chat feedback saved before that date (production only)."""
    likely_at = LIKELY_AT if likely_at is None else likely_at
    maybe_at = MAYBE_AT if maybe_at is None else maybe_at
    trips = trips_by_store(rows, asof); dates = item_dates(rows, label, asof)
    models, scores = {}, {}
    def model_for(s_):
        if s_ not in models:
            models[s_] = model.train([ds for (ss, _), ds in dates.items() if ss == s_], trips[s_])
        return models[s_]
    for (s_, lab), ds in dates.items():
        if len(ds) < 2 or (s_, lab) in open_keys or (s_, lab) not in st: continue
        similar = chance(ds, trips.get(s_, []), st[(s_, lab)]["since"] + 3)
        if similar < cutoff(maybe_at, s_): continue          # the lower of the two can't clear the bar
        m = model_for(s_)
        scores[(s_, lab)] = min(similar, model.score(m, ds, trips[s_], st[(s_, lab)]["since"])) if m else similar
    notes = []
    if feedback_on:
        scores, notes = feedback.adjust(scores, asof=feedback_on)
    out = {"likely": defaultdict(list), "maybe": defaultdict(list), "notes": notes}
    for (s_, lab), p in scores.items():
        v = st[(s_, lab)]; v["chance"] = p
        if p >= cutoff(likely_at, s_): out["likely"][s_].append((lab, v))
        elif p >= cutoff(maybe_at, s_): out["maybe"][s_].append((lab, v))
    for part in ("likely", "maybe"):
        for s_ in out[part]: out[part][s_].sort(key=lambda x: -x[1]["chance"])
    return out

def reason(v):
    g = v["gap"] if v["gap"] is not None else model.DEFAULT_GAP
    every = "every week" if g <= 8 else f"every {round(g / 7)} weeks" if g >= 13 else f"every {int(g)} days"
    late = " (overdue)" if v["since"] > g + 3 else ""
    return f'bought {v["times"]} times, about {every}, last bought {v["since"]} day{"" if v["since"] == 1 else "s"} ago{late}; about {v["chance"]:.0%} chance you want it on the next order'

def open_keys_for(label, rows):
    p = os.path.join(HERE, "open.json")
    if not os.path.exists(p): return set(), []
    op = json.load(open(p)); keys, names = set(), []
    for src, block in op.items():
        if src.startswith("cart_"): continue   # cart contents are handled by plan_fill.py, not treated as open orders
        for it in block.get("items", []):
            s = "Walmart" if src == "walmart" else ("ALDI" if it.get("store", "ALDI").startswith("ALDI") else it.get("store"))
            t = tokens(it["name"]); names.append((s, it["name"]))
            cands = [(jacc(tokens(n), t), lab) for (ss, n), lab in label.items() if ss == s]
            best = max(cands, default=(0, None))
            if best[0] >= 0.6: keys.add((s, best[1]))
    return keys, names

def due_for(asof):
    """This week's Likely/Maybe lists as of today (today's orders count), open orders left out, feedback applied."""
    rows = load(); label = cluster(rows); st = stats(rows, label, asof + timedelta(days=1))
    for v in st.values(): v["since"] -= 1  # stats used asof+1 so today's orders count; since = days before today
    okeys, onames = open_keys_for(label, rows)
    due = predict(st, asof + timedelta(days=1), frozenset(okeys), rows, label, feedback_on=asof + timedelta(days=1))
    return due, rows, label, onames

def write_next_week(asof):
    due, rows, label, onames = due_for(asof)
    lines = [f"# Next week's grocery list (as of {asof})", "",
             "Lists only. Nothing was added to any cart. Reasons come from your last 12 months of orders.",
             "Likely = right about 7 times in 10 in testing. Maybe = things you buy now and then that might be due; trim what you don't need.",
             f"Left out because they're already coming in an open order: {len(onames)} items.", ""]
    if due["notes"]:
        lines += ["Your feedback was used:"] + [f"- {n}" for n in due["notes"]] + [""]
    for s_ in STORES:
        lines.append(f"## {s_}")
        for title, part in (("Likely", "likely"), ("Maybe", "maybe")):
            items = due[part].get(s_, [])
            lines.append(f"### {title}")
            if not items: lines.append("Nothing here this week.")
            for i, (lab, v) in enumerate(items, 1):
                lines.append(f"{i}. {lab}" + (f" (x{v['qty']:g})" if v["qty"] >= 1.5 else "") + f": {reason(v)}")
            lines.append("")
    open(os.path.join(HERE, "next-week.md"), "w").write("\n".join(lines))
    return due

def backtest(today, weeks=12, likely_at=None, maybe_at=None):
    """Hide each past week, predict it from earlier orders only, compare with what was really bought.
    Keep rate = listed items bought that week / listed items. Coverage = repeat items bought that were listed / repeat items bought."""
    rows = load(); label = cluster(rows); res = []
    for k in range(weeks, 0, -1):
        start = today - timedelta(days=7 * k); end = start + timedelta(days=7)
        due = predict(stats(rows, label, start), start, rows=rows, label=label, likely_at=likely_at, maybe_at=maybe_at)
        before, bought = set(), defaultdict(set)
        for s_, d, n, q, oid in rows:
            if d < start: before.add((s_, label[(s_, n)]))
            elif d < end: bought[s_].add(label[(s_, n)])
        for s_ in STORES:
            likely = {lab for lab, v in due["likely"].get(s_, [])}
            maybe = {lab for lab, v in due["maybe"].get(s_, [])}
            repeat = {lab for lab in bought[s_] if (s_, lab) in before}
            res.append({"week": k, "store": s_, "shopped": bool(bought[s_]),
                        "likely": len(likely), "likely_kept": len(likely & bought[s_]),
                        "listed": len(likely | maybe), "kept": len((likely | maybe) & bought[s_]),
                        "repeat": len(repeat), "covered": len(repeat & (likely | maybe))})
    return res

def summarize(res, weeks=None):
    out = {}
    for s_ in STORES + ["ALL"]:
        rr = [r for r in res if (s_ == "ALL" or r["store"] == s_) and r["shopped"] and (weeks is None or r["week"] in weeks)]
        t = {f: sum(r[f] for r in rr) for f in ("likely", "likely_kept", "listed", "kept", "repeat", "covered")}
        t["weeks"] = len(rr)
        out[s_] = t
    return out

def fmt(t):
    pct = lambda a, b: f"{a}/{b} = {a / b:.0%}" if b else "n/a"
    return (f"weeks {t['weeks']} | Likely keep {pct(t['likely_kept'], t['likely'])} | whole-list keep {pct(t['kept'], t['listed'])}"
            f" | coverage {pct(t['covered'], t['repeat'])}")

if __name__ == "__main__":
    today = date.today()
    if "--asof" in sys.argv: today = date.fromisoformat(sys.argv[sys.argv.index("--asof") + 1])
    if "--backtest" in sys.argv:
        res = backtest(today, 12)
        for title, wk in (("All 12 weeks", None), ("Older 8 weeks (cutoffs picked here)", range(5, 13)), ("Recent 4 weeks (held out)", range(1, 5))):
            print(title)
            for s_, t in summarize(res, wk).items(): print(f"  {s_}: {fmt(t)}")
    else:
        due = write_next_week(today)
        print({part: {s_: len(v) for s_, v in d.items()} for part, d in due.items() if part != "notes"}, due["notes"])
