const TZ = 'Europe/Helsinki';
const body = (n) => { try { const j = $(n).first().json; return j.statusCode === 200 ? String(j.body || '') : ''; } catch (e) { return ''; } };
const parse = (s, d) => { try { const v = JSON.parse(s); return v || d; } catch (e) { return d; } };
const now = $now.setZone(TZ);
const ymd = (n) => now.plus({ days: n }).toFormat('yyyy-LL-dd');
