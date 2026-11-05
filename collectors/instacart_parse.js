// Turns the text of an Instacart full receipt into {store, date, items[]}. Only items actually received are kept.
window._icparse = function (txt) {
  const L = txt.split('\n').map(s => s.trim()).filter(Boolean);
  const m = txt.match(/Your order from (.+?) was placed on ([A-Za-z]+) (\d+)\w*, (\d{4})/);
  const mon = {January:'01',February:'02',March:'03',April:'04',May:'05',June:'06',July:'07',August:'08',September:'09',October:'10',November:'11',December:'12'};
  const date = m ? `${m[4]}-${mon[m[2]]}-${String(m[3]).padStart(2, '0')}` : null;
  const NOT_NAME = /^(\$|Adjustment:|Subtotal|Original price|Final item price|Replaced item price|✓|Refunded|Item \d+$|\d+(\.\d+)? (lb )?x \$)/;
  let sec = ''; const items = [];
  for (let i = 0; i < L.length; i++) {
    const l = L[i];
    if (/^(ADJUSTMENTS|NOT CHARGED|REPLACEMENTS|WEIGHT ADJUSTMENTS|ITEMS FOUND|ORDER TOTALS)/.test(l)) { sec = l.split(' (')[0]; if (sec === 'ORDER TOTALS') break; continue; }
    if (sec === '' || sec === 'NOT CHARGED' || sec === 'ADJUSTMENTS' || NOT_NAME.test(l)) continue;
    let j = i + 1; if (/^Item \d+$/.test(L[j] || '')) j++;           // Costco puts an item number under the name
    const qm = (L[j] || '').match(/^([\d.]+) (lb )?x \$/);
    const weight = sec === 'WEIGHT ADJUSTMENTS' && /^\$[\d.]+$/.test(L[j] || '') && /^Adjustment:/.test(L[j + 1] || '');
    if (!qm && !weight) continue;
    if (sec === 'REPLACEMENTS' && !/Replaced item price/.test(L.slice(j, j + 4).join(' '))) continue; // the item that was swapped out
    const nm = l.match(/^(.*?)(?: \(([^)]*)\))?$/);
    items.push({name: nm[1], size: nm[2] || '', qty: qm && !qm[2] ? +qm[1] : 1, section: sec});
  }
  return {store: m ? m[1] : '?', date, items};
};
