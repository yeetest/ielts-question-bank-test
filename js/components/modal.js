import { state } from '../state.js';
import { authState, ensureActionAccess, refreshSession } from '../auth.js';
import { renderSkillBadge, renderInlineTopicTags, renderContentTags, cleanTitle } from '../utils.js';
import { openTagSummary, openTypeSummary } from './tagSummary.js';
import {
  attemptCloseWritingModal,
  bindWritingPractice,
  renderWritingPractice
} from './writingPractice.js';

export function openOverlay() {
  document.getElementById('overlay').classList.add('open');
}

export function closeOverlay() {
  const finishClose = () => {
    document.getElementById('overlay').classList.remove('open');
    document.getElementById('modal').classList.remove('modal-wide');
    state.activeWritingContext = null;
  };

  if (!state.activeWritingContext) {
    finishClose();
    return;
  }

  attemptCloseWritingModal().then(allowed => {
    if (allowed) finishClose();
  });
}

export function openModal(tab, idx) {
  if (tab === 'task1' || tab === 'task2') {
    const item = tab === 'task1' ? state.writingTask1Data[idx] : state.writingTask2Data[idx];
    const modal = document.getElementById('modal');
    state.activeWritingContext = { tab, idx, taskId: item.id };
    modal.classList.add('modal-wide');
    document.getElementById('modal-content').innerHTML = renderWritingPractice(item);
    openOverlay();
    bindWritingPractice(item, () => openModal(tab, idx), {
      ensureActionAccess,
      runAiCorrection: async (_task, essay) => {
        return runAiCorrection(item, essay);
      },
      refreshSession: async () => {
        await refreshSession();
      }
    });
    return;
  }

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

async function runAiCorrection(item, essay) {
  const response = await fetch('/api/ai', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt: item.prompt,
      essay
    })
  });
  const payload = await response.json();
  await refreshSession();
  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      error: payload.error || 'AI correction failed.'
    };
  }

  authState.session = payload.session || authState.session;
  return {
    ok: true,
    feedback: payload.feedback || null,
    revisedEssay: payload.band9_rewrite || ''
  };
}
