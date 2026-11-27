const text = String(__TEXT__ || '').trim() || '…';
const chat_id = __CHAT__;
const out = [];
let rest = text;
while (rest.length > 3900) {
  let cut = rest.lastIndexOf('\n', 3900);
  if (cut < 1000) cut = 3900;
  out.push(rest.slice(0, cut));
  rest = rest.slice(cut).replace(/^\n+/, '');
}
out.push(rest);
return out.map(t => ({ json: { chat_id, text: t } }));
