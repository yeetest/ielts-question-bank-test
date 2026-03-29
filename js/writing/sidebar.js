import { state } from '../shared/state.js';
import { renderGrid } from '../components/grid.js';

function currentWritingData() {
  return state.currentTab === 'task1' ? state.writingTask1Data : state.writingTask2Data;
}

function currentFilters() {
  return {
    task: state.selectedWritingTaskTags,
    register: state.selectedWritingRegisterTags,
    topic: state.selectedWritingTopicTags
  };
}

function matchesWritingFilters(item) {
  const tags = item.writingTags || { task: [], register: [], topic: [] };
  const filters = currentFilters();
  if (filters.task.length && !tags.task.some(tag => filters.task.includes(tag))) return false;
  if (filters.register.length && !tags.register.some(tag => filters.register.includes(tag))) return false;
  if (filters.topic.length && !tags.topic.some(tag => filters.topic.includes(tag))) return false;
  return true;
}

export function getFilteredWritingData() {
  return currentWritingData().filter(matchesWritingFilters);
}

function countByKey(data, key) {
  const counts = {};
  data.forEach(item => {
    (item.writingTags?.[key] || []).forEach(tag => {
      counts[tag] = (counts[tag] || 0) + 1;
    });
  });
  return counts;
}

function renderTagGroup(label, className, counts, selected, clickHandler) {
  const entries = Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]));
  if (!entries.length) return '';
  return `
    <div class="sidebar-section">
      <div class="sidebar-section-label">${label}</div>
      <div class="sidebar-tags">
        ${entries.map(([tag, count]) => `
          <span class="stag ${className}${selected.includes(tag) ? ' sidebar-active' : ''}" onclick="${clickHandler}('${tag}')">
            ${tag.replace(/_/g, ' ')} <span class="sidebar-count">${count}</span>
          </span>
        `).join('')}
      </div>
    </div>
  `;
}

export function renderWritingSidebar() {
  const root = document.getElementById('sidebar-root');
  if (!root) return;

  const data = currentWritingData();
  const filtered = getFilteredWritingData();
  const hasFilters = state.selectedWritingTaskTags.length || state.selectedWritingRegisterTags.length || state.selectedWritingTopicTags.length;
  const taskCounts = countByKey(data, 'task');
  const registerCounts = countByKey(data, 'register');
  const topicCounts = countByKey(data, 'topic');

  root.innerHTML = `
    <div class="sidebar">
      <div class="sidebar-content">
        ${hasFilters ? `<button class="sidebar-clear-btn" onclick="window._writingSidebarClear()">Clear filters</button>` : ''}
        ${renderTagGroup(state.currentTab === 'task1' ? 'Task' : 'Mode', 'stag stag-skill', taskCounts, state.selectedWritingTaskTags, 'window._writingSidebarTask')}
        ${state.currentTab === 'task1'
          ? renderTagGroup('Register', 'stag stag-l2', registerCounts, state.selectedWritingRegisterTags, 'window._writingSidebarRegister')
          : ''
        }
        ${renderTagGroup('Topic', 'stag stag-l3', topicCounts, state.selectedWritingTopicTags, 'window._writingSidebarTopic')}
      </div>
    </div>
  `;

  const total = document.getElementById('total-count');
  if (total) {
    total.textContent = `${filtered.length} prompts · ${state.currentTab === 'task1' ? 'Task 1' : 'Task 2'}`;
  }
}

function toggleInList(list, value) {
  return list.includes(value) ? list.filter(item => item !== value) : [...list, value];
}

function rerenderWriting() {
  renderWritingSidebar();
  renderGrid(state.currentTab, getFilteredWritingData());
}

window._writingSidebarTask = value => {
  state.selectedWritingTaskTags = toggleInList(state.selectedWritingTaskTags, value);
  rerenderWriting();
};

window._writingSidebarRegister = value => {
  state.selectedWritingRegisterTags = toggleInList(state.selectedWritingRegisterTags, value);
  rerenderWriting();
};

window._writingSidebarTopic = value => {
  state.selectedWritingTopicTags = toggleInList(state.selectedWritingTopicTags, value);
  rerenderWriting();
};

window._writingSidebarClear = () => {
  state.selectedWritingTaskTags = [];
  state.selectedWritingRegisterTags = [];
  state.selectedWritingTopicTags = [];
  rerenderWriting();
};
