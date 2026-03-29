import { state } from './state.js';
import { renderGrid } from './components/grid.js';
import { renderSidebar } from './components/sidebar.js';

export const SECTIONS = Object.freeze(['speaking', 'writing']);

export function sectionFromURL() {
  const u = new URL(window.location.href);
  const section = u.searchParams.get('section');
  return SECTIONS.includes(section) ? section : 'writing';
}

export function setSectionInURL(section) {
  const u = new URL(window.location.href);
  u.searchParams.set('section', section);
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

export async function loadData() {
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
  const list = (writingPayload?.questions || []).map(item => ({
    ...item,
    content_tags: null
  }));
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

  updateChrome();
  renderGrid(state.currentTab);
  renderSidebar();
}
