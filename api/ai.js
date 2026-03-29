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
    const fenceMatch = text.match(/^```(?:json)?\s*([\s\S]*?)\s*```/im);
    if (fenceMatch?.[1]) {
      return fenceMatch[1].trim();
    }
  }

  const balanced = extractBalancedJsonObject(text);
  if (balanced) return balanced;

  const firstBrace = text.indexOf('{');
  const lastBrace = text.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
    return text.slice(firstBrace, lastBrace + 1).trim();
  }

  return text;
}

/** Prefer over first/last `}` — fixes wrong slice when strings contain `}` or output has trailing text. */
function extractBalancedJsonObject(text) {
  const start = text.indexOf('{');
  if (start === -1) return null;
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = start; i < text.length; i += 1) {
    const ch = text[i];
    if (escape) {
      escape = false;
      continue;
    }
    if (inString) {
      if (ch === '\\') escape = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') {
      inString = true;
      continue;
    }
    if (ch === '{') depth += 1;
    else if (ch === '}') {
      depth -= 1;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return null;
}

function getAssistantTextContent(message) {
  const c = message?.content;
  if (typeof c === 'string') return c;
  if (Array.isArray(c)) {
    return c
      .map(part => {
        if (typeof part === 'string') return part;
        if (part?.type === 'text' && typeof part.text === 'string') return part.text;
        return '';
      })
      .join('');
  }
  return '';
}

// Verbatim Band 9 wording from the official public document:
// "IELTS Writing band descriptors" (updated May 2023), https://cdn.ielts.org/Guides/ielts-writing-band-descriptors.pdf
// Task 1 and Task 2 share identical Coherence & Cohesion at Band 9 — store once to cut input tokens.

const OFFICIAL_BAND9_COHERENCE = `
Coherence & Cohesion:
The message can be followed effortlessly.
Cohesion is used in such a way that it very rarely attracts attention.
Any lapses in coherence or cohesion are minimal.
Paragraphing is skilfully managed.
`.trim();

const OFFICIAL_TASK1_BAND9 = `
Writing Task 1 — Band 9 (official descriptor text):

Task Achievement:
All the requirements of the task are fully and appropriately satisfied.
There may be extremely rare lapses in content.

${OFFICIAL_BAND9_COHERENCE}

Lexical Resource:
Full flexibility and precise use are evident within the scope of the task.
A wide range of vocabulary is used accurately and appropriately with very natural and sophisticated control of lexical features.
Minor errors in spelling and word formation are extremely rare and have minimal impact on communication.

Grammatical Range & Accuracy:
A wide range of structures within the scope of the task is used with full flexibility and control.
Punctuation and grammar are used appropriately throughout.
Minor errors are extremely rare and have minimal impact on communication
`.trim();

const OFFICIAL_TASK2_BAND9 = `
Writing Task 2 — Band 9 (official descriptor text):

Task Response:
The prompt is appropriately addressed and explored in depth.
A clear and fully developed position is presented which directly answers the question/s.
Ideas are relevant, fully extended and well supported.
Any lapses in content or support are extremely rare.

${OFFICIAL_BAND9_COHERENCE}

Lexical Resource:
Full flexibility and precise use are widely evident.
A wide range of vocabulary is used accurately and appropriately with very natural and sophisticated control of lexical features.
Minor errors in spelling and word formation are extremely rare and have minimal impact on communication.

Grammatical Range & Accuracy:
A wide range of structures is used with full flexibility and control.
Punctuation and grammar are used appropriately throughout.
Minor errors are extremely rare and have minimal impact on communication
`.trim();

function buildAssessmentSystemPrompt(taskType) {
  const t = taskType === 'task1' ? 'Task 1; first criterion = Task Achievement.' : 'Task 2; first criterion = Task Response (JSON key still task_achievement).';
  return `IELTS General Training examiner. Score using public Writing band descriptors (May 2023): https://cdn.ielts.org/Guides/ielts-writing-band-descriptors.pdf
${t}
Output a single raw JSON object only — no markdown, no \`\`\` fences, no text before or after the object.
Shape:
{"overall_band":number,"criteria":{"task_achievement":{"band":number,"comments":string},"coherence_cohesion":{"band":number,"comments":string},"lexical_resource":{"band":number,"comments":string},"grammatical_range_accuracy":{"band":number,"comments":string}}}
Per criterion: band + at most 2 short sentences in comments (keep comments compact).
For each criterion, briefly explain why the score is not higher: identify the main gap between the awarded band and Band 9, using the relevant band descriptors for both on that criterion. Do not give praise-only comments; each comment must clearly justify the score.
The user message includes STUDENT_ESSAY: its line breaks and blank lines are the candidate's paragraphing as submitted (not stripped). For coherence_cohesion, do not claim there is no paragraphing or a single wall of text when breaks are visible; only critique organisation if paragraphing is weak, unclear, or missing relative to the descriptors.
CRITICAL: comments must be valid JSON strings — escape every " as \\" inside comments; use \\n for newlines.`.trim();
}

function buildRewriteSystemPrompt(taskType) {
  const band9Block = taskType === 'task1' ? OFFICIAL_TASK1_BAND9 : OFFICIAL_TASK2_BAND9;
  const hint =
    taskType === 'task1'
      ? 'Task 1: full letter/email; tone; greeting/closing; all bullets.'
      : 'Task 2: full essay; intro, body, conclusion.';
  return `IELTS GT writing coach — produce model answer + brief revision_notes only (do not rescore).

Band 9 = official wording below (May 2023 PDF). revised_essay must meet it; keep student's ideas where sensible; natural English.
${hint} Words: Task1≥150, Task2≥250.

revision_notes: each of structure/content/grammar/vocabulary = 2–5 tight sentences (no long essays).

User message includes EXAMINER_ASSESSMENT_JSON — use to prioritise fixes.
Preserve the student's paragraph breaks in revised_essay unless a clearer structure is needed; match their grouping where sensible.

${band9Block}

Output a single raw JSON object only — no markdown or code fences.
{"revised_essay":string,"revision_notes":{"structure":string,"content":string,"grammar":string,"vocabulary":string}}
CRITICAL: escape every " inside string values as \\"; use \\n for line breaks inside JSON strings.`.trim();
}

function normaliseCriteria(criteria) {
  return {
    task_achievement: {
      band: criteria.task_achievement.band,
      comment: String(criteria.task_achievement.comment || criteria.task_achievement.comments || '').trim()
    },
    coherence_cohesion: {
      band: criteria.coherence_cohesion.band,
      comment: String(criteria.coherence_cohesion.comment || criteria.coherence_cohesion.comments || '').trim()
    },
    lexical_resource: {
      band: criteria.lexical_resource.band,
      comment: String(criteria.lexical_resource.comment || criteria.lexical_resource.comments || '').trim()
    },
    grammatical_range_accuracy: {
      band: criteria.grammatical_range_accuracy.band,
      comment: String(
        criteria.grammatical_range_accuracy.comment || criteria.grammatical_range_accuracy.comments || ''
      ).trim()
    }
  };
}

async function openRouterJson({ apiKey, model, max_tokens, system, user }) {
  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model,
      max_tokens,
      response_format: { type: 'json_object' },
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: user }
      ]
    })
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(payload?.error?.message || payload?.message || `OpenRouter request failed with status ${response.status}.`);
    error.statusCode = 502;
    throw error;
  }

  const choice = payload?.choices?.[0];
  const finishReason = choice?.finish_reason;
  const raw = getAssistantTextContent(choice?.message);
  if (!String(raw).trim()) {
    const error = new Error('OpenRouter returned an empty response.');
    error.statusCode = 502;
    throw error;
  }

  const candidates = [
    () => JSON.parse(String(raw).trim()),
    () => JSON.parse(extractJsonPayload(raw)),
    () => JSON.parse(extractBalancedJsonObject(String(raw)) || '')
  ];

  let lastErr = null;
  for (const tryParse of candidates) {
    try {
      const out = tryParse();
      if (out && typeof out === 'object') return out;
    } catch (e) {
      lastErr = e;
    }
  }

  const preview = String(raw).replace(/\s+/g, ' ').slice(0, 280);
  let msg = `OpenRouter returned JSON that could not be parsed (${lastErr?.message || 'unknown'}). Preview: ${preview}`;
  if (finishReason === 'length') {
    msg +=
      ' Response hit max_tokens (finish_reason=length). Raise OPENROUTER_MAX_TOKENS_ASSESSMENT or OPENROUTER_MAX_TOKENS_REWRITE.';
  }
  const error = new Error(msg);
  error.statusCode = 502;
  throw error;
}

function intEnv(name, fallback) {
  const v = process.env[name];
  if (v === undefined || v === '') return fallback;
  const n = parseInt(v, 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

async function requestOpenRouter(taskPrompt, essay, taskType) {
  const apiKey = process.env.OPENROUTER_API_KEY;
  const model = process.env.OPENROUTER_MODEL;
  const modelAssessment = process.env.OPENROUTER_MODEL_ASSESSMENT || model;

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

  // Assessment JSON was truncating around ~1100 tokens; defaults must fit 4 criteria + overhead.
  const maxAssess = intEnv('OPENROUTER_MAX_TOKENS_ASSESSMENT', 4096);
  const maxRewrite = intEnv('OPENROUTER_MAX_TOKENS_REWRITE', 8192);

  const userTaskBlock = `TASK_TYPE: ${taskType}\n\nTASK:\n${taskPrompt}\n\nSTUDENT_ESSAY (line breaks = candidate's paragraph breaks as typed):\n${essay}`;

  const assessment = await openRouterJson({
    apiKey,
    model: modelAssessment,
    max_tokens: maxAssess,
    system: buildAssessmentSystemPrompt(taskType),
    user: userTaskBlock
  });

  const overallBand = assessment?.overall_band;
  const criteriaRaw = assessment?.criteria;
  if (
    typeof overallBand !== 'number' ||
    !criteriaRaw ||
    typeof criteriaRaw !== 'object' ||
    !criteriaRaw.task_achievement ||
    !criteriaRaw.coherence_cohesion ||
    !criteriaRaw.lexical_resource ||
    !criteriaRaw.grammatical_range_accuracy
  ) {
    const error = new Error('OpenRouter (assessment step) did not return valid overall_band and criteria.');
    error.statusCode = 502;
    throw error;
  }

  const criteria = normaliseCriteria(criteriaRaw);

  const rewritePayload = await openRouterJson({
    apiKey,
    model,
    max_tokens: maxRewrite,
    system: buildRewriteSystemPrompt(taskType),
    user: `${userTaskBlock}\n\nEXAMINER_ASSESSMENT_JSON:\n${JSON.stringify({ overall_band: overallBand, criteria: assessment.criteria })}`
  });

  const rewrite = rewritePayload?.revised_essay;
  const revisionNote = rewritePayload?.revision_notes;
  if (typeof rewrite !== 'string' || !revisionNote || typeof revisionNote !== 'object') {
    const error = new Error('OpenRouter (rewrite step) did not return revised_essay and revision_notes.');
    error.statusCode = 502;
    throw error;
  }

  return {
    overall_band: overallBand,
    criteria,
    revised_essay: rewrite.trim(),
    revision_notes: {
      structure: String(revisionNote.structure || '').trim(),
      content: String(revisionNote.content || '').trim(),
      grammar: String(revisionNote.grammar || '').trim(),
      vocabulary: String(revisionNote.vocabulary || '').trim()
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
