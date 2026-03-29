const { readJson, readSession, writeSession } = require('./_lib/auth');

async function requestOpenRouter(taskPrompt, essay) {
  const apiKey = process.env.OPENROUTER_API_KEY;
  const model = process.env.OPENROUTER_MODEL;

  if (!apiKey) {
    const error = new Error('Missing OPENROUTER_API_KEY.');
    error.statusCode = 500;
    throw error;
  }

  if (!model) {
    const error = new Error('Missing OPENROUTER_MODEL.');
    error.statusCode = 500;
    throw error;
  }

  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model,
      temperature: 0.3,
      max_tokens: 1200,
      messages: [
        {
          role: 'system',
          content: `
You are an IELTS examiner and expert writing coach.

Evaluate the essay using IELTS band descriptors and return JSON only.

Requirements:
- Each feedback criterion: max 2 sentences
- Keep feedback concise
- Band 9 rewrite: 250–300 words, do NOT exceed 300 words

Return format:
{
  "feedback": {
    "overall_band": number,
    "task_achievement": { "band": number, "comments": string },
    "coherence_cohesion": { "band": number, "comments": string },
    "lexical_resource": { "band": number, "comments": string },
    "grammatical_range": { "band": number, "comments": string },
    "key_improvements": string[]
  },
  "band9_rewrite": string
}

Do NOT output anything outside JSON.
`
        },
        {
          role: 'user',
          content: `TASK:\n${taskPrompt}\n\nESSAY:\n${essay}`
        }
      ]
    })
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(payload?.error?.message || payload?.message || `OpenRouter request failed with status ${response.status}.`);
    error.statusCode = 502;
    throw error;
  }

  const raw = payload?.choices?.[0]?.message?.content;
  if (typeof raw !== 'string' || !raw.trim()) {
    const error = new Error('OpenRouter returned an empty response.');
    error.statusCode = 502;
    throw error;
  }

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    const error = new Error('OpenRouter returned invalid JSON.');
    error.statusCode = 502;
    throw error;
  }

  const feedback = parsed?.feedback;
  const rewrite = parsed?.band9_rewrite;
  if (
    !feedback ||
    typeof feedback !== 'object' ||
    typeof feedback.overall_band !== 'number' ||
    !feedback.task_achievement ||
    !feedback.coherence_cohesion ||
    !feedback.lexical_resource ||
    !feedback.grammatical_range ||
    !Array.isArray(feedback.key_improvements) ||
    typeof rewrite !== 'string'
  ) {
    const error = new Error('OpenRouter response did not match the required feedback + rewrite format.');
    error.statusCode = 502;
    throw error;
  }

  return {
    feedback,
    band9_rewrite: rewrite.trim()
  };
}

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

  if (session.credits <= 0) {
    res.statusCode = 403;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'No credits left.' }));
    return;
  }

  const body = await readJson(req);
  const essay = String(body.essay || '').trim();
  if (!essay) {
    res.statusCode = 400;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'Essay text is required.' }));
    return;
  }

  let result;
  try {
    result = await requestOpenRouter(String(body.prompt || ''), essay);
  } catch (error) {
    res.statusCode = error.statusCode || 500;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: error.message || 'AI correction failed.' }));
    return;
  }

  const nextSession = {
    ...session,
    credits: Math.max(session.credits - 1, 0)
  };

  writeSession(res, nextSession);
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({
    feedback: result.feedback,
    band9_rewrite: result.band9_rewrite,
    session: nextSession
  }));
};
