const PROMPT = __PROMPT__;
const SCHEMA = __SCHEMA__;
const SCENARIOS = ['at the supermarket (kauppa)', 'buying bus/train tickets and asking directions', 'doctor and pharmacy (lääkäri, apteekki)', 'Kela / TE-toimisto / Migri paperwork', 'job interview and workplace small talk', 'renting a flat and talking to the landlord', 'phone call: making and changing an appointment', 'café / restaurant ordering', 'school, daycare and neighbours', 'bank, post office and parcels'];
const scenario = SCENARIOS[now.ordinal % SCENARIOS.length];
const FOCUS = {
  1: 'GRAMMAR from Suomen Mestari at his current chapter: one rule, 3 examples, then practice sentences.',
  2: 'REAL LIFE: role-play vocabulary and phrases for: ' + scenario + '.',
  3: 'YKI SPEAKING (puhuminen): short spoken answers and one role-play task at basic level.',
  4: 'YKI READING + WRITING: a short notice/message with questions, and a 30-60 word writing task.',
  5: 'SENTENCE BUILDING: turn words into full sentences, then weekly review of the hardest words.',
  6: 'YKI LISTENING-style DICTATION and pronunciation (double letters, ä/ö/y) plus mnemonics recap.',
  7: 'LIGHT REVIEW: spaced repetition of due words, one easy real-life dialogue, rest day tone.'
};
const notesArr = (parse(body('Get notes'), { notes: [] }).notes || []).slice(-40);
const vocab = parse(body('Get vocab'), { words: {} }).words || {};
const all = Object.values(vocab);
const due = all.filter(w => w.due <= ymd(0)).sort((a, b) => a.box - b.box).slice(0, 10);
const known = Object.keys(vocab).slice(-300);
const INSTR = `\n\nTASK: Create TODAY'S DAILY LESSON as JSON matching the schema. Rules: exactly 5 new_words (not in known_words), each with a fresh Egyptian-Arabic mnemonic; 4 sentences that reuse new words and due_words; all Finnish must be correct (vowel harmony, case endings, partitive, time expressions); Arabic in Egyptian dialect; "real_life.lines" is a short dialogue of 4-6 lines; "yki" is ONE task matching today's focus; "question" is exactly ONE first question for him to answer in the chat (retrieval of a due word is a good choice); keep every field short because he reads on a phone. Use his current textbook position from the notes if any note mentions a chapter (kappale/kpl); otherwise assume Suomen Mestari 1, kappale 3-4 revision. Do not claim anything about specific textbook pages.`;
const user = JSON.stringify({ date: ymd(0), weekday: now.toFormat('cccc'), focus: FOCUS[now.weekday], scenario, notes: notesArr, due_words: due.map(w => ({ fi: w.fi, ar: w.ar, en: w.en })), known_words: known });
const request = { model: __MODEL__, max_tokens: 6000, output_config: { format: { type: 'json_schema', schema: SCHEMA } }, system: PROMPT + INSTR, messages: [{ role: 'user', content: user }] };
return [{ json: { body: request } }];
