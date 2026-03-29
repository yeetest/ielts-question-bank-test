const { readSession } = require('../_lib/auth');

module.exports = async (req, res) => {
  const session = readSession(req);
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({ session }));
};
