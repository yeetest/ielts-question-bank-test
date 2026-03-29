const { readSession, writeSession } = require('../_lib/auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.statusCode = 405;
    res.end('Method Not Allowed');
    return;
  }

  const session = readSession(req);
  if (!session) {
    res.statusCode = 401;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'Login required.' }));
    return;
  }

  const next = {
    ...session,
    credits: session.credits + 5
  };
  writeSession(res, next);
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({ ok: true, session: next }));
};
