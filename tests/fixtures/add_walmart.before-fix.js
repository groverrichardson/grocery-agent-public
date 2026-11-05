// Walmart safe add. Run on walmart.com/ip/<id>. Clicks only the Add button whose label names THIS page's product
// (recommendation carousels have Add buttons too; clicking the first one put the wrong items in the cart).
// Returns {ok, product, label} or {ok:false, why}. After it returns ok, read the cart and confirm the product is there.
(() => {
  const h1 = (document.querySelector('h1')?.innerText || '').trim();
  if (!h1) return JSON.stringify({ok: false, why: 'no product title on page'});
  const want = 'Add to cart - ' + h1.slice(0, 40);
  const b = [...document.querySelectorAll('button[aria-label^="Add to cart - "]')].find(x => x.getAttribute('aria-label').startsWith(want));
  if (!b) return JSON.stringify({ok: false, why: 'no Add button for this product', product: h1});
  b.click();
  return JSON.stringify({ok: true, product: h1, label: b.getAttribute('aria-label').slice(0, 80)});
})()
