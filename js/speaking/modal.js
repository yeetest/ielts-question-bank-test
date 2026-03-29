import { state } from '../shared/state.js';
import { renderSkillBadge, renderInlineTopicTags, renderContentTags, cleanTitle } from '../shared/utils.js';
import { openTagSummary, openTypeSummary } from './tagSummary.js';

export function openOverlay() {
  document.getElementById('overlay').classList.add('open');
}

export function closeOverlay() {
  document.getElementById('overlay').classList.remove('open');
  document.getElementById('modal').classList.remove('modal-wide');
}

export function openModal(tab, idx) {
  const item = tab === 'part1' ? state.part1Data[idx] : state.part2Data[idx];

  const hasBack = state.lastActiveTag || state.lastTypeSummary;
  const backBtn = hasBack ? `<button class="back-btn" id="back-btn">←</button>` : '';
  const topicTags = renderInlineTopicTags(item.content_tags);

  let html = '';

  if (tab === 'part1') {
    html = `
      ${backBtn}
      <h2>${item.topic_en}</h2>
      <div class="section-label">${item.season} · Part 1</div>
      ${renderContentTags(item.content_tags)}
      <div class="section-label" style="margin-top:14px">Questions</div>
      ${item.questions.map(q => {
        const primary = (q.skill_tags && q.skill_tags[0]) || '';
        const skillMatch = state.selectedSkillTags.length > 0
          && primary && state.selectedSkillTags.includes(primary);
        const subtypeMatch = state.selectedSkillSubtypes.length > 0
          && state.selectedSkillSubtypes.includes(q.skill_subtype);
        const timeMatch = state.selectedTimeFrame
          && q.time_frame === state.selectedTimeFrame;
        const match = skillMatch || subtypeMatch || timeMatch;
        return `<div class="q-row${match ? ' q-highlight' : ''}"><span>${q.text}${renderSkillBadge(q)}${topicTags}</span></div>`;
      }).join('')}
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
      ${p3.map(q => {
        const primary = (q.skill_tags && q.skill_tags[0]) || '';
        const skillMatch = state.selectedSkillTags.length > 0
          && primary && state.selectedSkillTags.includes(primary);
        const subtypeMatch = state.selectedSkillSubtypes.length > 0
          && state.selectedSkillSubtypes.includes(q.skill_subtype);
        const timeMatch = state.selectedTimeFrame
          && q.time_frame === state.selectedTimeFrame;
        const match = skillMatch || subtypeMatch || timeMatch;
        return `<div class="q-row${match ? ' q-highlight' : ''}"><span>${q.text}${renderSkillBadge(q)}${topicTags}</span></div>`;
      }).join('')}
    `;
  }

  document.getElementById('modal-content').innerHTML = html;
  openOverlay();

  const back = document.getElementById('back-btn');
  if (back) {
    back.addEventListener('click', () => {
      if (state.lastActiveTag) openTagSummary(state.lastActiveTag);
      else if (state.lastTypeSummary) openTypeSummary(state.lastTypeSummary);
    });
  }
}
