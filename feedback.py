"""Feedback: record kept/dropped items and adjust suggester scores.

CLI:
  python3 feedback.py add --store ALDI --kept "spinach, sample sauce" --dropped "sample cheese" [--date YYYY-MM-DD]
  python3 feedback.py show
Override the file with env var GROCERY_FEEDBACK_FILE (used by tests).
"""
import argparse, json, os, sys
from datetime import date, datetime

from textmatch import tokens, jacc

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback.jsonl")
STORES = ("ALDI", "Costco", "Walmart")


def feedback_path():
    return os.environ.get("GROCERY_FEEDBACK_FILE") or DEFAULT_PATH


def _split(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def record(store, kept=(), dropped=(), on=None, path=None):
    """Append one JSON line per item. Returns the list of entries written."""
    path = path or feedback_path()
    d = (on or date.today()).isoformat() if not isinstance(on, str) else on
    rows = [{"date": d, "store": store, "item": i, "verdict": v}
            for v, items in (("kept", kept), ("dropped", dropped)) for i in items]
    with open(path, "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return rows


def load(path=None):
    path = path or feedback_path()
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def _match(item, labels):
    """Best label for typed text: jacc >= 0.5 or lowercase substring either way."""
    text = item.lower().strip()
    tk = tokens(item)
    best, best_key = None, None
    for lab in labels:
        ll = lab.lower()
        j = jacc(tk, tokens(lab))
        sub = bool(text) and (text in ll or ll in text)
        if j >= 0.5 or sub:
            key = (j, sub)
            if best_key is None or key > best_key:
                best, best_key = lab, key
    return best


def _fmt(d):
    return f"{d.strftime('%b')} {d.day}"


def adjust(scores, store_labels=None, asof=None, path=None):
    """Return (new_scores, notes). Never mutates `scores`.

    scores: {(store, label): probability}. store_labels: optional {store: [labels]}
    (defaults to labels found in scores). asof: date or ISO string; only feedback
    dated strictly before asof is used.
    """
    asof = date.fromisoformat(asof) if isinstance(asof, str) else (asof or date.today())
    labels = {}
    for s, l in scores:
        labels.setdefault(s, []).append(l)
    for s, ls in (store_labels or {}).items():
        labels.setdefault(s, [])
        labels[s] += [l for l in ls if l not in labels[s]]

    per = {}  # (store, label) -> {"drops": [date], "kept": [date]}
    notes = []
    for e in load(path):
        try:
            d = date.fromisoformat(e["date"])
            store, item, verdict = e["store"], e["item"], e["verdict"]
        except (KeyError, ValueError, TypeError):
            continue
        if d >= asof:
            continue
        lab = _match(item, labels.get(store, []))
        if lab is None:
            notes.append(f"Unmatched: {store} \"{item}\" ({verdict} {_fmt(d)}), no matching item")
            continue
        slot = per.setdefault((store, lab), {"drops": [], "kept": []})
        slot["drops" if verdict == "dropped" else "kept"].append(d)

    out = dict(scores)
    for key, slot in per.items():
        if key not in out:
            continue
        s = out[key]
        label = key[1]
        mult = 1.0
        drops = sorted(slot["drops"], reverse=True)
        recent = [d for d in drops if (asof - d).days <= 21]
        old = [d for d in drops if (asof - d).days > 21]
        if recent:
            mult *= 0.4
        mult *= 0.8 ** len(old)
        if drops:
            mult = max(mult, 0.3)
            s *= mult
            notes.append(f"{label}: you dropped it {_fmt(drops[0])}, lowered")
        kept = [d for d in slot["kept"] if (asof - d).days <= 60]
        if kept:
            s = s + (1 - s) * 0.25
            notes.append(f"{label}: you kept it {_fmt(max(kept))}, raised")
        out[key] = s
    return out, notes


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--store", required=True, choices=STORES)
    a.add_argument("--kept", default="")
    a.add_argument("--dropped", default="")
    a.add_argument("--date", default=None)
    sub.add_parser("show")
    args = ap.parse_args(argv)
    if args.cmd == "add":
        if args.date:
            datetime.strptime(args.date, "%Y-%m-%d")
        rows = record(args.store, _split(args.kept), _split(args.dropped), on=args.date)
        print(f"saved {len(rows)} item(s) to {feedback_path()}")
    else:
        for e in load():
            print(f"{e['date']}  {e['store']:<7} {e['verdict']:<7} {e['item']}")


if __name__ == "__main__":
    main()
