import { state } from '../state.js';
import { renderTypeTags, renderContentTags, cleanTitle } from '../utils.js';
import { openTagSummary, openTypeSummary } from './tagSummary.js';

export function openOverlay() {
  document.getElementById('overlay').classList.add('open');
}

export function closeOverlay() {
  document.getElementById('overlay').classList.remove('open');
}

export function openModal(tab, idx) {
  const item = tab === 'part1' ? state.part1Data[idx] : state.part2Data[idx];

  const hasBack = state.lastActiveTag || state.lastTypeSummary;
  const backBtn = hasBack ? `<button class="back-btn" id="back-btn">←</button>` : '';

  let html = '';

  if (tab === 'part1') {
    html = `
      ${backBtn}
      <h2>${item.topic_en}</h2>
      <div class="section-label">${item.season} · Part 1</div>
      ${renderContentTags(item.content_tags)}
      <div class="section-label" style="margin-top:14px">Questions</div>
      ${item.questions.map(q => `
        <div class="q-row"><span>${q.text}${renderTypeTags(q.type_tags)}</span></div>
      `).join('')}
    `;
  } else {
    const cc = item.cue_card || {};
    const p3 = item.part3 || [];
    html = `
      ${backBtn}
      <h2>${item.topic || item.topic_en || ''}</h2>
      <div class="section-label">${item.season} · Part 2 + 3</div>
      <div class="section-label">Cue Card</div>
      <div class="cue-card">
        <div class="prompt">${cleanTitle(cc.prompt || '')}</div>
        <ul>
          ${(cc.you_should_say || [])
            .filter(s => s && !/^you should say/i.test(s))
            .map(s => `<li>${s}</li>`)
            .join('')}
        </ul>
      </div>
      <div class="section-label">Part 3 Questions</div>
      ${p3.map(q => `
        <div class="q-row">
          <span>${q.text}${renderTypeTags(q.type_tags)}</span>
        </div>
      `).join('')}
    `;
  }

  document.getElementById('modal-content').innerHTML = html;
  openOverlay();

  // Wire up back button — returns to whichever summary was last open
  const back = document.getElementById('back-btn');
  if (back) {
    back.addEventListener('click', () => {
      if (state.lastActiveTag) openTagSummary(state.lastActiveTag);
      else if (state.lastTypeSummary) openTypeSummary(state.lastTypeSummary);
    });
  }
}
