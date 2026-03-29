import { authState } from '../auth.js';
import { state } from '../state.js';

const WORKSPACE_KEY = 'ielts_writing_workspace_v2';
const LIBRARY_KEY = 'ielts_writing_library_v2';
const EMPTY_FLASHCARD_MESSAGE = '当前你还没有高光选中你想要学习的表达，快去右侧 sample 部分选中吧';

let activeController = null;
let selectionHandler = null;

const LOCAL_DICTIONARY = {
  outstanding: '杰出的，出色的',
  professionalism: '专业素养',
  adaptable: '适应能力强的',
  cohesion: '衔接，连贯',
  compelling: '有说服力的',
  pragmatic: '务实的',
  allocate: '分配',
  commitment: '投入，承诺',
  flexibility: '灵活性',
  resilience: '韧性',
  sustainable: '可持续的',
  beneficial: '有益的',
  decisive: '决定性的',
  outweigh: '超过，胜过',
  responsible: '负责任的'
};

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function readJsonStorage(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || '{}');
  } catch {
    return {};
  }
}

function writeJsonStorage(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function userLibraryKey(session = authState.session) {
  return session?.identity || 'anonymous';
}

function buildSampleAnswer(task) {
  if (task.type === 'task1') {
    return [
      'Dear Sir or Madam,',
      '',
      'I am writing to express my appreciation for the moving service your company recently provided when I relocated to my new flat. Overall, the experience was efficient, professional and far less stressful than I had anticipated.',
      '',
      'The most impressive aspect of the service was the team’s punctuality and organisation. The movers arrived exactly on time, packed the remaining loose items carefully, and handled my furniture with considerable care. As a result, the entire move was completed smoothly and within the period originally promised.',
      '',
      'I would also like to commend one member of staff in particular, Daniel, whose attitude was outstanding throughout the day. He remained polite, patient and reassuring, especially when I was concerned about several fragile boxes containing kitchenware and books. His professionalism made an excellent impression.',
      '',
      'The only area that could be improved was the communication on the evening before the move. I was not given a clear final arrival window until rather late, which made it difficult to organise the rest of my day. Even so, the quality of the actual service was excellent.',
      '',
      'Thank you again for such a positive experience. I would certainly recommend your company to others.',
      '',
      'Yours faithfully,'
    ].join('\n');
  }

  return [
    'In many cases, this trend is beneficial overall, even though it may create some short-term inconvenience. I believe it should generally be regarded as a positive development because its long-term advantages are more significant than its immediate drawbacks.',
    '',
    'Admittedly, some people oppose this kind of change because it may disrupt established habits or impose extra costs in the beginning. Individuals often have to adapt their routines, and in some cases they may feel uncertain about the practical consequences. These concerns are understandable, particularly when the transition happens quickly or without enough support.',
    '',
    'However, the broader picture is much more positive. Developments of this kind often encourage people to make more responsible decisions and to think beyond their immediate comfort. In the long run, this can improve personal well-being, reduce unnecessary harm and create benefits for society as a whole. Even when adaptation is required at first, the lasting gains usually outweigh the temporary inconvenience.',
    '',
    'Furthermore, positive change rarely occurs without some degree of adjustment. If every policy or social shift were rejected simply because it was inconvenient at the start, progress would be extremely limited. A more balanced judgement should consider whether the long-term outcome is constructive, and in this case it clearly is.',
    '',
    'In conclusion, although there may be some initial disadvantages, I consider this to be a positive development because the lasting benefits are both wider and more meaningful.'
  ].join('\n');
}

function buildFlashcards(highlights = []) {
  return highlights.map(item => ({
    id: item.id,
    english: item.text,
    chinese: item.translation
  }));
}

function defaultWorkspace(task) {
  return {
    taskId: task.id,
    essay: '',
    activeTab: 'sample',
    viewMode: 'practice',
    viewTaskId: task.id,
    correctionResult: null,
    highlights: [],
    flashcards: [],
    sidebarCollapsed: false,
    flashcardIndex: 0,
    flashcardAnswerVisible: false,
    selectionText: '',
    selectionTranslation: '',
    dirty: false
  };
}

function getWorkspaceStore() {
  return readJsonStorage(WORKSPACE_KEY);
}

function setWorkspaceStore(store) {
  writeJsonStorage(WORKSPACE_KEY, store);
}

function normalizeWorkspace(task, value) {
  const base = defaultWorkspace(task);
  const merged = { ...base, ...(value || {}) };
  merged.highlights = Array.isArray(merged.highlights) ? merged.highlights : [];
  merged.flashcards = Array.isArray(merged.flashcards) && merged.flashcards.length
    ? merged.flashcards
    : buildFlashcards(merged.highlights);
  return merged;
}

export function getWritingWorkspace(task) {
  const store = getWorkspaceStore();
  return normalizeWorkspace(task, store[task.id]);
}

export function patchWritingWorkspace(task, patch) {
  const store = getWorkspaceStore();
  const next = {
    ...getWritingWorkspace(task),
    ...patch
  };
  if (patch.highlights) {
    next.flashcards = buildFlashcards(next.highlights);
  }
  store[task.id] = next;
  setWorkspaceStore(store);
  return next;
}

function getLibraryStore() {
  return readJsonStorage(LIBRARY_KEY);
}

function setLibraryStore(store) {
  writeJsonStorage(LIBRARY_KEY, store);
}

function getUserLibrary(session = authState.session) {
  const store = getLibraryStore();
  return store[userLibraryKey(session)] || {};
}

function getSavedRecord(taskId, session = authState.session) {
  return getUserLibrary(session)[taskId] || null;
}

function getLibraryRecords(session = authState.session) {
  return Object.values(getUserLibrary(session)).sort((a, b) => (b.savedAt || '').localeCompare(a.savedAt || ''));
}

function createPracticeRecord(task, workspace) {
  return {
    taskId: task.id,
    title: task.title,
    type: task.type,
    prompt: task.prompt,
    sampleAnswer: buildSampleAnswer(task),
    originalEssay: workspace.essay,
    correctionResult: workspace.correctionResult,
    highlights: workspace.highlights,
    flashcards: buildFlashcards(workspace.highlights),
    savedAt: new Date().toISOString()
  };
}

function savePracticeRecord(task, session = authState.session) {
  if (!session) return null;

  const workspace = getWritingWorkspace(task);
  if (!workspace.correctionResult) return null;

  const store = getLibraryStore();
  const key = userLibraryKey(session);
  const library = store[key] || {};
  const record = createPracticeRecord(task, workspace);
  library[task.id] = record;
  store[key] = library;
  setLibraryStore(store);

  patchWritingWorkspace(task, {
    dirty: false,
    viewMode: 'record',
    viewTaskId: task.id
  });

  return record;
}

function lookupTranslation(text) {
  const normalized = String(text || '').trim().toLowerCase().replace(/[^\w\s-]/g, '');
  if (!normalized) return '';
  const firstWord = normalized.split(/\s+/)[0];
  return LOCAL_DICTIONARY[firstWord] || `暂未收录，建议结合上下文确认：${text.trim()}`;
}

function renderHighlightedText(text, highlights) {
  const unique = [...new Set((highlights || []).map(item => item.text).filter(Boolean))].sort((a, b) => b.length - a.length);
  let html = escapeHtml(text);
  unique.forEach(item => {
    const escaped = item.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    html = html.replace(new RegExp(escaped, 'g'), `<mark class="inline-highlight">${escapeHtml(item)}</mark>`);
  });
  return html.replace(/\n/g, '<br>');
}

function getViewTask(task, workspace) {
  if (workspace.viewMode === 'practice') {
    return task;
  }

  const records = getLibraryRecords();
  const matched = records.find(item => item.taskId === workspace.viewTaskId);
  return matched || task;
}

function renderFeedbackCards(correctionResult) {
  const feedback = correctionResult?.feedback;
  if (!feedback || typeof feedback !== 'object') {
    return '<div class="muted">No correction result yet. Use “Correct My Essay” to generate the combined IELTS feedback and revised Band 9 version.</div>';
  }

  return `
    <div class="writing-feedback-grid">
      ${[
        {
          title: 'Overall Band',
          band: feedback.overall_band,
          comments: Array.isArray(feedback.key_improvements)
            ? feedback.key_improvements.join(' ')
            : ''
        },
        {
          title: 'Task Achievement / Task Response',
          band: feedback.task_achievement?.band,
          comments: feedback.task_achievement?.comments
        },
        {
          title: 'Coherence & Cohesion',
          band: feedback.coherence_cohesion?.band,
          comments: feedback.coherence_cohesion?.comments
        },
        {
          title: 'Lexical Resource',
          band: feedback.lexical_resource?.band,
          comments: feedback.lexical_resource?.comments
        },
        {
          title: 'Grammatical Range & Accuracy',
          band: feedback.grammatical_range?.band,
          comments: feedback.grammatical_range?.comments
        }
      ].map(item => `
        <div class="feedback-card-mini">
          <div class="section-label">${escapeHtml(item.title)}</div>
          <div><strong>${escapeHtml(item.band)}</strong></div>
          <div>${escapeHtml(item.comments || '')}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderLibrarySidebar(task, workspace) {
  const records = getLibraryRecords();
  const currentViewKey = `${workspace.viewMode}:${workspace.viewTaskId || task.id}`;

  return `
    <aside class="writing-library-panel${workspace.sidebarCollapsed ? ' is-collapsed' : ''}">
      <div class="writing-library-head">
        <button class="secondary-btn" id="writing-library-toggle">${workspace.sidebarCollapsed ? '▶' : '◀'}</button>
        ${workspace.sidebarCollapsed ? '' : '<div class="section-label">Personal Writing Library</div>'}
      </div>
      ${workspace.sidebarCollapsed ? '' : `
        <button class="library-nav-btn${currentViewKey === `practice:${task.id}` ? ' active' : ''}" data-library-view="practice" data-library-task="${task.id}">
          Return to Question Page
        </button>
        <div class="section-label">My Practice Records</div>
        <div class="library-tree">
          ${records.length ? records.map(record => `
            <div class="library-question${record.taskId === workspace.viewTaskId ? ' active' : ''}">
              <div class="library-question-title">${escapeHtml(record.title)}</div>
              <div class="library-children">
                <button class="library-child-btn${currentViewKey === `record:${record.taskId}` ? ' active' : ''}" data-library-view="record" data-library-task="${record.taskId}">My Practice Record</button>
                <button class="library-child-btn${currentViewKey === `sample:${record.taskId}` ? ' active' : ''}" data-library-view="sample" data-library-task="${record.taskId}">Sample Band 9</button>
                <button class="library-child-btn${currentViewKey === `flashcards:${record.taskId}` ? ' active' : ''}" data-library-view="flashcards" data-library-task="${record.taskId}">Practice High-Score Expressions</button>
              </div>
            </div>
          `).join('') : '<div class="muted">No saved practice records yet.</div>'}
        </div>
      `}
    </aside>
  `;
}

function renderPracticeView(task, workspace) {
  const sampleAnswer = buildSampleAnswer(task);
  const revisedEssay = workspace.correctionResult?.revisedEssay || '';
  const rightPanelText = workspace.activeTab === 'sample' ? sampleAnswer : revisedEssay;
  const highlightedHtml = renderHighlightedText(rightPanelText, workspace.highlights);

  return `
    <div class="writing-main-view">
      <div class="writing-prompt">
        <div class="section-label">Prompt</div>
        <div class="prompt-prewrap">${escapeHtml(task.prompt)}</div>
      </div>

      <div class="writing-layout">
        <section class="writing-pane writing-pane-left">
          <div class="writing-pane-head">
            <h3>Writing Editor</h3>
            <div class="writing-save-status">
              <span>${workspace.dirty ? 'Unsaved changes' : 'All manual changes saved'}</span>
            </div>
          </div>
          <textarea id="writing-essay-input" class="writing-textarea" placeholder="Write or paste your essay here.">${escapeHtml(workspace.essay)}</textarea>
          <div class="writing-notes">
            <div class="section-label">Save Rule</div>
            <p>Your workspace is restored locally, but only “Save to My Private Template Library” creates the official writing-library record shown in the sidebar.</p>
          </div>
        </section>

        <section class="writing-pane writing-pane-right">
          <div class="writing-pane-head">
            <div class="tabs writing-tabs">
              <button class="tab${workspace.activeTab === 'sample' ? ' active' : ''}" data-writing-tab="sample">Sample Band 9</button>
              <button class="tab${workspace.activeTab === 'revised' ? ' active' : ''}" data-writing-tab="revised">My Revised Band 9</button>
            </div>
          </div>

          ${workspace.activeTab === 'sample' ? `
            <div class="writing-reading-panel writing-highlight-surface" id="writing-reading-panel" data-highlight-source="sample">${highlightedHtml}</div>
            <div class="writing-tab-note">Use the sample for reference, but build your own private high-score version and expression library from your own correction result.</div>
          ` : workspace.correctionResult ? `
            ${renderFeedbackCards(workspace.correctionResult)}
            <div class="writing-reading-panel writing-highlight-surface" id="writing-reading-panel" data-highlight-source="revised">${highlightedHtml}</div>
            <div class="button-inline writing-cta-row">
              <button class="secondary-btn" id="writing-save-library">Save to My Private Template Library</button>
            </div>
          ` : `
            <div class="writing-empty-state">
              <button class="secondary-btn primary-action-btn" id="writing-correct-essay">Correct My Essay</button>
            </div>
          `}

          <div class="writing-selection-bar" id="writing-selection-bar" hidden>
            <div>
              <div class="section-label">Selected text</div>
              <div id="writing-selected-text"></div>
              <div class="muted" id="writing-translation"></div>
            </div>
            <div class="button-inline">
              <button class="secondary-btn" id="writing-translate">Translate</button>
              <button class="secondary-btn" id="writing-save-highlight">Save Highlight</button>
            </div>
          </div>
        </section>
      </div>
    </div>
  `;
}

function renderRecordView(record) {
  return `
    <div class="writing-main-view">
      <div class="writing-prompt">
        <div class="section-label">${record.type === 'task1' ? 'Task 1' : 'Task 2'}</div>
        <div class="prompt-prewrap">${escapeHtml(record.prompt)}</div>
      </div>
      <div class="writing-record-grid">
        <section class="writing-pane">
          <div class="writing-pane-head">
            <h3>My Original Essay</h3>
            <div class="writing-save-status"><span>Saved record</span></div>
          </div>
          <div class="writing-reading-panel">${escapeHtml(record.originalEssay).replace(/\n/g, '<br>')}</div>
        </section>
        <section class="writing-pane">
          <div class="writing-pane-head">
            <h3>AI Correction Result</h3>
            <div class="writing-save-status"><span>${new Date(record.savedAt).toLocaleString()}</span></div>
          </div>
          ${renderFeedbackCards(record.correctionResult)}
          <div class="writing-reading-panel">${renderHighlightedText(record.correctionResult?.revisedEssay || '', record.highlights)}</div>
        </section>
      </div>
    </div>
  `;
}

function renderSavedSampleView(record) {
  return `
    <div class="writing-main-view">
      <div class="writing-prompt">
        <div class="section-label">Sample Band 9</div>
        <div class="prompt-prewrap">${escapeHtml(record.prompt)}</div>
      </div>
      <section class="writing-pane">
        <div class="writing-reading-panel">${renderHighlightedText(record.sampleAnswer, record.highlights)}</div>
      </section>
    </div>
  `;
}

function renderFlashcardsView(record, workspace) {
  const flashcards = record.flashcards || buildFlashcards(record.highlights);
  if (!flashcards.length) {
    return `
      <div class="writing-main-view">
        <section class="writing-pane">
          <div class="writing-empty-copy">${EMPTY_FLASHCARD_MESSAGE}</div>
        </section>
      </div>
    `;
  }

  const index = Math.min(workspace.flashcardIndex || 0, flashcards.length - 1);
  const current = flashcards[index];

  return `
    <div class="writing-main-view">
      <section class="writing-pane">
        <div class="writing-pane-head">
          <h3>Practice High-Score Expressions</h3>
          <div class="writing-save-status"><span>${index + 1} / ${flashcards.length}</span></div>
        </div>
        <div class="flashcard-shell">
          <div class="flashcard-face">
            <div class="section-label">Chinese -> English</div>
            <div class="flashcard-copy">${escapeHtml(current.chinese)}</div>
            ${workspace.flashcardAnswerVisible ? `<div class="flashcard-answer">${escapeHtml(current.english)}</div>` : '<div class="flashcard-answer muted">Think of the English expression first, then reveal the answer.</div>'}
          </div>
          <div class="button-inline">
            <button class="secondary-btn" id="flashcard-prev"${index === 0 ? ' disabled' : ''}>Previous</button>
            <button class="secondary-btn" id="flashcard-show">Show Answer</button>
            <button class="secondary-btn" id="flashcard-next"${index === flashcards.length - 1 ? ' disabled' : ''}>Next</button>
          </div>
        </div>
      </section>
    </div>
  `;
}

function renderMainView(task, workspace) {
  if (workspace.viewMode === 'practice') {
    return renderPracticeView(task, workspace);
  }

  const records = getLibraryRecords();
  const record = records.find(item => item.taskId === workspace.viewTaskId);
  if (!record) {
    return `
      <div class="writing-main-view">
        <section class="writing-pane">
          <div class="writing-empty-copy">Select a saved practice record from the sidebar.</div>
        </section>
      </div>
    `;
  }

  if (workspace.viewMode === 'record') return renderRecordView(record);
  if (workspace.viewMode === 'sample') return renderSavedSampleView(record);
  return renderFlashcardsView(record, workspace);
}

export function renderWritingPractice(task) {
  const workspace = getWritingWorkspace(task);
  const currentTask = getViewTask(task, workspace);

  return `
    <div class="writing-workspace" data-writing-task-id="${task.id}">
      <div class="writing-header">
        <div>
          <h2>${escapeHtml(currentTask.title || task.title)}</h2>
          <div class="section-label">${currentTask.type === 'task1' ? 'Task 1' : 'Task 2'}</div>
        </div>
        <div class="writing-save-status">
          <span>${authState.session ? escapeHtml(authState.session.identity) : 'Browse freely until you use protected actions'}</span>
          <span>${workspace.highlights.length} highlights</span>
        </div>
      </div>

      <div class="writing-shell">
        ${renderLibrarySidebar(task, workspace)}
        ${renderMainView(task, workspace)}
      </div>
    </div>
  `;
}

async function trySaveBeforeNavigation(task, onSaved = null) {
  const workspace = getWritingWorkspace(task);
  if (!workspace.dirty) return true;

  const hasResult = Boolean(workspace.correctionResult);
  const confirmed = window.confirm(
    hasResult
      ? 'You have unsaved changes. Click OK to save this result to My Private Template Library before leaving.'
      : 'You have unsaved draft changes. Click OK to keep them in the temporary workspace and leave this view, or Cancel to stay.'
  );

  if (!confirmed) return false;
  if (!hasResult) return true;

  if (!authState.session) {
    activeController?.hooks.ensureActionAccess({
      type: 'saveLibrary',
      requiresCredits: false,
      onAllowed: async () => {
        savePracticeRecord(task);
        if (typeof onSaved === 'function') onSaved();
        activeController?.reopen();
      }
    });
    return false;
  }

  savePracticeRecord(task);
  if (typeof onSaved === 'function') onSaved();
  return true;
}

function rerender() {
  activeController?.reopen();
}

function saveHighlight(task, source) {
  const selection = window.getSelection();
  const text = selection?.toString().trim();
  if (!text) return;

  const workspace = getWritingWorkspace(task);
  if (workspace.highlights.some(item => item.text === text)) return;

  patchWritingWorkspace(task, {
    highlights: [
      ...workspace.highlights,
      {
        id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
        text,
        translation: lookupTranslation(text),
        source,
        createdAt: new Date().toISOString()
      }
    ],
    selectionText: '',
    selectionTranslation: '',
    dirty: true
  });

  rerender();
}

function bindSelection(task) {
  const panel = document.getElementById('writing-reading-panel');
  const bar = document.getElementById('writing-selection-bar');
  if (!panel || !bar) return;

  const source = panel.dataset.highlightSource || 'sample';

  if (selectionHandler) {
    document.removeEventListener('selectionchange', selectionHandler);
  }

  selectionHandler = () => {
    if (!panel.contains(document.getSelection()?.anchorNode)) return;
    const text = document.getSelection()?.toString().trim() || '';
    if (!text) {
      bar.hidden = true;
      return;
    }

    bar.hidden = false;
    document.getElementById('writing-selected-text').textContent = text;
    document.getElementById('writing-translation').textContent = '';

    const workspace = getWritingWorkspace(task);
    patchWritingWorkspace(task, {
      selectionText: text,
      selectionTranslation: workspace.selectionTranslation
    });
  };

  document.addEventListener('selectionchange', selectionHandler);

  document.getElementById('writing-translate')?.addEventListener('click', () => {
    const workspace = getWritingWorkspace(task);
    const translation = lookupTranslation(workspace.selectionText);
    patchWritingWorkspace(task, { selectionTranslation: translation });
    document.getElementById('writing-translation').textContent = translation;
  });

  document.getElementById('writing-save-highlight')?.addEventListener('click', () => {
    saveHighlight(task, source);
  });
}

async function runCorrection(task) {
  const essayInput = document.getElementById('writing-essay-input');
  const essay = essayInput?.value.trim() || '';
  if (!essay) {
    alert('Paste or write your essay before running the correction.');
    return;
  }

  const response = await activeController.hooks.runAiCorrection(task, essay);
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      activeController.hooks.ensureActionAccess({
        type: 'correctEssay',
        requiresCredits: true,
        onAllowed: async () => {
          await runCorrection(task);
        }
      });
      return;
    }

    alert(response.error || 'AI correction failed.');
    return;
  }

  patchWritingWorkspace(task, {
    essay,
    activeTab: 'revised',
    viewMode: 'practice',
    viewTaskId: task.id,
    correctionResult: {
      feedback: response.feedback,
      revisedEssay: response.revisedEssay,
      correctedAt: new Date().toISOString()
    },
    dirty: true
  });

  rerender();
}

function bindSidebar(task) {
  document.getElementById('writing-library-toggle')?.addEventListener('click', () => {
    const workspace = getWritingWorkspace(task);
    patchWritingWorkspace(task, { sidebarCollapsed: !workspace.sidebarCollapsed });
    rerender();
  });

  document.querySelectorAll('[data-library-view]').forEach(button => {
    button.addEventListener('click', async () => {
      const nextView = button.dataset.libraryView;
      const nextTaskId = button.dataset.libraryTask;

      if (nextView === 'practice') {
        const allow = await trySaveBeforeNavigation(task, () => {
          activeController?.onReturnToQuestions();
        });
        if (!allow) return;
        activeController.onReturnToQuestions();
        return;
      }

      const allow = await trySaveBeforeNavigation(task, () => {
        patchWritingWorkspace(task, {
          viewMode: nextView,
          viewTaskId: nextTaskId
        });
      });
      if (!allow) return;

      patchWritingWorkspace(task, {
        viewMode: nextView,
        viewTaskId: nextTaskId
      });
      rerender();
    });
  });
}

function bindPracticeView(task) {
  const textarea = document.getElementById('writing-essay-input');
  textarea?.addEventListener('input', event => {
    patchWritingWorkspace(task, {
      essay: event.target.value,
      dirty: true
    });
  });

  document.querySelectorAll('[data-writing-tab]').forEach(button => {
    button.addEventListener('click', async () => {
      const allow = await trySaveBeforeNavigation(task, () => {
        patchWritingWorkspace(task, {
          activeTab: button.dataset.writingTab,
          viewMode: 'practice',
          viewTaskId: task.id
        });
      });
      if (!allow) return;

      patchWritingWorkspace(task, {
        activeTab: button.dataset.writingTab,
        viewMode: 'practice',
        viewTaskId: task.id
      });
      rerender();
    });
  });

  document.getElementById('writing-correct-essay')?.addEventListener('click', async () => {
    const allowed = activeController.hooks.ensureActionAccess({
      type: 'correctEssay',
      requiresCredits: true,
      onAllowed: async () => {
        await runCorrection(task);
      }
    });
    if (!allowed) return;
    await runCorrection(task);
  });

  document.getElementById('writing-save-library')?.addEventListener('click', async () => {
    const saveNow = async () => {
      const record = savePracticeRecord(task);
      if (!record) {
        alert('Run “Correct My Essay” first, then save the official record.');
        return;
      }
      rerender();
    };

    if (!authState.session) {
      activeController.hooks.ensureActionAccess({
        type: 'saveLibrary',
        requiresCredits: false,
        onAllowed: saveNow
      });
      return;
    }

    await saveNow();
  });

  bindSelection(task);
}

function bindFlashcards(task) {
  document.getElementById('flashcard-show')?.addEventListener('click', () => {
    patchWritingWorkspace(task, { flashcardAnswerVisible: true });
    rerender();
  });

  document.getElementById('flashcard-prev')?.addEventListener('click', () => {
    const workspace = getWritingWorkspace(task);
    patchWritingWorkspace(task, {
      flashcardIndex: Math.max((workspace.flashcardIndex || 0) - 1, 0),
      flashcardAnswerVisible: false
    });
    rerender();
  });

  document.getElementById('flashcard-next')?.addEventListener('click', () => {
    const workspace = getWritingWorkspace(task);
    const records = getLibraryRecords();
    const record = records.find(item => item.taskId === workspace.viewTaskId);
    const total = record?.flashcards?.length || record?.highlights?.length || 0;
    patchWritingWorkspace(task, {
      flashcardIndex: Math.min((workspace.flashcardIndex || 0) + 1, Math.max(total - 1, 0)),
      flashcardAnswerVisible: false
    });
    rerender();
  });
}

function bindBeforeUnload(task) {
  window.onbeforeunload = event => {
    if (!getWritingWorkspace(task).dirty) return undefined;
    event.preventDefault();
    event.returnValue = '';
    return '';
  };
}

export function bindWritingPractice(task, reopen, hooks) {
  activeController = {
    task,
    reopen,
    hooks,
    onReturnToQuestions: () => {
      if (selectionHandler) {
        document.removeEventListener('selectionchange', selectionHandler);
        selectionHandler = null;
      }
      window.onbeforeunload = null;
      state.activeWritingContext = null;
      activeController = null;
      document.getElementById('overlay').classList.remove('open');
      document.getElementById('modal').classList.remove('modal-wide');
    }
  };

  bindSidebar(task);
  bindPracticeView(task);
  bindFlashcards(task);
  bindBeforeUnload(task);
}

export async function attemptCloseWritingModal() {
  if (!activeController) return true;

  const allow = await trySaveBeforeNavigation(activeController.task, () => {
    if (selectionHandler) {
      document.removeEventListener('selectionchange', selectionHandler);
      selectionHandler = null;
    }
    window.onbeforeunload = null;
    activeController = null;
    state.activeWritingContext = null;
    document.getElementById('overlay').classList.remove('open');
    document.getElementById('modal').classList.remove('modal-wide');
  });
  if (!allow) return false;

  if (selectionHandler) {
    document.removeEventListener('selectionchange', selectionHandler);
    selectionHandler = null;
  }
  window.onbeforeunload = null;
  activeController = null;
  return true;
}
