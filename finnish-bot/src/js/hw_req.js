const msg = $('Telegram Trigger').first().json.message;
const key = Object.keys($input.first().binary || {})[0];
const buf = await this.helpers.getBinaryDataBuffer(0, key);
const HW = '\n\nTHIS MESSAGE IS A PHOTO OF HOMEWORK. Follow HOMEWORK PHOTOS. Reply in Egyptian Arabic, plain text, one line per answer: written -> correct -> ✔/❌ + short reason. Never guess unclear text. At the very end add ONE final line exactly like this: "MISTAKES: pattern 1 | pattern 2" (short English grammar patterns he got wrong) or "MISTAKES: none".';
const request = {
  model: __MODEL__,
  max_tokens: 3000,
  system: $('Build prompt').first().json.system + HW,
  messages: [{ role: 'user', content: [
    { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: buf.toString('base64') } },
    { type: 'text', text: msg.caption || 'Please check this homework.' }
  ] }]
};
return [{ json: { body: request } }];
