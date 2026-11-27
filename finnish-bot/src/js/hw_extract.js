const res = $input.first().json;
if (res.error || !Array.isArray(res.content)) throw new Error('Claude error: ' + JSON.stringify(res.error || res).slice(0, 300));
let text = res.content.filter(c => c.type === 'text').map(c => c.text).join('\n').trim();
const m = text.match(/\n?MISTAKES:\s*(.*)\s*$/i);
let mistakes = '';
if (m) { mistakes = m[1].trim(); text = text.slice(0, m.index).trim(); }
const state = parse(body('Get notes'), { notes: [] });
if (!Array.isArray(state.notes)) state.notes = [];
if (mistakes && !/^none\.?$/i.test(mistakes)) state.notes.push({ date: ymd(0), text: 'Homework mistakes: ' + mistakes });
return [{ json: { reply: text, payload: JSON.stringify(state, null, 1) } }];
