import { authState } from './auth.js';
import { state } from '../shared/state.js';

const WORKSPACE_KEY = 'ielts_writing_workspace_v3';
const LIBRARY_KEY = 'ielts_writing_library_v3';
const EMPTY_FLASHCARD_MESSAGE = '当前你还没有高光选中你想要学习的表达，快去右侧我的专属 9 分范文部分选中吧';

let activeController = null;
let selectionHandler = null;
let splitHandlers = null;
let timerInterval = null;

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

function maskOutlineText(text) {
  return String(text || '').replace(/[A-Za-z][A-Za-z-]*/g, match => '_'.repeat(Math.max(match.length, 3)));
}

function countWords(text) {
  return String(text || '').trim().split(/\s+/).filter(Boolean).length;
}

function getTaskDurationMs(task) {
  return (task.type === 'task1' ? 20 : 40) * 60 * 1000;
}

function formatCountdown(ms) {
  const totalSeconds = Math.max(Math.ceil(ms / 1000), 0);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function defaultWorkspace(task) {
  return {
    taskId: task.id,
    essay: '',
    activeTab: 'revised',
    viewMode: 'practice',
    viewTaskId: task.id,
    correctionResult: null,
    highlights: [],
    flashcards: [],
    sidebarCollapsed: false,
    editorWidth: 48,
    timerStartedAt: Date.now(),
    flashcardIndex: 0,
    flashcardAnswerVisible: false,
    outlineAnswerVisible: false,
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
  merged.activeTab = 'revised';
  if (typeof merged.editorWidth !== 'number') merged.editorWidth = 48;
  if (typeof merged.timerStartedAt !== 'number') merged.timerStartedAt = Date.now();
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

function renderRevisionNote(correctionResult) {
  const note = correctionResult?.revisionNote;
  if (!note) return '';
  return `
    <section class="writing-pane writing-revision-note">
      <div class="writing-pane-head">
        <h3>修改说明</h3>
      </div>
      <div class="writing-reading-panel">${escapeHtml(note).replace(/\n/g, '<br>')}</div>
    </section>
  `;
}

function renderKeywordOutlineExercise(record, workspace) {
  const outline = record.correctionResult?.keywordOutline || '';
  if (!outline) {
    return `
      <div class="writing-main-view">
        <section class="writing-pane">
          <div class="writing-empty-copy">这条记录还没有 keyword outline。</div>
        </section>
      </div>
    `;
  }

  const masked = maskOutlineText(outline).replace(/\n/g, '<br>');
  const answer = escapeHtml(outline).replace(/\n/g, '<br>');
  return `
    <div class="writing-main-view">
      <section class="writing-pane">
        <div class="writing-pane-head">
          <h3>Keyword Outline 填空练习</h3>
          <div class="writing-save-status"><span>${workspace.outlineAnswerVisible ? '已显示答案' : '先回忆再看答案'}</span></div>
        </div>
        <div class="flashcard-shell">
          <div class="flashcard-face">
            <div class="section-label">Fill in the outline</div>
            <div class="flashcard-copy">${workspace.outlineAnswerVisible ? answer : masked}</div>
          </div>
          <div class="button-inline">
            <button class="secondary-btn" id="outline-toggle-answer">${workspace.outlineAnswerVisible ? '隐藏答案' : '显示答案'}</button>
          </div>
        </div>
      </section>
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
                <button class="library-child-btn${currentViewKey === `flashcards:${record.taskId}` ? ' active' : ''}" data-library-view="flashcards" data-library-task="${record.taskId}">高分表达</button>
                <button class="library-child-btn${currentViewKey === `outline:${record.taskId}` ? ' active' : ''}" data-library-view="outline" data-library-task="${record.taskId}">Keyword Outline</button>
              </div>
            </div>
          `).join('') : '<div class="muted">还没有保存的记录。</div>'}
        </div>
      `}
    </aside>
  `;
}

function renderPracticeView(task, workspace) {
  const revisedEssay = workspace.correctionResult?.revisedEssay || '';
  const editorWidth = Math.min(Math.max(workspace.editorWidth, 28), 72);
  const wordCount = countWords(workspace.essay);

  return `
    <div class="writing-main-view">
      <div class="writing-layout writing-layout-resizable">
        <section class="writing-pane writing-pane-left" id="writing-editor-pane" style="width:${editorWidth}%;">
          <div class="writing-prompt">
            <div class="section-label">${task.type === 'task1' ? 'Task 1' : 'Task 2'}</div>
            <div class="prompt-prewrap">${escapeHtml(task.prompt)}</div>
          </div>
          <div class="writing-pane-head">
            <h3>写作区</h3>
            <div class="writing-save-status">
              <span>${workspace.dirty ? '未保存' : '已保存'}</span>
              <span id="writing-word-count">字数 ${wordCount}</span>
              <span id="writing-timer" data-deadline="${workspace.timerStartedAt + getTaskDurationMs(task)}">倒计时 ${formatCountdown((workspace.timerStartedAt + getTaskDurationMs(task)) - Date.now())}</span>
            </div>
          </div>
          <textarea id="writing-essay-input" class="writing-textarea" placeholder="在这里输入或粘贴你的作文。">${escapeHtml(workspace.essay)}</textarea>
        </section>

        <div class="writing-divider" id="writing-divider" aria-label="resize panes"></div>

        <section class="writing-pane writing-pane-right" id="writing-result-pane">
          <div class="writing-pane-head">
            <h3>我的专属 9 分范文</h3>
          </div>

          ${workspace.correctionResult ? `
            ${renderFeedbackCards(workspace.correctionResult)}
            <div class="writing-reading-panel writing-highlight-surface" id="writing-reading-panel" data-highlight-source="revised">${renderHighlightedText(revisedEssay, workspace.highlights)}</div>
            ${renderRevisionNote(workspace.correctionResult)}
            <div class="button-inline writing-cta-row">
              <button class="secondary-btn" id="writing-save-library">保存到我的私有满分作文库</button>
            </div>
          ` : `
            <div class="writing-empty-state">
              <button class="secondary-btn primary-action-btn" id="writing-correct-essay">把我的文章改到 9 分</button>
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
          ${record.correctionResult?.revisionNote ? `<div class="writing-reading-panel">${escapeHtml(record.correctionResult.revisionNote).replace(/\n/g, '<br>')}</div>` : ''}
        </section>
      </div>
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
  if (workspace.viewMode === 'outline') return renderKeywordOutlineExercise(record, workspace);
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
  const source = panel.dataset.highlightSource || 'revised';

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

function unbindTimer() {
  if (!timerInterval) return;
  window.clearInterval(timerInterval);
  timerInterval = null;
}

function bindTimer(task) {
  const timerEl = document.getElementById('writing-timer');
  if (!timerEl) return;
  const deadline = Number(timerEl.dataset.deadline || 0);
  const paint = () => {
    const remaining = deadline - Date.now();
    timerEl.textContent = `倒计时 ${formatCountdown(remaining)}`;
    timerEl.classList.toggle('is-overtime', remaining <= 0);
  };
  paint();
  unbindTimer();
  timerInterval = window.setInterval(paint, 1000);
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
      revisionNote: response.revisionNote,
      keywordOutline: response.keywordOutline,
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
    const wordCountEl = document.getElementById('writing-word-count');
    if (wordCountEl) {
      wordCountEl.textContent = `字数 ${countWords(event.target.value)}`;
    }
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
  bindTimer(task);
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

function bindOutline(task) {
  document.getElementById('outline-toggle-answer')?.addEventListener('click', () => {
    const workspace = getWritingWorkspace(task);
    patchWritingWorkspace(task, {
      outlineAnswerVisible: !workspace.outlineAnswerVisible
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
  unbindTimer();
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
  bindOutline(task);
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
