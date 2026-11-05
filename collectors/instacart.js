// Instacart collector. Paste into the instacart.com/store/account/orders tab, which must stay in front (Chrome slows background tabs).
// Read-only: loads order pages and full receipts in hidden frames. Never clicks Reorder / Add all items to cart.
(async () => {
  const CUTOFF = new Date('2025-10-02T00:00:00');
  const STORES = /^(ALDI|ALDI Express|Costco)$/;
  const RX = 'http://127.0.0.1:8765';
  const S = window._icrun = {phase: 'start', t0: Date.now(), listed: 0, fetched: 0, saved: 0, dup: 0, open: [], skipped: 0, stopReason: '', errors: []};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const send = async (method, path, body) => (await fetch(RX + path, {method, headers: {'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined})).json();
  const known = new Set(await send('GET', '/known?source=instacart'));
  const mon = {Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11};
  const cardDate = t => { const m = t.match(/([A-Z][a-z]{2}) (\d+)(?:, (\d{4}))?/); return m ? new Date(m[3] ? +m[3] : new Date().getFullYear(), mon[m[1]], +m[2]) : null; };
  const cards = () => [...document.querySelectorAll('a')].filter(a => /order detail/i.test(a.innerText)).map(a => {
    let e = a; while (e.parentElement && (e.parentElement.innerText.match(/Order placed/g) || []).length < 2) e = e.parentElement;
    const l = e.innerText.split('\n').map(s => s.trim()).filter(Boolean);
    return {id: a.href.split('/').pop(), status: l[1] || '', store: l[7] || '', date: cardDate(l[1] || '')};
  });
  // 1. load the list until we pass the cutoff or reach an order we already saved
  S.phase = 'loading list';
  for (let i = 0; i < 60; i++) {
    const c = cards(); const last = c[c.length - 1];
    if (c.some(x => known.has(x.id)) || (last && last.date && last.date < CUTOFF)) break;
    window.scrollTo(0, document.body.scrollHeight); await sleep(1500);
    const b = [...document.querySelectorAll('button,a')].find(x => /^Load more orders$/i.test(x.innerText.trim()));
    if (b) { b.click(); await sleep(1500); } else if (i > 3) break;
  }
  const frame = async (url, test, timeout = 40000) => {
    const f = document.createElement('iframe'); f.style.cssText = 'position:fixed;left:0;top:0;width:1200px;height:900px;opacity:0.01;pointer-events:none'; f.src = url; document.body.appendChild(f);
    const t0 = Date.now(); let v = null;
    while (Date.now() - t0 < timeout) { await sleep(700); try { v = test(f.contentDocument); if (v) break; } catch (e) {} }
    f.remove(); return v;
  };
  // 2. work newest -> oldest
  for (const c of cards()) {
    S.listed++;
    if (known.has(c.id)) { S.stopReason = 'reached already-saved order ' + c.id; break; }
    if (c.date && c.date < CUTOFF) { S.stopReason = 'reached 12-month cutoff'; break; }
    if (!STORES.test(c.store) || /Cancel|Refunded/i.test(c.status)) { S.skipped++; continue; }
    if (!/^(Delivered|Picked up)/.test(c.status)) { S.open.push(c); continue; } // still coming: read separately, not saved
    S.phase = 'order ' + c.id;
    try {
      const href = await frame('/store/orders/' + c.id, d => { const a = [...d.querySelectorAll('a')].find(a => /\/receipt/.test(a.href)); return a && a.href; });
      if (!href) { S.errors.push(c.id + ':no receipt link'); continue; }
      const u = new URL(href); u.searchParams.set('full', 'true');
      const txt = await frame(u.toString(), d => { const m = d.querySelector('main'); return m && /ORDER TOTALS/i.test(m.innerText) && m.innerText; });
      if (!txt) { S.errors.push(c.id + ':receipt did not load'); continue; }
      S.fetched++;
      const p = window._icparse(txt);
      const r = await send('POST', '/order', {source: 'instacart', order_id: c.id, store: p.store, date: p.date, items: p.items, raw: txt});
      r.saved ? S.saved++ : S.dup++;
    } catch (e) { S.errors.push(c.id + ':' + e); }
  }
  S.secs = (Date.now() - S.t0) / 1000; S.phase = 'done';
  await send('POST', '/log', {source: 'instacart', ...S, open: S.open.map(o => o.id + ' ' + o.store + ' ' + o.status)});
})();
