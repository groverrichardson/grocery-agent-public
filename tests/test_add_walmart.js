// Regression test for collectors/add_walmart.js, using made-up pages in the same shape as real Walmart pages (title and button labels only).
// Run: node tests/test_add_walmart.js            (the live script)
//      ADD_WALMART_SCRIPT=tests/fixtures/add_walmart.before-fix.js node tests/test_add_walmart.js   (must fail)
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
const root = path.join(__dirname, '..');
const script = fs.readFileSync(process.env.ADD_WALMART_SCRIPT ? path.resolve(process.env.ADD_WALMART_SCRIPT) : path.join(root, 'collectors/add_walmart.js'), 'utf8');

function run(title, labels, dry) {
  const clicked = [];
  const buttons = labels.map(l => ({getAttribute: a => (a === 'aria-label' ? l : null), click: () => clicked.push(l)}));
  const document = {
    querySelector: s => (s === 'h1' && title ? {innerText: title} : null),
    querySelectorAll: s => {
      const m = s.match(/^button\[aria-label(?:\^="(.*)")?\]$/);
      if (!m) throw new Error('unexpected selector ' + s);
      return buttons.filter(b => b.getAttribute('aria-label').startsWith(m[1] || ''));
    },
  };
  const sandbox = {document, JSON};
  sandbox.window = sandbox;
  if (dry) sandbox.__addWalmartDryRun = true;
  return {result: JSON.parse(vm.runInNewContext(script, sandbox)), clicked};
}
const load = n => JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', `walmart_${n}.json`), 'utf8'));
let failed = 0;
const test = (name, fn) => { try { fn(); console.log('pass', name); } catch (e) { failed++; console.log('FAIL', name, '-', e.message.split('\n')[0]); } };

for (const n of ['lotion', 'crackers']) {
  const f = load(n), want = 'Add to cart - ' + f.title;
  test(`${n}: with the exact button present, clicks only that one`, () => {
    const {result, clicked} = run(f.title, f.not_in_cart);
    assert.deepStrictEqual(clicked, [want]);
    assert.strictEqual(result.ok, true);
  });
  test(`${n}: with no exact button (in cart), refuses and clicks nothing`, () => {
    const {result, clicked} = run(f.title, f.in_cart);
    assert.deepStrictEqual(clicked, []);
    assert.strictEqual(result.ok, false);
  });
  test(`${n}: dry run finds the button without clicking`, () => {
    const {result, clicked} = run(f.title, f.not_in_cart, true);
    assert.deepStrictEqual(clicked, []);
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.dry, true);
  });
}
test('no title: refuses and clicks nothing', () => {
  const {result, clicked} = run('', ['Add to cart - Anything']);
  assert.deepStrictEqual(clicked, []);
  assert.strictEqual(result.ok, false);
});
test('a longer name that starts with the title is not a match', () => {
  const {clicked} = run('Sample Bakery Bread, 16 oz', ['Add to cart - Sample Bakery Bread, 16 oz, 2 Pack']);
  assert.deepStrictEqual(clicked, []);
});
test('extra spaces in a label still match the same name', () => {
  const {clicked} = run("Sample Bakery Rolls 12 Count, 12oz, Shelf", ["Add to cart - Sample Bakery Rolls 12 Count, 12oz,  Shelf"]);
  assert.strictEqual(clicked.length, 1);
});
console.log(failed ? `${failed} failed` : 'all passed');
process.exit(failed ? 1 : 0);
