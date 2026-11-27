const s = $('Put').first().json.statusCode;
if (![200, 201, 204].includes(s)) throw new Error('Nextcloud write failed (HTTP ' + s + '). Check the folder exists and the app password.');
return [{ json: { result: $('Logic').first().json.result } }];
