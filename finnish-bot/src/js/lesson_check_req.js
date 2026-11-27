const SCHEMA = __SCHEMA__;
const res = $input.first().json;
if (res.error || !Array.isArray(res.content)) throw new Error('Claude error: ' + JSON.stringify(res.error || res).slice(0, 300));
const lesson = res.content.filter(c => c.type === 'text').map(c => c.text).join('');
const SYSTEM = 'You are a strict Finnish language proofreader and Egyptian-Arabic reviewer. You receive a lesson as JSON. Fix every error in the Finnish (spelling, vowel harmony, case endings, partitive, verb forms, time expressions, word meaning) and any wrong or unnatural Egyptian-Arabic/English meaning. Keep the same JSON structure, the same number of items and the same length. Do not add new content. Return only the corrected JSON.';
const request = { model: __MODEL__, max_tokens: 6000, output_config: { format: { type: 'json_schema', schema: SCHEMA } }, system: SYSTEM, messages: [{ role: 'user', content: lesson }] };
return [{ json: { body: request } }];
