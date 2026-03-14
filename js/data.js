import { state } from './state.js';
import { renderGrid } from './components/grid.js';
import { renderSidebar } from './components/sidebar.js';

export async function loadData() {
  const [part1, part2, taxonomyRows] = await Promise.all([
    fetch('merged_part1.json').then(r => r.json()),
    fetch('merged_part2.json').then(r => r.json()),
    fetch('data/topic_taxonomy_v2_final.json').then(r => r.json()),
  ]);

  state.part1Data = part1;
  state.part2Data = part2;
  state.taxonomyV2Map = new Map(
    (taxonomyRows || []).map(row => [
      (row.topic || '').trim(),
      { l1: row.l1 || null, l2: row.l2 || null, l3: row.l3 || null },
    ])
  );

  // Attach taxonomy_v2 primary mapping to each topic object for filtering.
  state.part1Data.forEach(topic => {
    const key = (topic.topic_en || '').trim();
    topic.taxonomy_v2_primary = state.taxonomyV2Map.get(key) || null;
  });
  state.part2Data.forEach(topic => {
    const key = (topic.topic || '').trim();
    topic.taxonomy_v2_primary = state.taxonomyV2Map.get(key) || null;
  });

  renderGrid('part1');
  renderSidebar(); // render sidebar after data is available
}
