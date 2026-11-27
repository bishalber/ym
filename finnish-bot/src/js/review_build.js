const state = parse(body('Get vocab'), { words: {} });
const due = Object.values(state.words || {}).filter(w => w.due <= ymd(0)).sort((a, b) => (a.box - b.box) || a.due.localeCompare(b.due));
let msg, md;
if (!due.length) {
  msg = '🎉 مفيش كلمات مستحقة للمراجعة النهارده. كمل بكرة!';
  md = `# Review ${ymd(0)}\n\nNo words due.\n`;
} else {
  const first = due[0];
  const rest = due.slice(1, 6).map(w => `• ${w.fi} = ${w.ar} (${w.en})`).join('\n');
  msg = `🔁 مراجعة المساء\nعندك ${due.length} كلمة مستحقة.\n\n❓ أول كلمة: ما معنى "${first.fi}"؟ (اكتب بالعربي أو الإنجليزي)\n${first.mnemonic ? '(تلميح ممكن لو احتجته)' : ''}\n\nبعدها هسألك على الباقي واحدة واحدة.`;
  md = `# Review question asked ${ymd(0)}\n\nAsked: meaning of "${first.fi}" (answer: ${first.ar} / ${first.en}${first.mnemonic ? '; hint: ' + first.mnemonic : ''}).\nStill due after it:\n${rest || '(none)'}\nGrade each answer with vocab_grade.\n`;
}
return [{ json: { msg, reviewUrl: __BASE__ + '/lessons/' + ymd(0) + '-review.md', reviewMd: md } }];
