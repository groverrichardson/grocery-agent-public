// Fill-plan step 2 (Instacart). Run in a tab on instacart.com/store/<store>/buy_it_again (e.g. aldi, costco).
// View only: scrolls and presses "Load More" (which only loads more of the list). Never presses Add.
// Set window._want = [[pickLabel, nameAsOnReceipt], ...] first; result in window._found as {item, product, link, price, stock} (add "store" when saving to fill-found.json).
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 12; i++) {
    const b = [...document.querySelectorAll('button')].find(x => x.innerText.trim() === 'Load More');
    if (!b) break; b.click(); await sleep(1800);
  }
  const cards = {};
  for (const a of document.querySelectorAll('a[href*="/products/"]')) {
    let e = a;
    for (let i = 0; i < 4 && e.parentElement; i++) { if (e.parentElement.querySelectorAll('a[href*="/products/"]').length > 1) break; e = e.parentElement; }
    const t = e.innerText.split('\n').map(s => s.trim()).filter(Boolean).join(' | ');
    if (!cards[a.pathname] || cards[a.pathname].length < t.length) cards[a.pathname] = t;
  }
  window._found = (window._want || []).map(([pick, name]) => {
    const hit = Object.entries(cards).find(([, t]) => t.includes('| ' + name + ' |'));
    if (!hit) return {item: pick, found: false, why: 'not on the Buy it again list'};
    const [path, t] = hit;
    return {item: pick, product: name, found: true, link: 'https://www.instacart.com' + path, price: (t.match(/Current price: (\$[\d.]+)/) || [])[1] || '',
            stock: (t.match(/(Many in stock|In stock|Low stock|Out of stock)/i) || ['stock not shown'])[0]};
  });
})();
