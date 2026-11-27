const PROMPT = __PROMPT__;
const notes = (parse(body('Get notes'), { notes: [] }).notes || []).slice(-40).map(n => `- (${n.date}) ${n.text}`).join('\n') || '(none yet)';
const all = Object.values(parse(body('Get vocab'), { words: {} }).words || {});
const due = all.filter(w => w.due <= ymd(0));
const lesson = body('Get lesson');
const review = body('Get review');
const system = PROMPT
  + `\n\nTODAY: ${now.toFormat('cccc d LLLL yyyy, HH:mm')} (Helsinki)`
  + `\nVOCAB STATS: ${all.length} words saved, ${due.length} due for review today.`
  + `\n\nSAVED NOTES (progress, repeated mistakes, preferences):\n${notes}`
  + (lesson ? `\n\nTODAY'S LESSON ALREADY SENT TO BISHU (continue from it, do not repeat it):\n${lesson}` : '')
  + (review ? `\n\nTODAY'S REVIEW QUESTION ALREADY SENT (grade his answer with vocab_grade):\n${review}` : '');
return [{ json: { system } }];
