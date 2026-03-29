const { readJson, writeSession, verifySupabaseAccessToken, decrementProfileCredits } = require('./_lib/auth');

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
      max_tokens: 1200,
      response_format: {
        type: 'json_object'
      },
      messages: [
        {
          role: 'system',
          content: `
You are an IELTS General Training writing examiner and expert writing coach.

Evaluate the essay using IELTS General Training writing band descriptors and return JSON only.

Requirements:

1. Overall Band
- Return ONE overall band score
- Do NOT explain it

2. Four Criteria
For each:
- give a band score
- give 1–2 sentences (evaluation + suggestion)

Criteria:
- Task Achievement / Task Response
- Coherence & Cohesion
- Lexical Resource
- Grammatical Range & Accuracy

3. Revised Band 9 Essay
- based on the student's ideas, but revise where necessary
- follow Band 9 descriptors

Length:
- ${taskType === 'task1' ? 'Task 1: 150–200 words' : 'Task 2: 250–300 words'}

4. Revision Notes
Explain improvements in:
- Structure
- Content
- Grammar
- Vocabulary

Return format:
{
  "overall_band": number,
  "criteria": {
    "task_achievement": { "band": number, "comment": string },
    "coherence_cohesion": { "band": number, "comment": string },
    "lexical_resource": { "band": number, "comment": string },
    "grammatical_range_accuracy": { "band": number, "comment": string }
  },
  "revised_essay": string,
  "revision_notes": {
    "structure": string,
    "content": string,
    "grammar": string,
    "vocabulary": string
  }
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

  const overallBand = parsed?.overall_band;
  const criteria = parsed?.criteria;
  const rewrite = parsed?.revised_essay;
  const revisionNotes = parsed?.revision_notes;
  if (
    typeof overallBand !== 'number' ||
    !criteria ||
    typeof criteria !== 'object' ||
    !criteria.task_achievement ||
    !criteria.coherence_cohesion ||
    !criteria.lexical_resource ||
    !criteria.grammatical_range_accuracy ||
    typeof rewrite !== 'string' ||
    !revisionNotes ||
    typeof revisionNotes !== 'object' ||
    typeof revisionNotes.structure !== 'string' ||
    typeof revisionNotes.content !== 'string' ||
    typeof revisionNotes.grammar !== 'string' ||
    typeof revisionNotes.vocabulary !== 'string'
  ) {
    const error = new Error('OpenRouter response did not match the required score + criteria + revised essay + revision notes format.');
    error.statusCode = 502;
    throw error;
  }

  return {
    overall_band: overallBand,
    criteria,
    revised_essay: rewrite.trim(),
    revision_notes: {
      structure: revisionNotes.structure.trim(),
      content: revisionNotes.content.trim(),
      grammar: revisionNotes.grammar.trim(),
      vocabulary: revisionNotes.vocabulary.trim()
    }
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
    overall_band: result.overall_band,
    criteria: result.criteria,
    revised_essay: result.revised_essay,
    revision_notes: result.revision_notes,
    session: nextSession
  }));
};
