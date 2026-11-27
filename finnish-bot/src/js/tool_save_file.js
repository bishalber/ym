const inp = $('When called').first().json;
const path = String(inp.path || '').trim().replace(/^\/+/, '');
if (!/^(lessons|notes|homework)\/[A-Za-z0-9._\/-]+$/.test(path) || path.includes('..')) throw new Error('path must look like lessons/2026-12-01-topic.md (folders: lessons, notes, homework)');
return [{ json: { url: __BASE__ + '/' + path, payload: String(inp.content || ''), result: 'Saved ' + path } }];
