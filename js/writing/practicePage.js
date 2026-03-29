import { loadData, practiceIdFromURL } from '../shared/data.js';
import { closeAuthModal, currentAccessToken, ensureActionAccess, refreshSession } from './auth.js';
import { state } from '../shared/state.js';
import { bindWritingPractice, renderWritingPractice } from './writingPractice.js';

function getWritingTaskById(taskId) {
  return [...state.writingTask1Data, ...state.writingTask2Data].find(item => item.id === taskId) || null;
}

function renderMissingState() {
  const root = document.getElementById('practice-root');
  root.innerHTML = `
    <div class="writing-page">
      <section class="writing-pane">
        <div class="writing-empty-copy">未找到对应题目，请返回题库重新进入。</div>
        <div class="button-inline">
          <button class="secondary-btn" id="back-to-bank">返回题库</button>
        </div>
      </section>
    </div>
  `;
  document.getElementById('back-to-bank')?.addEventListener('click', () => {
    window.location.assign('./?section=writing');
  });
}

async function renderPractice(taskId) {
  const task = getWritingTaskById(taskId);
  if (!task) {
    renderMissingState();
    return;
  }

  state.currentSection = 'writing';
  state.currentTab = task.type === 'task1' ? 'task1' : 'task2';
  state.activeWritingContext = { taskId: task.id };

  const root = document.getElementById('practice-root');
  root.innerHTML = renderWritingPractice(task);

  bindWritingPractice(task, () => renderPractice(task.id), {
    ensureActionAccess,
    runAiCorrection: async (_task, essay) => {
      const response = await fetch('/api/ai', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${currentAccessToken()}`
        },
        body: JSON.stringify({
          prompt: task.prompt,
          taskType: task.type,
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
      return {
        ok: true,
        feedback: payload.feedback || null,
        revisedEssay: payload.band9_rewrite || '',
        revisionNote: payload.revision_note || payload.revision_notes || '',
        keywordOutline: payload.keyword_outline || ''
      };
    },
    exitPractice: () => {
      window.location.assign(`./?section=writing&tab=${task.type === 'task1' ? 'task1' : 'task2'}`);
    }
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  document.getElementById('auth-close-btn')?.addEventListener('click', closeAuthModal);
  document.getElementById('auth-overlay')?.addEventListener('click', event => {
    if (event.target === document.getElementById('auth-overlay')) {
      closeAuthModal();
    }
  });

  try {
    await loadData({ render: false });
    await refreshSession();
  } catch (error) {
    console.error(error);
    renderMissingState();
    return;
  }

  const taskId = practiceIdFromURL();
  await renderPractice(taskId);
});
