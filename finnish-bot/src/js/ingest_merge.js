const res = $input.first().json;
if (res.error || !Array.isArray(res.content)) throw new Error('Claude error: ' + JSON.stringify(res.error || res).slice(0, 300));
const data = JSON.parse(res.content.filter(c => c.type === 'text').map(c => c.text).join(''));
const state = parse(body('Get vocab'), { words: {} });
if (!state.words) state.words = {};
const added = [], known = [];
for (const w of data.words || []) {
  const key = String(w.fi || '').trim().toLowerCase();
  if (!key) continue;
  if (state.words[key]) { known.push(key); continue; }
  state.words[key] = { fi: w.fi.trim(), ar: w.ar || '', en: w.en || '', example: w.example || '', mnemonic: w.mnemonic || '', chapter: data.chapter || '', box: 1, due: ymd(1), added: ymd(0), lapses: 0, seen: 0 };
  added.push(w);
}
const lines = added.map(w => `• ${w.fi} = ${w.ar} (${w.en})`).join('\n');
const reply = added.length
  ? `✅ ضفت ${added.length} كلمة${data.chapter ? ' من ' + data.chapter : ''}:\n${lines}\n\nهنراجعهم بالتكرار المتباعد. تحب نبدأ بأول كلمة دلوقتي؟`
  : '⚠️ ملقيتش كلمات جديدة واضحة في الصورة' + (known.length ? ' (كلهم متسجلين قبل كده)' : '') + '. ابعت صورة أوضح لصفحة الـ sanasto.';
return [{ json: { reply, payload: JSON.stringify(state, null, 1) } }];
