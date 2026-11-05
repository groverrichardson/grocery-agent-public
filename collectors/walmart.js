// Walmart collector. Paste into the walmart.com/orders tab (read-only: fetches order pages, clicks "Next page" only).
// Needs window._send (helper-window bridge to the Mac receiver). Results go to history.jsonl / open.json.
(async () => {
  const CUTOFF = new Date('2025-10-02T00:00:00-05:00');
  const FINAL = new Set(['DELIVERED', 'PICKED_UP', 'CANCELLED', 'CANCELED', 'RETURNED']);
  const S = window._wmrun = {phase: 'start', t0: Date.now(), pages: 0, fetched: 0, saved: 0, dup: 0, open: 0, instore: 0, openParts: 0, stopReason: '', errors: [], statuses: {}};
  try {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const known = new Set(await window._send('GET', '/known?source=walmart'));           // keys like "<order id>#<part>"
  const knownBase = new Set([...known].map(k => k.split('#')[0]));
  const stillOpen = new Set(await window._send('GET', '/openids?source=walmart'));     // orders that had parts on the way last time
  const getOrder = async id => {
    const t = await (await fetch('/orders/' + id)).text();
    const m = t.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
    return m ? JSON.parse(m[1]).props.pageProps.initialData.data.order : null;
  };
  const itemsOf = g => {
    const out = [], seen = new Set();
    (function walk(x, sub) {
      if (!x || typeof x !== 'object') return;
      if (x.productInfo && x.productInfo.name && x.id) {
        if (!seen.has(x.id)) { seen.add(x.id); out.push({name: x.productInfo.name, size: '', qty: +x.quantity || 1, price: x.priceInfo?.linePrice?.displayValue || '', substitution: sub}); }
        return;
      }
      for (const k in x) { if (k === 'items' && Array.isArray(x.categories)) continue; walk(x[k], sub || k === 'substitutions'); }
    })(g, false);
    return out;
  };
  const st = g => (g.status && g.status.statusType) || g.status;
  const openItems = [];
  // Each part of an order (pickup, delivery, shipped) is saved on its own once it has arrived.
  const handle = async (id) => {
    let o; try { o = await getOrder(id); S.fetched++; } catch (e) { S.errors.push(id + ':' + e); return 'err'; }
    if (!o) { S.errors.push(id + ':nodata'); return 'err'; }
    if (new Date(o.orderDate) < CUTOFF) return 'cutoff:' + o.orderDate.slice(0, 10);
    (o.groups_2101 || []).forEach((g, k) => {
      S.statuses[st(g)] = (S.statuses[st(g)] || 0) + 1;
      if (!FINAL.has(st(g))) { for (const it of itemsOf(g)) openItems.push({...it, order_id: id, status: st(g)}); S.openParts++; }
    });
    for (const [k, g] of (o.groups_2101 || []).entries()) {
      if (!(st(g) === 'DELIVERED' || st(g) === 'PICKED_UP') || known.has(id + '#' + k)) continue;
      const r = await window._send('POST', '/order', {source: 'walmart', order_id: id + '#' + k, store: 'Walmart', date: o.orderDate.slice(0, 10), part: g.fulfillmentType, items: itemsOf(g)});
      r.saved ? S.saved++ : S.dup++;
    }
    return 'ok';
  };
  for (const id of stillOpen) await handle(id);   // re-check last run's open orders first
  const ids = () => [...document.querySelectorAll('[data-automation-id^="view-order-details-link-"]')].map(a => a.getAttribute('data-automation-id').replace('view-order-details-link-', ''));
  let stop = false;
  const done = new Set(stillOpen);
  while (!stop) {
    S.phase = 'page ' + (S.pages + 1);
    for (const id of [...new Set(ids())]) {
      if (done.has(id)) continue; done.add(id);
      if (knownBase.has(id)) { S.stopReason = 'reached already-saved order ' + id; stop = true; break; }
      if (id.length > 16) { S.instore++; continue; }
      const r = await handle(id);
      if (r.startsWith('cutoff')) { S.stopReason = 'reached 12-month cutoff at ' + r.slice(7); stop = true; break; }
    }
    if (stop) break;
    const nb = [...document.querySelectorAll('button,a')].find(b => (b.getAttribute('aria-label') || '').trim() === 'Next page');
    if (!nb || nb.disabled || nb.getAttribute('aria-disabled') === 'true') { S.stopReason = 'no more pages'; break; }
    nb.click(); S.pages++; await sleep(2500);
  }
  await window._send('POST', '/open', {source: 'walmart', items: openItems, read_at: new Date().toISOString()});
  } catch (e) { S.errors.push('fatal:' + e); }
  S.secs = (Date.now() - S.t0) / 1000; S.phase = 'done';
  await window._send('POST', '/log', {source: 'walmart', run: window._runNo || 0, ...S});
})();
