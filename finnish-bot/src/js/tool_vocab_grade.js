const g = $('Load').first().json;
let state = { words: {} };
if (g.statusCode === 200) { try { const s = JSON.parse(g.body); if (s && s.words) state = s; } catch (e) {} }
const inp = $('When called').first().json;
const key = String(inp.word || '').trim().toLowerCase();
const w = state.words[key];
if (!w) throw new Error(`Word "${key}" is not saved. Use vocab_add first.`);
const ok = /^(y|yes|true|1|correct)/i.test(String(inp.correct || ''));
const INTERVALS = [1, 2, 4, 8, 16];
w.seen = (w.seen || 0) + 1;
if (ok) { w.box = Math.min(5, (w.box || 1) + 1); }
else { w.box = 1; w.lapses = (w.lapses || 0) + 1; }
w.due = ymd(INTERVALS[w.box - 1]);
return [{ json: { result: `${w.fi}: ${ok ? 'correct' : 'wrong'} -> box ${w.box}, next review ${w.due}.`, payload: JSON.stringify(state, null, 1) } }];
