const {
  readJson,
  readSession,
  writeSession,
  verifySupabaseAccessToken,
  decrementProfileCredits
} = require('./_lib/auth');

function extractJsonPayload(raw) {
  const text = String(raw || '').trim();
  if (!text) return '';

  if (text.startsWith('```')) {
    const fenceMatch = text.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
    if (fenceMatch?.[1]) {
      return fenceMatch[1].trim();
    }
  }

  const firstBrace = text.indexOf('{');
  const lastBrace = text.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
    return text.slice(firstBrace, lastBrace + 1).trim();
  }

  return text;
}

async function requestOpenRouter(taskPrompt, essay, taskType) {
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
      response_format: {
        type: 'json_object'
      },
      messages: [
        {
          role: 'system',
          content: `
You are an IELTS examiner and expert writing coach.

Evaluate the essay using IELTS band descriptors and return JSON only.

Requirements:

1. Feedback
Briefly comment on the student's performance for each of the four IELTS criteria :
- Task Achievement / Task Response
- Coherence & Cohesion
- Lexical Resource
- Grammatical Range & Accuracy

For each criterion:
- briefly explain how the student performs according to the band descriptors and give a band score
- give short improvement suggestions
- keep it concise: maximum 2–3 sentences

2. Band 9 Rewrite
Write a Band 9 sample essay based on the student's essay.
- Use the most appropriate, natural, and precise expressions based on the student's original meaning, ideas, and general direction
- Do not force fancy vocabulary
- Length: ${taskType === 'task1' ? '150-200 words for task1' : '250-300 words for task2'}

3. Revision Note
After the rewrite, briefly explain how the revised version is improved in terms of:
- structure
- content
- grammar
- vocabulary
- etc

4. Keyword Outline
After the rewrite, provide a paragraph-by-paragraph keyword outline of the Band 9 rewrite.
Requirements:
- label each paragraph as P1, P2, P3, etc.
- use short keywords and arrows, not full sentences
- reflect the actual structure of the rewritten essay
- include the main idea and key supporting points for each paragraph

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
  "band9_rewrite": string,
  "revision_note": string,
  "keyword_outline": string
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
    parsed = JSON.parse(extractJsonPayload(raw));
  } catch {
    const error = new Error('OpenRouter returned invalid JSON.');
    error.statusCode = 502;
    throw error;
  }

  const feedback = parsed?.feedback;
  const rewrite = parsed?.band9_rewrite;
  const revisionNote = parsed?.revision_notes ?? parsed?.revision_note;
  const keywordOutline = parsed?.keyword_outline;
  if (
    !feedback ||
    typeof feedback !== 'object' ||
    typeof feedback.overall_band !== 'number' ||
    !feedback.task_achievement ||
    !feedback.coherence_cohesion ||
    !feedback.lexical_resource ||
    !feedback.grammatical_range ||
    !Array.isArray(feedback.key_improvements) ||
    typeof rewrite !== 'string' ||
    !revisionNote ||
    (typeof revisionNote !== 'string' && typeof revisionNote !== 'object') ||
    typeof keywordOutline !== 'string'
  ) {
    const error = new Error('OpenRouter response did not match the required feedback + rewrite + revision note + keyword outline format.');
    error.statusCode = 502;
    throw error;
  }

  return {
    feedback,
    band9_rewrite: rewrite.trim(),
    revision_note: typeof revisionNote === 'string'
      ? revisionNote.trim()
      : {
          structure: String(revisionNote.structure || '').trim(),
          content: String(revisionNote.content || '').trim(),
          grammar: String(revisionNote.grammar || '').trim(),
          vocabulary: String(revisionNote.vocabulary || '').trim()
        },
    keyword_outline: keywordOutline.trim()
  };
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.statusCode = 405;
    res.end('Method Not Allowed');
    return;
  }

  const authHeader = req.headers.authorization || '';
  const bearer = authHeader.startsWith('Bearer ') ? authHeader.slice(7).trim() : '';
  if (!bearer) {
    res.statusCode = 401;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'Login required.' }));
    return;
  }

  let session = null;
  try {
    session = await verifySupabaseAccessToken(bearer);
  } catch (error) {
    res.statusCode = error.statusCode || 500;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: error.message || 'Session verification failed.' }));
    return;
  }

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
  const taskType = body.taskType === 'task1' ? 'task1' : 'task2';
  if (!essay) {
    res.statusCode = 400;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'Essay text is required.' }));
    return;
  }

  let result;
  try {
    result = await requestOpenRouter(String(body.prompt || ''), essay, taskType);
  } catch (error) {
    res.statusCode = error.statusCode || 500;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: error.message || 'AI correction failed.' }));
    return;
  }

  let nextSession;
  try {
    nextSession = await decrementProfileCredits(bearer, session.userId, session.credits);
  } catch (error) {
    res.statusCode = error.statusCode || 500;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: error.message || 'Could not deduct credits.' }));
    return;
  }

  writeSession(res, nextSession);
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({
    feedback: result.feedback,
    band9_rewrite: result.band9_rewrite,
    revision_note: result.revision_note,
    keyword_outline: result.keyword_outline,
    session: nextSession
  }));
};
