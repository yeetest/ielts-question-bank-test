import { state } from '../state.js';
import { renderContentTags, cleanTitle } from '../utils.js';

export function renderGrid(tab) {
  state.currentTab = tab;

  // Update tab button active state
  document.getElementById('tab-part1').classList.toggle('active', tab === 'part1');
  document.getElementById('tab-part2').classList.toggle('active', tab === 'part2');

  const grid = document.getElementById('grid');
  grid.innerHTML = '';

  const data = tab === 'part1' ? state.part1Data : state.part2Data;
  document.getElementById('total-count').textContent =
    `${data.length} topics · Part ${tab === 'part1' ? '1' : '2'}`;

  data.forEach((item, idx) => {
    const questions = item.questions || item.part3 || [];

    // Truncate long titles to 80 chars
    let title = tab === 'part1'
      ? item.topic_en
      : cleanTitle(item.cue_card?.prompt || item.topic || '');
    if (title.length > 80) title = title.slice(0, 79) + '…';

    const card = document.createElement('div');
    card.className = 'card';
    card.dataset.idx = idx;   // store index so click handler knows which topic to open
    card.dataset.tab = tab;

    card.innerHTML = `
      <div class="card-title">${title}</div>
      <div class="card-meta">${questions.length} questions</div>
      ${renderContentTags(item.content_tags)}
    `;

    grid.appendChild(card);
  });
}
