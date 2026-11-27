const read = (r) => JSON.parse(r.content.filter(c => c.type === 'text').map(c => c.text).join(''));
let L, checked = true;
try { L = read($('Claude check').first().json); }
catch (e) { checked = false; L = read($('Claude lesson').first().json); }
const state = parse(body('Get vocab'), { words: {} });
if (!state.words) state.words = {};
let added = 0;
for (const w of L.new_words) {
  const key = String(w.fi || '').trim().toLowerCase();
  if (!key || state.words[key]) continue;
  state.words[key] = { fi: w.fi.trim(), ar: w.ar, en: w.en, example: w.example_fi, mnemonic: w.mnemonic_ar, chapter: 'daily ' + ymd(0), box: 1, due: ymd(1), added: ymd(0), lapses: 0, seen: 0 };
  added++;
}
const words = L.new_words.map((w, i) => `${i + 1}. ${w.fi} = ${w.ar} (${w.en})\n   ${w.example_fi} = ${w.example_ar}\n   💡 ${w.mnemonic_ar}`).join('\n');
const sents = L.sentences.map(s => `• ${s.fi}\n  ${s.ar}`).join('\n');
const dlg = L.real_life.lines.map(l => `${l.who}: ${l.fi}\n   ${l.ar}`).join('\n');
const msg = `📘 ${L.title}\n${L.intro_ar}\n\n🆕 كلمات النهارده\n${words}\n\n🧩 جمل\n${sents}\n\n📐 قاعدة\n${L.grammar_ar}\n\n🏪 موقف حقيقي\n${L.real_life.scenario_ar}\n${dlg}\n\n🎯 YKI (${L.yki.skill})\n${L.yki.task_fi}\n${L.yki.task_ar}\n\n📝 واجب: ${L.homework_ar}\n\n❓ سؤال واحد:\n${L.question.fi}\n${L.question.ar}${checked ? '' : '\n\n(⚠️ الدرس ماتراجعش لغوياً الليلة)'}`;
const md = `# ${L.title}\n\nDate: ${ymd(0)}\n\n${msg}\n`;
return [{ json: { msg, lessonUrl: __BASE__ + '/lessons/' + ymd(0) + '.md', lessonMd: md, vocabPayload: JSON.stringify(state, null, 1), added } }];
