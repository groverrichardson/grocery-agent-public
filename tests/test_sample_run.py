"""End-to-end test of the list side of the weekly run, on the made-up data in sample/.
It works in a temp copy, with a stand-in for rem/rem, so it can't touch Reminders, a store or real history."""
import contextlib, io, json, os, shutil, stat, sys, tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = date(2026, 10, 1)  # a Thursday, right after the last sample week
tmp = tempfile.mkdtemp()
for f in os.listdir(ROOT):
    if f.endswith(".py"): shutil.copy(os.path.join(ROOT, f), tmp)
shutil.copy(os.path.join(ROOT, "sample/history.jsonl"), tmp)
shutil.copy(os.path.join(ROOT, "sample/open.json"), tmp)
os.mkdir(os.path.join(tmp, "rem"))
fake = os.path.join(tmp, "rem", "rem")
log = os.path.join(tmp, "rem-calls.txt")
with open(fake, "w") as f:  # records each call; "read" returns the sample list
    f.write(f'#!/bin/sh\nif [ "$1" = read ]; then cat "{ROOT}/sample/shopping-list.json"; else echo "$1 $(cat)" >> "{log}"; echo true; fi\n')
os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
os.environ["GROCERY_FEEDBACK_FILE"] = os.path.join(tmp, "feedback.jsonl")
sys.path.insert(0, tmp)
import suggest, plan_fill, weekly
assert weekly.__file__.startswith(os.path.realpath(tmp)) or weekly.__file__.startswith(tmp), weekly.__file__

class FixedDate(date):
    @classmethod
    def today(cls): return TODAY
weekly.date = FixedDate

def captured(fn, *a, **k):
    out = io.StringIO()
    with contextlib.redirect_stdout(out): fn(*a, **k)
    return out.getvalue()

passed = 0
def check(name, ok, detail=""):
    global passed
    assert ok, f"FAIL {name} {detail}"
    passed += 1; print("pass", name)

rows = suggest.load(os.path.join(tmp, "history.jsonl"))
check("loader keeps orders and skips backup items", rows and not any("Backup" in r[2] for r in rows))

res = suggest.backtest(TODAY, 12)
t = suggest.summarize(res)["ALL"]
check("backtest runs and lists items", t["weeks"] > 0 and t["listed"] > 0, t)

picks = plan_fill.build_picks(TODAY)
check("suggester picks due items", len(picks["picks"]) > 0)

got = json.loads(captured(weekly.candidates, os.path.join(ROOT, "sample/carts.json")))
butter = [m["product"] for i in got["items"] if i["item"] == "butter" for m in i["matches"]]
check("'butter' casts a wide net, real butter and peanut butter", any("Butter Sticks" in p for p in butter) and any("Peanut Butter" in p for p in butter), butter)
check("an item with no history has no matches", not [i for i in got["items"] if i["item"] == "Unicorn tonic"][0]["matches"])
check("a suggestion already in the cart is dropped", not any("Lemonade" in s["product"] for s in got["suggestions"]), got["suggestions"])

weekly.QUEUE = os.path.join(tmp, "fill-queue.json")
captured(weekly.queue, os.path.join(ROOT, "sample/resolved.json"))
q = json.load(open(weekly.QUEUE))
check("the queue week is this Thursday", q["week"] == "2026-10-01", q["week"])
new = [i for i in q["items"] if i["item"] == "Unicorn tonic"][0]
check("a first-time item tries ALDI, then Walmart, then Costco", new["try_order"] == ["ALDI", "Walmart", "Costco"])
check("a suggestion is marked and has no list item", [i for i in q["items"] if i.get("suggested")][0]["reminder"] is None)

out = captured(weekly.done, os.path.join(ROOT, "sample/results.json"))
calls = open(log).read()
check("added and skipped get checked off, not found stays open", "sample-reminder-1" in calls and "sample-reminder-2" in calls and "sample-reminder-3" not in calls, calls)
check("the only list change is checking off", calls.startswith("complete ") and calls.count("\n") == 1, calls)

shutil.rmtree(tmp)
print(f"all {passed} sample run checks passed")
