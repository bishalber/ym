const g = $('Load').first().json;
let state = { words: {} };
if (g.statusCode === 200) { try { const s = JSON.parse(g.body); if (s && s.words) state = s; } catch (e) {} }
let items;
try { items = JSON.parse($('When called').first().json.words); }
catch (e) { throw new Error('words must be a JSON array like [{"fi":"talo","ar":"بيت","en":"house"}]'); }
if (!Array.isArray(items)) items = [items];
let added = 0; const known = [];
for (const w of items) {
  const key = String((w && w.fi) || '').trim().toLowerCase();
  if (!key) continue;
  if (state.words[key]) { known.push(key); continue; }
  state.words[key] = { fi: w.fi.trim(), ar: w.ar || '', en: w.en || '', example: w.example || '', mnemonic: w.mnemonic || '', chapter: w.chapter || '', box: 1, due: ymd(1), added: ymd(0), lapses: 0, seen: 0 };
  added++;
}
return [{ json: { result: `Added ${added} word(s). Already saved: ${known.join(', ') || 'none'}. Total saved: ${Object.keys(state.words).length}.`, payload: JSON.stringify(state, null, 1) } }];
