import os, tempfile, subprocess, sys
from datetime import date

tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
tmp.close()
os.environ["GROCERY_FEEDBACK_FILE"] = tmp.name
import feedback as fb

HERE = os.path.dirname(os.path.abspath(__file__))
ASOF = date(2026, 10, 15)
S = {("ALDI", "Sample Greens Spinach"): 0.6, ("ALDI", "Sample Cheese"): 0.5,
     ("Costco", "Sample Cheese"): 0.5, ("ALDI", "Sample Sauce"): 0.4}

def reset():
    open(tmp.name, "w").close()

def run(scores=S):
    return fb.adjust(scores, None, ASOF)

# recording via CLI
reset()
r = subprocess.run([sys.executable, os.path.join(HERE, "feedback.py"), "add", "--store", "ALDI",
                    "--kept", "spinach, sample sauce", "--dropped", "sample cheese", "--date", "2026-10-08"],
                   capture_output=True, text=True, env=os.environ)
assert r.returncode == 0, r.stderr
lines = fb.load()
assert len(lines) == 3, lines
assert lines[0] == {"date": "2026-10-08", "store": "ALDI", "item": "spinach", "verdict": "kept"}
assert {l["verdict"] for l in lines} == {"kept", "dropped"}
show = subprocess.run([sys.executable, os.path.join(HERE, "feedback.py"), "show"],
                      capture_output=True, text=True, env=os.environ).stdout
assert "sample cheese" in show

# fuzzy match + keep raises + drop lowers + input not mutated + store isolation
orig = dict(S)
new, notes = run()
assert S == orig
assert new[("ALDI", "Sample Greens Spinach")] > 0.6          # spinach -> long label, kept
assert abs(new[("ALDI", "Sample Greens Spinach")] - (0.6 + 0.4 * 0.25)) < 1e-9
assert new[("ALDI", "Sample Sauce")] > 0.4
assert abs(new[("ALDI", "Sample Cheese")] - 0.5 * 0.4) < 1e-9      # recent drop
assert new[("Costco", "Sample Cheese")] == 0.5                     # other store untouched
assert any(n.startswith("Sample Cheese: you dropped it Oct 8, lowered") for n in notes), notes

# entries on/after asof are ignored
assert fb.adjust(S, None, date(2026, 10, 8))[0] == S

# old drops decay (0.8 each, capped at 0.3x)
reset()
fb.record("ALDI", dropped=["sample cheese"], on="2026-08-01")
assert abs(run()[0][("ALDI", "Sample Cheese")] - 0.5 * 0.8) < 1e-9
for d in ("2026-08-02", "2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07"):
    fb.record("ALDI", dropped=["sample cheese"], on=d)
assert abs(run()[0][("ALDI", "Sample Cheese")] - 0.5 * 0.3) < 1e-9   # capped
# kept older than 60 days has no effect
reset()
fb.record("ALDI", kept=["sample sauce"], on="2026-06-01")
assert run()[0][("ALDI", "Sample Sauce")] == 0.4

# unmatched reported, not an error
reset()
fb.record("ALDI", dropped=["dragonfruit"], on="2026-10-08")
fb.record("Walmart", dropped=["sample cheese"], on="2026-10-08")  # store has no such label
new, notes = run()
assert new == S
assert sum("Unmatched" in n for n in notes) == 2, notes

os.unlink(tmp.name)
print("all tests passed")
