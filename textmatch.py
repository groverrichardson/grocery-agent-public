"""Name matching shared by the suggester and feedback: item names reduced to key words, and how much two names overlap."""
import re

STOP = set("""fresh package bag bags per count pack value family size the and with for each ct oz lb lbs fl gal
original classic natural all-natural style shelf stable shelf-stable free bottle carton container box jar can cans
little salad bar happy harvest farms specially selected emporium selection park street deli baker's bakers treat
corner chef's chefs cupboard simply nature stonemill clancy's clancys millville friendly boulder season's seasons choice
great value marketside kirkland signature""".split())

def tokens(name):
    name = re.sub(r"\(.*?\)", " ", name.lower())
    name = re.sub(r"\d+(\.\d+)?\s*(oz|lb|lbs|ct|count|pack|fl|gal|l|ml|qt|quart|sheets|bags|pk)\b", " ", name)
    words = re.findall(r"[a-z][a-z'&-]+", name)
    return frozenset(w.strip("'") for w in words if len(w) > 2 and w not in STOP)

def jacc(a, b):
    return len(a & b) / len(a | b) if a | b else 0
