const {
  readSession,
  writeSession,
  verifySupabaseAccessToken
} = require('../_lib/auth');

module.exports = async (req, res) => {
  const authHeader = req.headers.authorization || '';
  const bearer = authHeader.startsWith('Bearer ') ? authHeader.slice(7).trim() : '';
  let session = null;

  if (bearer) {
    try {
      const verified = await verifySupabaseAccessToken(bearer);
      if (verified) {
        const existing = readSession(req);
        session = existing && existing.identity === verified.identity
          ? existing
          : verified;
        session = {
          ...session,
          userId: verified.userId,
          identity: verified.identity,
          credits: verified.credits
        };
        writeSession(res, session);
      }
    } catch (error) {
      res.statusCode = error.statusCode || 500;
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify({ error: error.message || 'Session sync failed.', session: null }));
      return;
    }
  } else {
    session = readSession(req);
  }

  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({ session }));
};
