import { state } from './state.js';
import { renderGrid } from './components/grid.js';

export async function loadData() {
  [state.part1Data, state.part2Data] = await Promise.all([
    fetch('merged_part1.json').then(r => r.json()),
    fetch('merged_part2.json').then(r => r.json()),
  ]);
  renderGrid('part1');
}
