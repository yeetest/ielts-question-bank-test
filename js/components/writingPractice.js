import { authState } from '../auth.js';
import { state } from '../state.js';

const WORKSPACE_KEY = 'ielts_writing_workspace_v3';
const LIBRARY_KEY = 'ielts_writing_library_v3';
const EMPTY_FLASHCARD_MESSAGE = '当前你还没有高光选中你想要学习的表达，快去右侧 sample 部分选中吧';

let activeController = null;
let selectionHandler = null;
let splitHandlers = null;

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

function readWorkspaceStore() {
  return readJsonStorage(WORKSPACE_KEY);
}

function writeWorkspaceStore(store) {
  writeJsonStorage(WORKSPACE_KEY, store);
}

function buildFlashcards(highlights = []) {
  return highlights.map(item => ({
    id: item.id,
    english: item.text,
    chinese: item.translation
  }));
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

function getSampleAnswer(task) {
  return task.sampleAnswer || buildSampleAnswer(task);
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
    editorWidth: 48,
    flashcardIndex: 0,
    flashcardAnswerVisible: false,
    selectionText: '',
    selectionTranslation: '',
    selectionX: 0,
    selectionY: 0,
    dirty: false
  };
}

function normalizeWorkspace(task, value) {
  const merged = { ...defaultWorkspace(task), ...(value || {}) };
  merged.highlights = Array.isArray(merged.highlights) ? merged.highlights : [];
  merged.flashcards = Array.isArray(merged.flashcards) && merged.flashcards.length
    ? merged.flashcards
    : buildFlashcards(merged.highlights);
  if (typeof merged.editorWidth !== 'number') merged.editorWidth = 48;
  merged.selectionText = '';
  merged.selectionTranslation = '';
  merged.selectionX = 0;
  merged.selectionY = 0;
  return merged;
}

export function getWritingWorkspace(task) {
  const store = readWorkspaceStore();
  return normalizeWorkspace(task, store[task.id]);
}

export function patchWritingWorkspace(task, patch) {
  const store = readWorkspaceStore();
  const next = {
    ...getWritingWorkspace(task),
    ...patch
  };
  if (patch.highlights) {
    next.flashcards = buildFlashcards(next.highlights);
  }
  store[task.id] = next;
  writeWorkspaceStore(store);
  return next;
}

function readLibraryStore() {
  return readJsonStorage(LIBRARY_KEY);
}

function writeLibraryStore(store) {
  writeJsonStorage(LIBRARY_KEY, store);
}

function getUserLibrary(session = authState.session) {
  const store = readLibraryStore();
  return store[userLibraryKey(session)] || {};
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
    sampleAnswer: getSampleAnswer(task),
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

  const store = readLibraryStore();
  const key = userLibraryKey(session);
  const nextLibrary = store[key] || {};
  nextLibrary[task.id] = createPracticeRecord(task, workspace);
  store[key] = nextLibrary;
  writeLibraryStore(store);

  patchWritingWorkspace(task, {
    dirty: false,
    viewMode: 'record',
    viewTaskId: task.id
  });

  return nextLibrary[task.id];
}

function lookupTranslation(text) {
  const normalized = String(text || '').trim().toLowerCase().replace(/[^\w\s-]/g, '');
  if (!normalized) return '';
  const word = normalized.split(/\s+/)[0];
  return LOCAL_DICTIONARY[word] || `暂未收录：${text.trim()}`;
}

function renderHighlightedText(text, highlights) {
  const unique = [...new Set((highlights || []).map(item => item.text).filter(Boolean))].sort((a, b) => b.length - a.length);
  let html = escapeHtml(text || '');
  unique.forEach(item => {
    const escaped = item.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    html = html.replace(new RegExp(escaped, 'g'), `<mark class="inline-highlight">${escapeHtml(item)}</mark>`);
  });
  return html.replace(/\n/g, '<br>');
}

function renderFeedbackCards(correctionResult) {
  const feedback = correctionResult?.feedback;
  if (!feedback || typeof feedback !== 'object') {
    return '<div class="muted">还没有批改结果。</div>';
  }

  const cards = [
    {
      title: 'Overall Band',
      band: feedback.overall_band,
      comments: Array.isArray(feedback.key_improvements) ? feedback.key_improvements.join(' ') : ''
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
  ];

  return `
    <div class="writing-feedback-grid">
      ${cards.map(item => `
        <div class="feedback-card-mini">
          <div class="section-label">${escapeHtml(item.title)}</div>
          <div><strong>${escapeHtml(item.band)}</strong></div>
          <div>${escapeHtml(item.comments || '')}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderFloatingSelection(workspace) {
  const hasSelection = Boolean(workspace.selectionText);
  const style = hasSelection
    ? `style="left:${workspace.selectionX}px; top:${workspace.selectionY}px;"`
    : '';
  return `
    <div class="writing-selection-float" id="writing-selection-float" ${hasSelection ? '' : 'hidden'} ${style}>
      <div class="button-inline">
        <button class="secondary-btn selection-btn" id="writing-translate">翻译</button>
        <button class="secondary-btn selection-btn" id="writing-save-highlight">保存到学习材料</button>
      </div>
      <div class="selection-translation-pop"${workspace.selectionTranslation ? '' : ' hidden'}>${escapeHtml(workspace.selectionTranslation)}</div>
    </div>
  `;
}

function renderLibrarySidebar(task, workspace) {
  const records = getLibraryRecords();
  const currentViewKey = `${workspace.viewMode}:${workspace.viewTaskId || task.id}`;

  return `
    <aside class="writing-library-panel${workspace.sidebarCollapsed ? ' is-collapsed' : ''}">
      <div class="writing-library-head">
        <button class="secondary-btn" id="writing-library-toggle">${workspace.sidebarCollapsed ? '展开' : '收起'}</button>
        ${workspace.sidebarCollapsed ? '' : '<div class="section-label">我的写作库</div>'}
      </div>
      ${workspace.sidebarCollapsed ? '' : `
        <button class="library-nav-btn${currentViewKey === `practice:${task.id}` ? ' active' : ''}" data-library-view="practice" data-library-task="${task.id}">
          返回题库
        </button>
        <div class="section-label">我的练习记录</div>
        <div class="library-tree">
          ${records.length ? records.map(record => `
            <div class="library-question${record.taskId === workspace.viewTaskId ? ' active' : ''}">
              <div class="library-question-title">${escapeHtml(record.title)}</div>
              <div class="library-children">
                <button class="library-child-btn${currentViewKey === `record:${record.taskId}` ? ' active' : ''}" data-library-view="record" data-library-task="${record.taskId}">我的练习</button>
                <button class="library-child-btn${currentViewKey === `sample:${record.taskId}` ? ' active' : ''}" data-library-view="sample" data-library-task="${record.taskId}">满分范文</button>
                <button class="library-child-btn${currentViewKey === `flashcards:${record.taskId}` ? ' active' : ''}" data-library-view="flashcards" data-library-task="${record.taskId}">高分表达</button>
              </div>
            </div>
          `).join('') : '<div class="muted">还没有保存的记录。</div>'}
        </div>
      `}
    </aside>
  `;
}

function renderPracticeView(task, workspace) {
  const sampleAnswer = getSampleAnswer(task);
  const revisedEssay = workspace.correctionResult?.revisedEssay || '';
  const rightText = workspace.activeTab === 'sample' ? sampleAnswer : revisedEssay;
  const editorWidth = Math.min(Math.max(workspace.editorWidth, 28), 72);

  return `
    <div class="writing-main-view">
      <div class="writing-prompt">
        <div class="section-label">${task.type === 'task1' ? 'Task 1' : 'Task 2'}</div>
        <div class="prompt-prewrap">${escapeHtml(task.prompt)}</div>
      </div>

      <div class="writing-layout writing-layout-resizable">
        <section class="writing-pane writing-pane-left" id="writing-editor-pane" style="width:${editorWidth}%;">
          <div class="writing-pane-head">
            <h3>写作区</h3>
            <div class="writing-save-status">
              <span>${workspace.dirty ? '未保存' : '已保存'}</span>
            </div>
          </div>
          <textarea id="writing-essay-input" class="writing-textarea" placeholder="在这里输入或粘贴你的作文。">${escapeHtml(workspace.essay)}</textarea>
        </section>

        <div class="writing-divider" id="writing-divider" aria-label="resize panes"></div>

        <section class="writing-pane writing-pane-right" id="writing-result-pane">
          <div class="writing-pane-head">
            <div class="tabs writing-tabs">
              <button class="tab${workspace.activeTab === 'sample' ? ' active' : ''}" data-writing-tab="sample">Sample Band 9</button>
              <button class="tab${workspace.activeTab === 'revised' ? ' active' : ''}" data-writing-tab="revised">My Revised Band 9</button>
            </div>
          </div>

          ${workspace.activeTab === 'sample' ? `
            <div class="writing-reading-panel writing-highlight-surface" id="writing-reading-panel" data-highlight-source="sample">${renderHighlightedText(sampleAnswer, workspace.highlights)}</div>
          ` : workspace.correctionResult ? `
            ${renderFeedbackCards(workspace.correctionResult)}
            <div class="writing-reading-panel writing-highlight-surface" id="writing-reading-panel" data-highlight-source="revised">${renderHighlightedText(revisedEssay, workspace.highlights)}</div>
            <div class="button-inline writing-cta-row">
              <button class="secondary-btn" id="writing-save-library">保存到我的私有满分作文库</button>
            </div>
          ` : `
            <div class="writing-empty-state">
              <button class="secondary-btn primary-action-btn" id="writing-correct-essay">AI 修改</button>
            </div>
          `}

          ${renderFloatingSelection(workspace)}
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
            <h3>我的原文</h3>
            <div class="writing-save-status"><span>已保存</span></div>
          </div>
          <div class="writing-reading-panel">${escapeHtml(record.originalEssay).replace(/\n/g, '<br>')}</div>
        </section>
        <section class="writing-pane">
          <div class="writing-pane-head">
            <h3>AI 修改结果</h3>
            <div class="writing-save-status"><span>${new Date(record.savedAt).toLocaleString()}</span></div>
          </div>
          ${renderFeedbackCards(record.correctionResult)}
          <div class="writing-reading-panel">${renderHighlightedText(record.correctionResult?.revisedEssay || '', record.highlights)}</div>
        </section>
      </div>
    </div>
  `;
}

function renderSampleView(record) {
  return `
    <div class="writing-main-view">
      <div class="writing-prompt">
        <div class="section-label">Sample Band 9</div>
        <div class="prompt-prewrap">${escapeHtml(record.prompt)}</div>
      </div>
      <section class="writing-pane">
        ${record.sampleAnswer
          ? `<div class="writing-reading-panel">${renderHighlightedText(record.sampleAnswer, record.highlights)}</div>`
          : '<div class="writing-empty-copy">这道题目前还没有预生成的 Band 9 sample。</div>'
        }
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
          <h3>高分表达</h3>
          <div class="writing-save-status"><span>${index + 1} / ${flashcards.length}</span></div>
        </div>
        <div class="flashcard-shell">
          <div class="flashcard-face">
            <div class="section-label">Chinese -> English</div>
            <div class="flashcard-copy">${escapeHtml(current.chinese)}</div>
            ${workspace.flashcardAnswerVisible ? `<div class="flashcard-answer">${escapeHtml(current.english)}</div>` : '<div class="flashcard-answer muted">先回忆英文，再点显示答案。</div>'}
          </div>
          <div class="button-inline">
            <button class="secondary-btn" id="flashcard-prev"${index === 0 ? ' disabled' : ''}>上一个</button>
            <button class="secondary-btn" id="flashcard-show">显示答案</button>
            <button class="secondary-btn" id="flashcard-next"${index === flashcards.length - 1 ? ' disabled' : ''}>下一个</button>
          </div>
        </div>
      </section>
    </div>
  `;
}

function renderMainView(task, workspace) {
  if (workspace.viewMode === 'practice') return renderPracticeView(task, workspace);
  const record = getLibraryRecords().find(item => item.taskId === workspace.viewTaskId);
  if (!record) {
    return `
      <div class="writing-main-view">
        <section class="writing-pane">
          <div class="writing-empty-copy">请先从左侧选择一条记录。</div>
        </section>
      </div>
    `;
  }
  if (workspace.viewMode === 'record') return renderRecordView(record);
  if (workspace.viewMode === 'sample') return renderSampleView(record);
  return renderFlashcardsView(record, workspace);
}

export function renderWritingPractice(task) {
  const workspace = getWritingWorkspace(task);
  return `
    <div class="writing-page" data-writing-task-id="${task.id}">
      <div class="writing-page-head">
        <div>
          <div class="section-label">${task.type === 'task1' ? 'Task 1' : 'Task 2'}</div>
          <h2>${escapeHtml(task.title || 'Writing task')}</h2>
        </div>
        <div class="writing-save-status">
          <span>${authState.session ? escapeHtml(authState.session.identity) : '未登录'}</span>
          <span>${workspace.highlights.length} highlights</span>
        </div>
      </div>

      <div class="writing-shell${workspace.sidebarCollapsed ? ' writing-shell-wide' : ''}">
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
  const confirmed = window.confirm(hasResult ? '当前内容还没保存到作文库，是否先保存？' : '当前作文还没有正式保存，确认离开吗？');
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

function clearSelectionUI(task) {
  patchWritingWorkspace(task, {
    selectionText: '',
    selectionTranslation: '',
    selectionX: 0,
    selectionY: 0
  });
}

function updateSelectionPopover(task) {
  const workspace = getWritingWorkspace(task);
  const pop = document.getElementById('writing-selection-float');
  if (!pop) return;

  if (!workspace.selectionText) {
    pop.hidden = true;
    return;
  }

  pop.hidden = false;
  pop.style.left = `${workspace.selectionX}px`;
  pop.style.top = `${workspace.selectionY}px`;
  const translation = pop.querySelector('.selection-translation-pop');
  if (translation) {
    translation.textContent = workspace.selectionTranslation || '';
    translation.hidden = !workspace.selectionTranslation;
  }
}

function saveHighlight(task, source) {
  const workspace = getWritingWorkspace(task);
  const text = workspace.selectionText.trim();
  if (!text) return;
  if (workspace.highlights.some(item => item.text === text)) {
    clearSelectionUI(task);
    rerender();
    return;
  }

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
    dirty: true,
    selectionText: '',
    selectionTranslation: ''
  });
  rerender();
}

function bindSelection(task) {
  const panel = document.getElementById('writing-reading-panel');
  if (!panel) return;
  const source = panel.dataset.highlightSource || 'sample';

  if (selectionHandler) {
    document.removeEventListener('selectionchange', selectionHandler);
  }

  selectionHandler = () => {
    const selection = window.getSelection();
    const text = selection?.toString().trim() || '';
    if (!text || !panel.contains(selection?.anchorNode)) {
      clearSelectionUI(task);
      updateSelectionPopover(task);
      return;
    }

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    patchWritingWorkspace(task, {
      selectionText: text,
      selectionTranslation: '',
      selectionX: rect.left + (rect.width / 2),
      selectionY: Math.max(rect.top - 12, 12)
    });
    updateSelectionPopover(task);
  };

  document.addEventListener('selectionchange', selectionHandler);

  const translateBtn = document.getElementById('writing-translate');
  translateBtn?.addEventListener('mousedown', event => event.preventDefault());
  translateBtn?.addEventListener('click', () => {
    const workspace = getWritingWorkspace(task);
    const translation = lookupTranslation(workspace.selectionText);
    window.alert(translation || '未找到翻译。');
    clearSelectionUI(task);
    window.getSelection()?.removeAllRanges();
    updateSelectionPopover(task);
  });

  const saveBtn = document.getElementById('writing-save-highlight');
  saveBtn?.addEventListener('mousedown', event => event.preventDefault());
  saveBtn?.addEventListener('click', () => {
    saveHighlight(task, source);
    window.getSelection()?.removeAllRanges();
  });
}

function unbindSplit() {
  if (!splitHandlers) return;
  window.removeEventListener('mousemove', splitHandlers.move);
  window.removeEventListener('mouseup', splitHandlers.up);
  splitHandlers = null;
}

function bindResizableSplit(task) {
  const layout = document.querySelector('.writing-layout-resizable');
  const divider = document.getElementById('writing-divider');
  if (!layout || !divider) return;

  divider.addEventListener('mousedown', event => {
    event.preventDefault();
    const rect = layout.getBoundingClientRect();

    const onMove = moveEvent => {
      const next = ((moveEvent.clientX - rect.left) / rect.width) * 100;
      patchWritingWorkspace(task, {
        editorWidth: Math.min(Math.max(next, 28), 72)
      });
      const current = getWritingWorkspace(task).editorWidth;
      const editorPane = document.getElementById('writing-editor-pane');
      if (editorPane) editorPane.style.width = `${current}%`;
    };

    const onUp = () => {
      unbindSplit();
      rerender();
    };

    splitHandlers = { move: onMove, up: onUp };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  });
}

async function runCorrection(task) {
  const essay = document.getElementById('writing-essay-input')?.value.trim() || '';
  if (!essay) {
    alert('请先输入作文。');
    return;
  }

  const response = await activeController.hooks.runAiCorrection(task, essay);
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      activeController.hooks.ensureActionAccess({
        type: 'correctEssay',
        requiresCredits: true,
        onAllowed: async () => runCorrection(task)
      });
      return;
    }
    alert(response.error || 'AI 修改失败。');
    return;
  }

  patchWritingWorkspace(task, {
    essay,
    activeTab: 'revised',
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
        const allow = await trySaveBeforeNavigation(task, () => activeController?.hooks.exitPractice?.());
        if (!allow) return;
        activeController?.hooks.exitPractice?.();
        return;
      }

      const allow = await trySaveBeforeNavigation(task, () => {
        patchWritingWorkspace(task, { viewMode: nextView, viewTaskId: nextTaskId });
      });
      if (!allow) return;

      patchWritingWorkspace(task, { viewMode: nextView, viewTaskId: nextTaskId });
      rerender();
    });
  });
}

function bindPractice(task) {
  document.getElementById('writing-essay-input')?.addEventListener('input', event => {
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
      onAllowed: async () => runCorrection(task)
    });
    if (!allowed) return;
    await runCorrection(task);
  });

  document.getElementById('writing-save-library')?.addEventListener('click', async () => {
    const persist = async () => {
      const record = savePracticeRecord(task);
      if (!record) {
        alert('请先完成 AI 修改。');
        return;
      }
      rerender();
    };

    if (!authState.session) {
      activeController.hooks.ensureActionAccess({
        type: 'saveLibrary',
        requiresCredits: false,
        onAllowed: persist
      });
      return;
    }
    await persist();
  });

  bindSelection(task);
  bindResizableSplit(task);
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
    const record = getLibraryRecords().find(item => item.taskId === workspace.viewTaskId);
    const total = record?.flashcards?.length || 0;
    patchWritingWorkspace(task, {
      flashcardIndex: Math.min((workspace.flashcardIndex || 0) + 1, Math.max(total - 1, 0)),
      flashcardAnswerVisible: false
    });
    rerender();
  });
}

function cleanup() {
  if (selectionHandler) {
    document.removeEventListener('selectionchange', selectionHandler);
    selectionHandler = null;
  }
  unbindSplit();
  window.onbeforeunload = null;
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
  cleanup();
  activeController = { task, reopen, hooks };
  bindSidebar(task);
  bindPractice(task);
  bindFlashcards(task);
  bindBeforeUnload(task);
}

export async function attemptCloseWritingModal() {
  if (!activeController) return true;
  const allow = await trySaveBeforeNavigation(activeController.task, () => {
    cleanup();
    state.activeWritingContext = null;
  });
  if (!allow) return false;
  cleanup();
  state.activeWritingContext = null;
  activeController = null;
  return true;
}
