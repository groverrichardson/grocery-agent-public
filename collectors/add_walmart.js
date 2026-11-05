// Walmart safe add. Run on walmart.com/ip/<id>. Clicks only an Add button labeled with THIS page's full product name.
// Recommended products have Add buttons too, often the same brand in another size, and they come first in the page.
// A product already in the cart has a quantity stepper instead of an Add button, so it gets a refusal, not a click.
// Set window.__addWalmartDryRun = true to check the page without clicking. Test: node tests/test_add_walmart.js
// Returns {ok, product, label} or {ok:false, why}. After it returns ok, read the cart and compare the full name and size.
(() => {
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();  // labels can hold double spaces that the page title collapses
  const h1 = clean(document.querySelector('h1')?.innerText);
  if (!h1) return JSON.stringify({ok: false, why: 'no product title on page'});
  const label = 'Add to cart - ' + h1;
  const matches = [...document.querySelectorAll('button[aria-label]')].filter(x => clean(x.getAttribute('aria-label')) === label);
  if (!matches.length) return JSON.stringify({ok: false, why: 'no Add button with this exact product name (it may already be in the cart)', product: h1});
  if (window.__addWalmartDryRun) return JSON.stringify({ok: true, dry: true, product: h1, matches: matches.length});
  matches[0].click();
  return JSON.stringify({ok: true, product: h1, label});
})()
