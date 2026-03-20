import { state } from './state.js';
import { renderGrid } from './components/grid.js';
import { renderSidebar } from './components/sidebar.js';

export const QUARTER_IDS = Object.freeze(['2026-01-to-04', '2026-05-to-08']);

export const QUARTER_LABELS = Object.freeze({
  '2026-01-to-04': 'Jan–Apr 2026',
  '2026-05-to-08': 'May–Aug 2026',
});

export function quarterFromURL() {
  try {
    const q = new URLSearchParams(window.location.search).get('quarter');
    if (q && QUARTER_IDS.includes(q)) return q;
  } catch {
    /* ignore */
  }
  return '2026-01-to-04';
}

export function quarterDataBase(quarterId) {
  return `data/quarters/${quarterId}/`;
}

export function setQuarterInURL(quarterId) {
  const u = new URL(window.location.href);
  u.searchParams.set('quarter', quarterId);
  history.replaceState(null, '', `${u.pathname}${u.search}${u.hash}`);
}

function updateChromeForQuarter(quarterId) {
  const label = document.getElementById('quarter-label');
  if (label) {
    const base = QUARTER_LABELS[quarterId] || quarterId;
    const suffix = quarterId === '2026-05-to-08' ? ' · placeholder' : '';
    label.textContent = base + suffix;
  }
  document.title = `IELTS Speaking Question Bank — ${QUARTER_LABELS[quarterId] || quarterId}`;
  const sel = document.getElementById('quarter-select');
  if (sel) sel.value = quarterId;
}

export async function loadData(quarterId) {
  const base = quarterDataBase(quarterId);
  const [part1, part2, taxonomyRows] = await Promise.all([
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
  ]);

  state.currentQuarterId = quarterId;
  state.part1Data = part1;
  state.part2Data = part2;
  state.taxonomyV2Map = new Map(
    (taxonomyRows || []).map(row => [
      (row.topic || '').trim(),
      { l1: row.l1 || null, l2: row.l2 || null, l3: row.l3 || null },
    ])
  );

  state.part1Data.forEach(topic => {
    const key = (topic.topic_en || '').trim();
    topic.taxonomy_v2_primary = state.taxonomyV2Map.get(key) || null;
  });
  state.part2Data.forEach(topic => {
    const key = (topic.topic || '').trim();
    topic.taxonomy_v2_primary = state.taxonomyV2Map.get(key) || null;
  });

  updateChromeForQuarter(quarterId);
  renderGrid(state.currentTab);
  renderSidebar();
}
