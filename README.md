# Grocery agent

My family adds plain words like "butter" to one shared Reminders list all week. On Thursday morning this tool works out the real product and store from our order history, adds items to our ALDI, Costco and Walmart carts, and checks off what went in. It also suggests items that look due. Then my wife reviews the carts and we place the orders ourselves.

**It runs on my Mac, against my own store logins.** There's no server or hosted app. It's a Claude desktop scheduled task that follows [RUNBOOK.md](RUNBOOK.md), using Claude in Chrome in a browser where I'm already signed in. So cloning this repo won't fill a cart unless you have your own accounts and order history.

**It never checks out.** It stops at the cart. None of the scripts here has a checkout step, and the runbook forbids Claude from checking out or paying.

**The video shows it running live** on real carts, including what went wrong along the way.

## How it works
1. Collectors read order history from Instacart and Walmart, view only, into a file on the Mac.
2. `weekly.py` reads the open items on the list and finds possible matches in that history. `suggest.py` scores what's due.
3. Claude decides what each item really is. "Butter" means butter, not peanut butter or pork butt. That's judgment, not a keyword match.
4. Claude adds items in Chrome. On Walmart, `collectors/add_walmart.js` clicks only a button with the page's full product name, and otherwise clicks nothing.
5. Claude compares the carts before and after, removes only its own mistakes, and checks off the list.

## What I left out
This repo has the code, the tests and a scrubbed runbook. Our order history, receipts, cart snapshots and run logs stay on my Mac. `sample/` and the test fixtures are made up, with invented products and order ids. [PROMPTS.md](PROMPTS.md) has my real prompts and how they changed.

## Run the tests
You need Python 3 with numpy, and Node. The tests use only the made-up data, so they can't touch a store, a list or an order.

```bash
./run-tests.sh
```

They cover the list side of the weekly run, the suggester and the Walmart add script, including a regression test that the old add script fails. The live store steps aren't covered, because they need real logins.

## Run it for real
You'd need a Mac, Claude desktop with Claude in Chrome, and your own store accounts.

```bash
mkdir -p raw snapshots
swiftc rem/rem.swift -o rem/rem -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker rem/Info.plist
```

Then point a Claude desktop scheduled task at RUNBOOK.md. The first run builds up `history.jsonl` and `open.json`, which stay out of git.
