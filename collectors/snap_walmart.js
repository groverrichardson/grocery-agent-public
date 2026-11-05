// Walmart cart snapshot, view only. Run on walmart.com/cart. Returns {count, items:[[name, qty]]} from the cart's own labels.
(() => {
  const items = [...document.querySelectorAll('[aria-label^="Decrease quantity "]')].map(e => {
    const m = e.getAttribute('aria-label').match(/^Decrease quantity (.*), Current Quantity (\d+)$/);
    return m ? [m[1], +m[2]] : null;
  }).filter(Boolean);
  const head = (document.body.innerText.match(/Cart\s*\((\d+) items?\)/) || [])[1];
  return JSON.stringify({store: 'Walmart', header_count: head ? +head : null, lines: items.length, items});
})()
