const {
  readJson,
  issueVerification,
  validateIdentity
} = require('../_lib/auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.statusCode = 405;
    res.end('Method Not Allowed');
    return;
  }

  const body = await readJson(req);
  if (!validateIdentity(body.identity, body.mode)) {
    res.statusCode = 400;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'Invalid email or phone number.' }));
    return;
  }

  const { normalized, code, token } = issueVerification(body.identity, body.mode);
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({
    ok: true,
    identity: normalized,
    verificationToken: token,
    previewCode: process.env.NODE_ENV === 'production' ? undefined : code
  }));
};
