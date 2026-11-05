// Fill-plan step 2 (Walmart). Run in any walmart.com tab. View only: reads your past order page to get the exact
// product id, then reads that product's page for price and stock (your selected store). Never presses Add to cart.
// Set window._want = [[nameAsOrdered, latestOrderId], ...] first; result in window._found.
(async () => {
  const nd = t => JSON.parse(t.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/)[1]);
  window._found = [];
  for (const [name, oid] of window._want || []) {
    try {
      const o = nd(await (await fetch('/orders/' + oid)).text()); let pid = null;
      (function w(x) { if (!x || typeof x !== 'object' || pid) return; if (x.productInfo && x.productInfo.name === name) { pid = x.productInfo.usItemId; return; } for (const k in x) w(x[k]); })(o);
      if (!pid) { window._found.push({item: name, found: false, why: 'product id not in that order'}); continue; }
      const pr = nd(await (await fetch('/ip/' + pid)).text()).props.pageProps.initialData.data.product;
      window._found.push({item: name, found: true, link: 'https://www.walmart.com/ip/' + pid, product: pr.name,
                          price: pr.priceInfo?.currentPrice?.priceString || '', stock: pr.availabilityStatus || ''});
    } catch (e) { window._found.push({item: name, found: false, why: String(e).slice(0, 80)}); }
  }
})();
