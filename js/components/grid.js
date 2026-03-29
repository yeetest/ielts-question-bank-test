import { state } from '../state.js';
import { renderContentTags, cleanTitle } from '../utils.js';

function setCount(text) {
  const el = document.getElementById('total-count');
  if (el) el.textContent = text;
}

function renderSpeaking(grid, tab, filteredData) {
  const data = filteredData !== null ? filteredData : (tab === 'part1' ? state.part1Data : state.part2Data);
  document.getElementById('tab-part1').classList.toggle('active', tab === 'part1');
  document.getElementById('tab-part2').classList.toggle('active', tab === 'part2');
  setCount(`${data.length} topics · ${tab === 'part1' ? 'Part 1' : 'Part 2 + Part 3'}`);

  data.forEach((item, idx) => {
    const questions = item.questions || item.part3 || [];
    let title = tab === 'part1'
      ? item.topic_en
      : cleanTitle(item.cue_card?.prompt || item.topic || '');
    if (title.length > 80) title = title.slice(0, 79) + '…';

    const card = document.createElement('div');
    card.className = 'card';
    const originalData = tab === 'part1' ? state.part1Data : state.part2Data;
    card.dataset.idx = filteredData !== null ? originalData.indexOf(item) : idx;
    card.dataset.tab = tab;
    card.innerHTML = `
      <div class="card-title">${title}</div>
      <div class="card-meta">${questions.length} questions</div>
      ${renderContentTags(item.content_tags)}
    `;
    grid.appendChild(card);
  });
}

function renderWriting(grid, tab) {
  const data = tab === 'task1' ? state.writingTask1Data : state.writingTask2Data;
  document.getElementById('tab-part1').classList.toggle('active', tab === 'task1');
  document.getElementById('tab-part2').classList.toggle('active', tab === 'task2');
  setCount(`${data.length} prompts · ${tab === 'task1' ? 'Task 1' : 'Task 2'}`);

  data.forEach((item, idx) => {
    const title = item.title || `Task ${tab === 'task1' ? '1' : '2'}`;
    const preview = item.promptLead || item.prompt.split('\n').filter(Boolean)[0] || '';
    const card = document.createElement('div');
    card.className = 'card';
    card.dataset.idx = idx;
    card.dataset.tab = tab;
    card.innerHTML = `
      <div class="card-title">${title}</div>
      <div class="card-meta">${tab === 'task1' ? 'Task 1' : 'Task 2'}</div>
      ${renderContentTags(item.content_tags)}
      <div class="card-copy">${preview}</div>
    `;
    grid.appendChild(card);
  });
}

export function renderGrid(tab, filteredData = null) {
  state.currentTab = tab;
  const grid = document.getElementById('grid');
  grid.innerHTML = '';

  if (state.currentSection === 'speaking') {
    renderSpeaking(grid, tab, filteredData);
    return;
  }

  renderWriting(grid, tab);
}
