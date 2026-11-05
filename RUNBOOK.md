# Weekly grocery run (Claude desktop scheduled task)

Everything starts from one list, the shared Reminders list **Shopping**. Never create another list.
The family only does two things. All week, anyone adds what they need in plain words ("butter"), with no store or brand.
On Thursday morning, the main shopper reviews the carts and adds or removes items there. She never approves or checks off
anything on the list. This run works out the real product and store from order history, fills the carts, and checks
off what went in.

Hard rules (every run):
- Never remove or change an item that was in a cart before this run. Never check out, never pay. The only thing this run may remove is its own mistake (step 8).
- Store sites only through Claude in Chrome (load the chrome-browser skill first). No other browser tools.
- Never rename or delete anyone's reminders, and never add any. The only list change is checking off items now in a cart.
- Log every run in attempts.md (one line) and keep a before/after cart snapshot in snapshots/.

## The run (Thursday 7:00 a.m.)
1. `cd <this folder> && (lsof -i :8765 >/dev/null || nohup python3 receiver.py >> receiver.log 2>&1 &)`
2. Refresh order history in Chrome (view only):
   - Instacart: open https://www.instacart.com/store/account/orders, keep the tab in front, run
     `eval((await (await fetch('http://127.0.0.1:8765/js/instacart_parse')).json()).code)` then the same for
     `/js/instacart`. Poll `window._icrun.phase` until `done`.
   - Walmart: open https://www.walmart.com/orders. Its page can't reach the Mac directly, so inject a button
     that opens http://127.0.0.1:8765/relay in a popup and defines `window._send` (postMessage bridge), click it
     with a real click, then paste the contents of collectors/walmart.js (eval is blocked there). Poll `window._wmrun`.
3. Cart snapshot (view only): Instacart cart panel (button top right on any instacart.com/store/<store> page)
   for ALDI and Costco; walmart.com/cart with collectors/snap_walmart.js. Save as
   `snapshots/carts-<YYYY-MM-DD>.json` in the same shape as sample/carts.json.
4. `python3 weekly.py candidates --carts snapshots/carts-<YYYY-MM-DD>.json`. It prints each open item with a wide net
   of possible history matches, plus this week's suggestions.
5. Decide what each item really is. This is your judgment, not a keyword match. "butter" means butter, not peanut
   butter, buttermilk or pork butt. "Flashlight batteries" means AA.
   - Pick the product they actually buy: among real matches, most `trips_90d`, then most `trips_all`, then most recent.
   - The store is that product's store. Honor a store if someone typed one ("butter costco").
   - Nothing in history is really that item: set store and product to null. The fill tries ALDI, then Walmart, then Costco.
   - Drop a suggestion only if it's the same thing as an item on the list.
   Save `resolved-<YYYY-MM-DD>.json`: `{"items": [{id, item, store, product, qty}], "suggestions": [{store, product, qty}]}`.
6. `python3 weekly.py queue resolved-<YYYY-MM-DD>.json`

7. Fill, from fill-queue.json, per item:
   - Already in that store's cart or on an open order for that store (same product or clearly the same item) → put it under `skipped`, don't add. Skipped list items get checked off, since they're covered.
   - **Never click the first Add button on a page.** Store pages also have Add buttons on recommended products. Only
     click one whose label names the exact product. After each add, open the cart and compare the full product name
     and size, word for word, to the cart line (a matching brand or start of the name isn't enough), and confirm the
     count went up by one. Note what each add changed in the cart. If anything else landed, handle it in step 8 before adding more at that store.
   - ALDI / Costco: if Instacart connector tools (mcp `cart`, `search_products`) are available, try them first,
     and check in the Instacart cart panel that the item landed in the store's **Family Cart**. If the
     connector isn't available or doesn't reach the Family Cart, use Chrome: open
     https://www.instacart.com/store/<aldi|costco>/s?k=<product> and press the button labeled `Add 1 ct <product>`.
   - **Open Instacart orders:** a placed order shows "Add items to order" and the cart panel says "Your upcoming order".
     Never add to or change an order. Before adding at that store, open the carts list on https://www.instacart.com/store
     and confirm a Family Cart for it exists, or press "New cart" once. After the first add, check the item is in the
     cart and the order total hasn't changed. If it went to the order, stop and report it.
   - Walmart: find the product id from the most recent order with that product (walmart.com/orders/<id>
     `__NEXT_DATA__`, `productInfo.usItemId`), open walmart.com/ip/<id>, make sure one-time purchase is
     selected, then run collectors/add_walmart.js. It clicks only a button labeled with this page's full product name.
     If it refuses, nothing was clicked: the product may already be in the cart (its button becomes a quantity stepper),
     so check the cart, count it as skipped if it's there, otherwise try once more or mark it `not_found`. Set quantity after.
   - `product` is null (no history): search the stores in `try_order` and use the first with a clear match. No clear match anywhere → `not_found`.
8. Double-check and clean up before anyone reviews:
   - Snapshot carts after and compare with the before snapshot, line by line (Walmart's collapsed seller groups too).
   - For each line this run added, check it's the product it was meant to be, at the right quantity.
   - **Wrong item your own add caused:** remove just that line, and fix the quantity if that's what's wrong. Then try the
     right product once more, or mark it `not_found`. Report every removal.
   - **Never remove a line you can't tie to one of your own adds.** Someone may be adding to a shared cart while this runs, so flag it in the report instead.
   - Every item from the before snapshot must still be there, unchanged. Snapshot again once clean.
9. Write fill-results-<week>.json (`added`, `skipped`, `not_found`, each entry keeping its `reminder` id, plus store,
   item, product, qty) and run `python3 weekly.py done fill-results-<week>.json`. Added and skipped items get checked
   off the list. Not-found items stay open with a note.
10. Report what was added per store (mark suggested items), what was skipped or not found, any match you weren't sure about, and the cart counts before and after.

If Chrome isn't connected, nothing can be filled: change nothing and report it.
