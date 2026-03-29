import { state } from './state.js';
import { renderGrid } from '../components/grid.js';
import { renderSidebar } from '../speaking/sidebar.js';

export const SECTIONS = Object.freeze(['speaking', 'writing']);

function cleanWritingPrompt(prompt) {
  const text = String(prompt || '')
    .replace(/\r/g, '')
    .replace(/^WRITING TASK\s*[12]\s*/i, '')
    .replace(/You should spend about \d+ minutes on this task\.?/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  return text;
}

function normalizePromptForDedup(prompt) {
  return cleanWritingPrompt(prompt)
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[^a-z0-9 ]/g, '')
    .trim();
}

function extractLeadSentence(prompt) {
  const cleaned = cleanWritingPrompt(prompt);
  const paragraphs = cleaned.split(/\n+/).map(item => item.trim()).filter(Boolean);
  const lead = paragraphs.find(item => !/^write (a letter|about|an answer)/i.test(item) && !/^(in your letter|you should say|give reasons|include any relevant examples)/i.test(item));
  return (lead || paragraphs[0] || '').replace(/\s+/g, ' ').trim();
}

function extractCoreQuestion(prompt, type) {
  const cleaned = cleanWritingPrompt(prompt);
  const lines = cleaned
    .split(/\n+/)
    .map(item => item.trim().replace(/\s+/g, ' '))
    .filter(Boolean)
    .filter(item => !/^write (a letter|about|at least)/i.test(item))
    .filter(item => !/^give reasons/i.test(item))
    .filter(item => !/^include any relevant examples/i.test(item))
    .filter(item => !/^you should say/i.test(item));

  if (type === 'task2') {
    const directQuestion = lines.find(item => /\?$/.test(item) && item.length > 20);
    if (directQuestion) return directQuestion;
    const lastPromptLine = [...lines].reverse().find(item => item.length > 20);
    if (lastPromptLine) return lastPromptLine;
  }

  if (type === 'task1') {
    const instruction = lines.find(item => /^write a letter/i.test(item));
    if (instruction) return instruction;
  }

  return extractLeadSentence(cleaned);
}

function compactTitle(text, maxWords = 7) {
  const words = String(text || '').replace(/[.:]/g, '').split(/\s+/).filter(Boolean);
  return words.slice(0, maxWords).join(' ');
}

function inferTask1Tags(prompt) {
  const text = prompt.toLowerCase();
  const action = [
    ['complaint', /(complain|problem|not happy|poor service|damage|delay)/],
    ['request', /(request|ask for|want to know|need permission|arrange)/],
    ['invitation', /(invite|opening|celebrate|party|event)/],
    ['application', /(apply|application|job|position|manager|department)/],
    ['feedback', /(feedback|review|opinion|service)/],
    ['advice', /(advice|suggest|recommend|experience)/],
    ['apology', /(apolog|sorry)/],
    ['thanks', /(thank|appreciation|grateful)/]
  ].find(([, pattern]) => pattern.test(text))?.[0] || 'letter';

  const topic = [
    ['work', /(job|manager|company|department|career|staff|employee|theatre)/],
    ['study', /(college|university|course|study abroad|student|school)/],
    ['housing', /(apartment|flat|owner|rent|house|move|furniture)/],
    ['travel', /(trip|holiday|travel|tour|airport|hotel)/],
    ['service', /(service|company|shop|restaurant|removal|delivery)/],
    ['family', /(friend|sister|family|classmate)/],
    ['community', /(club|community|local|neighbour)/]
  ].find(([, pattern]) => pattern.test(text))?.[0] || 'general';

  return { l1: 'letter', l2: [action], l3: [topic] };
}

function inferTask2Tags(prompt) {
  const text = prompt.toLowerCase();
  const essayType = [
    ['opinion', /(do you agree|to what extent|your opinion|do you think)/],
    ['discussion', /(discuss both views|advantages and disadvantages|positive and negative)/],
    ['problem_solution', /(causes|problems|solutions|solve|what can be done)/],
    ['two_part', /(why is this|is this a positive|what are the reasons)/]
  ].find(([, pattern]) => pattern.test(text))?.[0] || 'general';

  const topic = [
    ['education', /(school|student|teacher|university|education|children)/],
    ['work', /(work|job|career|company|employee)/],
    ['technology', /(technology|computer|internet|online|media)/],
    ['environment', /(environment|pollution|energy|climate|transport)/],
    ['society', /(society|government|public|community|crime)/],
    ['health', /(health|exercise|food|medical)/],
    ['family', /(family|parent|child|children)/]
  ].find(([, pattern]) => pattern.test(text))?.[0] || 'general';

  return { l1: essayType, l2: [topic], l3: [] };
}

function buildWritingTitle(item, cleanedPrompt) {
  const lead = extractCoreQuestion(cleanedPrompt, item.type);
  if (item.type === 'task1') {
    return compactTitle(lead, 8) || 'Letter task';
  }
  return compactTitle(lead, 12) || 'Essay task';
}

function prepareWritingTasks(rawQuestions) {
  const seen = new Set();
  return rawQuestions
    .map(item => {
      const cleanedPrompt = cleanWritingPrompt(item.prompt);
      const dedupeKey = normalizePromptForDedup(cleanedPrompt);
      if (!cleanedPrompt || seen.has(dedupeKey)) return null;
      seen.add(dedupeKey);
      return {
        ...item,
        prompt: cleanedPrompt,
        title: buildWritingTitle(item, cleanedPrompt),
        promptLead: extractCoreQuestion(cleanedPrompt, item.type),
        content_tags: item.type === 'task1' ? inferTask1Tags(cleanedPrompt) : inferTask2Tags(cleanedPrompt),
        sampleAnswer: typeof item.sampleAnswer === 'string' && item.sampleAnswer.trim() ? item.sampleAnswer.trim() : ''
      };
    })
    .filter(Boolean);
}

export function sectionFromURL() {
  const u = new URL(window.location.href);
  const section = u.searchParams.get('section');
  return SECTIONS.includes(section) ? section : 'writing';
}

export function practiceIdFromURL() {
  const u = new URL(window.location.href);
  return u.searchParams.get('practice') || '';
}

export function writingTabFromURL() {
  const u = new URL(window.location.href);
  const tab = u.searchParams.get('tab');
  return tab === 'task2' ? 'task2' : 'task1';
}

export function setSectionInURL(section) {
  const u = new URL(window.location.href);
  u.searchParams.set('section', section);
  history.replaceState(null, '', `${u.pathname}${u.search}${u.hash}`);
}

export function setPracticeInURL(taskId) {
  const u = new URL(window.location.href);
  if (taskId) u.searchParams.set('practice', taskId);
  else u.searchParams.delete('practice');
  history.replaceState(null, '', `${u.pathname}${u.search}${u.hash}`);
}

function updateChrome() {
  const label = document.getElementById('section-meta');
  if (!label) return;

  if (state.currentSection === 'speaking') {
    document.title = 'IELTS Speaking Question Bank';
    label.textContent = 'Jan–Apr 2026';
    return;
  }

  document.title = 'IELTS Writing Question Bank';
  label.textContent = 'IELTS General Training Writing';
}

export async function loadData(options = {}) {
  const { render = true } = options;
  const base = 'data/quarters/2026-01-to-04/';
  const [part1, part2, taxonomyRows, writingPayload] = await Promise.all([
    fetch(`${base}merged_part1.json`).then(r => {
      if (!r.ok) throw new Error(`merged_part1: ${r.status}`);
      return r.json();
    }),
    fetch(`${base}merged_part2.json`).then(r => {
      if (!r.ok) throw new Error(`merged_part2: ${r.status}`);
      return r.json();
    }),
    fetch(`${base}topic_taxonomy_v2_final.json`).then(r => {
      if (!r.ok) throw new Error(`topic_taxonomy: ${r.status}`);
      return r.json();
    }),
    fetch('data/writing_questions.json').then(r => {
      if (!r.ok) throw new Error(`writing_questions: ${r.status}`);
      return r.json();
    })
  ]);

  state.part1Data = part1;
  state.part2Data = part2;
  state.taxonomyV2Map = new Map(
    (taxonomyRows || []).map(row => [
      (row.topic || '').trim(),
      { l1: row.l1 || null, l2: row.l2 || null, l3: row.l3 || null },
    ])
  );
  const list = prepareWritingTasks(writingPayload?.questions || []);
  state.writingTask1Data = list.filter(item => item.type === 'task1');
  state.writingTask2Data = list.filter(item => item.type === 'task2');

  state.part1Data.forEach(topic => {
    const key = (topic.topic_en || '').trim();
    topic.taxonomy_v2_primary = state.taxonomyV2Map.get(key) || null;
  });
  state.part2Data.forEach(topic => {
    const key = (topic.topic || '').trim();
    topic.taxonomy_v2_primary = state.taxonomyV2Map.get(key) || null;
  });

  if (render) {
    updateChrome();
    renderGrid(state.currentTab);
    renderSidebar();
  }
}
