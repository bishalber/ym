const msg = $('Telegram Trigger').first().json.message;
const key = Object.keys($input.first().binary || {})[0];
const buf = await this.helpers.getBinaryDataBuffer(0, key);
const SYSTEM = 'You extract vocabulary from a photo of a Finnish textbook page (Suomen Mestari) for an Egyptian-Arabic speaker who also reads English. Return ONLY words clearly visible on the page; skip anything unclear; never invent words. For each word give: fi (base form as printed), ar (short Egyptian Arabic meaning), en (English meaning), example (a short correct Finnish sentence, or empty), mnemonic (one short Arabic sound-alike/picture hint, or empty). chapter: the chapter/kappale if the caption or page says so, else empty.';
const schema = __SCHEMA__;
const request = {
  model: __MODEL__,
  max_tokens: 4000,
  output_config: { format: { type: 'json_schema', schema } },
  system: SYSTEM,
  messages: [{ role: 'user', content: [
    { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: buf.toString('base64') } },
    { type: 'text', text: 'Caption: ' + (msg.caption || '') }
  ] }]
};
return [{ json: { body: request } }];
