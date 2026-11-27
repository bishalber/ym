const g = $('Load').first().json;
let state = { words: {} };
if (g.statusCode === 200) { try { const s = JSON.parse(g.body); if (s && s.words) state = s; } catch (e) {} }
const limit = Math.max(1, Math.min(30, parseInt($('When called').first().json.limit, 10) || 10));
const all = Object.values(state.words);
const due = all.filter(w => w.due <= ymd(0)).sort((a, b) => (a.box - b.box) || a.due.localeCompare(b.due));
const boxes = [1, 2, 3, 4, 5].map(b => `box${b}:${all.filter(w => w.box === b).length}`).join(' ');
const lines = due.slice(0, limit).map(w => `${w.fi} | ${w.ar} | ${w.en} | box${w.box}${w.example ? ' | ' + w.example : ''}${w.mnemonic ? ' | 💡' + w.mnemonic : ''}`);
return [{ json: { result: `Saved: ${all.length}. Due today: ${due.length}. ${boxes}\n` + (lines.join('\n') || '(nothing due)') } }];
