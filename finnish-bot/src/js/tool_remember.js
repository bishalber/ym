const g = $('Load').first().json;
let state = { notes: [] };
if (g.statusCode === 200) { try { const s = JSON.parse(g.body); if (s && Array.isArray(s.notes)) state = s; } catch (e) {} }
const note = String($('When called').first().json.note || '').trim().slice(0, 400);
if (!note) throw new Error('note is empty');
state.notes.push({ date: ymd(0), text: note });
state.notes = state.notes.slice(-200);
return [{ json: { result: 'Saved note.', payload: JSON.stringify(state, null, 1) } }];
