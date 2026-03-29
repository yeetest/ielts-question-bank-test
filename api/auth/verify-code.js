const {
  readJson,
  verifyCode,
  writeSession
} = require('../_lib/auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.statusCode = 405;
    res.end('Method Not Allowed');
    return;
  }

  const body = await readJson(req);
  const session = verifyCode(body.verificationToken, body.code);
  if (!session) {
    res.statusCode = 400;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'Invalid or expired verification code.' }));
    return;
  }

  writeSession(res, session);
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({ ok: true, session }));
};
