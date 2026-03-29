const { getSupabaseConfig } = require('../_lib/auth');

module.exports = async (_req, res) => {
  const { url, anonKey } = getSupabaseConfig();
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({
    supabaseUrl: url || '',
    supabaseAnonKey: anonKey || ''
  }));
};
