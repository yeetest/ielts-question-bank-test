const { createHmac, timingSafeEqual } = require('node:crypto');

function getSecret() {
  return process.env.AUTH_SESSION_SECRET || 'local-static-auth-secret';
}

function sign(raw) {
  return createHmac('sha256', getSecret()).update(raw).digest('hex');
}

function encode(data) {
  const raw = Buffer.from(JSON.stringify(data)).toString('base64url');
  return `${raw}.${sign(raw)}`;
}

function decode(token) {
  if (!token || !token.includes('.')) return null;
  const [raw, sig] = token.split('.');
  const expected = sign(raw);
  const left = Buffer.from(sig);
  const right = Buffer.from(expected);
  if (left.length !== right.length || !timingSafeEqual(left, right)) return null;
  try {
    return JSON.parse(Buffer.from(raw, 'base64url').toString('utf8'));
  } catch {
    return null;
  }
}

function serializeCookie(name, value, options = {}) {
  const parts = [`${name}=${value}`];
  if (options.httpOnly) parts.push('HttpOnly');
  if (options.sameSite) parts.push(`SameSite=${options.sameSite}`);
  if (options.secure) parts.push('Secure');
  if (options.path) parts.push(`Path=${options.path}`);
  if (typeof options.maxAge === 'number') parts.push(`Max-Age=${options.maxAge}`);
  return parts.join('; ');
}

function parseCookies(req) {
  const header = req.headers.cookie || '';
  return Object.fromEntries(
    header
      .split(';')
      .map(item => item.trim())
      .filter(Boolean)
      .map(item => {
        const idx = item.indexOf('=');
        return [item.slice(0, idx), item.slice(idx + 1)];
      })
  );
}

async function readJson(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString('utf8');
  return raw ? JSON.parse(raw) : {};
}

function getSupabaseConfig() {
  return {
    url: process.env.SUPABASE_URL || '',
    anonKey: process.env.SUPABASE_ANON_KEY || ''
  };
}

async function verifySupabaseAccessToken(accessToken) {
  const { url, anonKey } = getSupabaseConfig();
  if (!url || !anonKey) {
    const error = new Error('Missing SUPABASE_URL or SUPABASE_ANON_KEY.');
    error.statusCode = 500;
    throw error;
  }

  const response = await fetch(`${url}/auth/v1/user`, {
    headers: {
      apikey: anonKey,
      Authorization: `Bearer ${accessToken}`
    }
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) return null;
  const email = String(payload?.email || '').trim().toLowerCase();
  if (!email) return null;
  return {
    identity: email,
    credits: 0
  };
}

function readSession(req) {
  const token = parseCookies(req).ielts_session;
  const payload = decode(token);
  if (!payload || payload.kind !== 'session') return null;
  return {
    identity: payload.identity,
    credits: payload.credits
  };
}

function writeSession(res, session) {
  const token = encode({
    kind: 'session',
    identity: session.identity,
    credits: session.credits,
    iat: Date.now()
  });
  res.setHeader('Set-Cookie', serializeCookie('ielts_session', token, {
    httpOnly: true,
    sameSite: 'Lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 60 * 60 * 24 * 14
  }));
}

function clearSession(res) {
  res.setHeader('Set-Cookie', serializeCookie('ielts_session', '', {
    httpOnly: true,
    sameSite: 'Lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 0
  }));
}

module.exports = {
  readJson,
  getSupabaseConfig,
  verifySupabaseAccessToken,
  readSession,
  writeSession,
  clearSession
};
