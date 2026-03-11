import { state } from '../state.js';
import { renderGrid } from './grid.js';

let sidebarCollapsed = false;

// ── L1 → L2 → L3 hierarchy (mirrors TAG_HIERARCHY from Python) ──
const TAG_TREE = {
  people: {
    family: ["conflict_resolution"],
    friendship: ["helping_others", "collaboration"],
    celebrity: [],
    influence: [],
    admiration: [],
    talent: [],
    intelligence: ["problem-solving"],
    happiness: [],
    child: [],
  },
  place: {
    home: ["everyday_life"],
    travel: ["adventure", "international", "navigation"],
    nature: ["animals", "conservation"],
    architecture: [],
  },
  object: {
    books: [],
    heirloom: [],
    toy: [],
    phone: [],
    money: [],
    technology: ["app", "social_media"],
  },
  "experience/activity": {
    art: [],
    music: [],
    reading: [],
    movies: [],
    food: [],
    work: [],
    sports: [],
    shopping: [],
    service: [],
    learning: ["self-learning", "curiosity"],
    science: [],
    creativity: [],
    culture: ["stories", "language"],
    communication: ["advice"],
    media: [],
    celebration: ["social_event", "first_time"],
    disruption: ["restriction"],
    mistake: [],
    achievement: ["planning", "self-improvement", "decision"],
    passion: ["likes_dislikes"],
    aspiration: [],
    anticipation: [],
    childhood: ["nostalgia"],
    habit: [],
  },
};

// ── helpers ──────────────────────────────────────────────────────
function getAllTopics() {
  return [...state.part1Data, ...state.part2Data];
}

function getContentTags(topic) {
  const ct = topic.content_tags;
  if (!ct) return { l1: '', l2: [], l3: [] };
  if (Array.isArray(ct)) return { l1: ct[0] || '', l2: ct.slice(1), l3: [] };
  return ct;
}

function countByL1(topics) {
  const counts = {};
  topics.forEach(t => {
    const l1 = getContentTags(t).l1;
    if (l1) counts[l1] = (counts[l1] || 0) + 1;
  });
  return counts;
}

function countByL2(topics, l1Filter) {
  const counts = {};
  topics.forEach(t => {
    const ct = getContentTags(t);
    if (l1Filter && ct.l1 !== l1Filter) return;
    (ct.l2 || []).forEach(tag => {
      counts[tag] = (counts[tag] || 0) + 1;
    });
  });
  return counts;
}

function countByL3(topics, l1Filter, l2Filters) {
  const counts = {};
  topics.forEach(t => {
    const ct = getContentTags(t);
    if (l1Filter && ct.l1 !== l1Filter) return;
    if (l2Filters.length > 0 && !(ct.l2 || []).some(tag => l2Filters.includes(tag))) return;
    (ct.l3 || []).forEach(tag => {
      counts[tag] = (counts[tag] || 0) + 1;
    });
  });
  return counts;
}

function extractSkillTags() {
  const p1Counts = {};
  state.part1Data.forEach(topic => {
    (topic.questions || []).forEach(q => {
      (q.type_tags || []).forEach(tag => { p1Counts[tag] = (p1Counts[tag] || 0) + 1; });
    });
  });
  const p2Counts = {};
  state.part2Data.forEach(topic => {
    (topic.part3 || []).forEach(q => {
      (q.type_tags || []).forEach(tag => { p2Counts[tag] = (p2Counts[tag] || 0) + 1; });
    });
  });
  return { p1: p1Counts, p2: p2Counts };
}

// ── filter logic ─────────────────────────────────────────────────
function applyFilters(data, tab) {
  let filtered = [...data];

  if (state.selectedSkillTags.length > 0) {
    filtered = filtered.filter(item => {
      const questions = tab === 'part1' ? (item.questions || []) : (item.part3 || []);
      return questions.some(q =>
        q.type_tags && q.type_tags.some(tag => state.selectedSkillTags.includes(tag))
      );
    });
  }

  if (state.selectedL1Tag) {
    filtered = filtered.filter(item => getContentTags(item).l1 === state.selectedL1Tag);
  }

  if (state.selectedL2Tags.length > 0) {
    filtered = filtered.filter(item => {
      const l2 = getContentTags(item).l2 || [];
      return l2.some(tag => state.selectedL2Tags.includes(tag));
    });
  }

  if (state.selectedL3Tags.length > 0) {
    filtered = filtered.filter(item => {
      const l3 = getContentTags(item).l3 || [];
      return l3.some(tag => state.selectedL3Tags.includes(tag));
    });
  }

  return filtered;
}

function applyFiltersAndRender() {
  const data = state.currentTab === 'part1' ? state.part1Data : state.part2Data;
  const filteredData = applyFilters(data, state.currentTab);
  renderGrid(state.currentTab, filteredData);
}

// ── which L2/L3 tags to show based on hierarchy + selection ──────
function getVisibleL2Tags() {
  if (!state.selectedL1Tag) return [];
  const subtree = TAG_TREE[state.selectedL1Tag];
  return subtree ? Object.keys(subtree) : [];
}

function getVisibleL3Tags() {
  if (!state.selectedL1Tag || state.selectedL2Tags.length === 0) return [];
  const subtree = TAG_TREE[state.selectedL1Tag] || {};
  const l3tags = [];
  state.selectedL2Tags.forEach(l2 => {
    (subtree[l2] || []).forEach(l3 => {
      if (!l3tags.includes(l3)) l3tags.push(l3);
    });
  });
  return l3tags;
}

// ── render ───────────────────────────────────────────────────────
function renderSidebar() {
  const currentTopics = state.currentTab === 'part1' ? state.part1Data : state.part2Data;
  const skills = extractSkillTags();
  const currentSkills = state.currentTab === 'part1' ? skills.p1 : skills.p2;
  const hasFilters = state.selectedSkillTags.length > 0
    || state.selectedL1Tag
    || state.selectedL2Tags.length > 0
    || state.selectedL3Tags.length > 0;

  // Skill tags
  const skillEntries = Object.entries(currentSkills).sort((a, b) => b[1] - a[1]);

  // L1 counts (scoped to current tab)
  const l1Counts = countByL1(currentTopics);
  const l1Order = ["people", "place", "object", "experience/activity"];

  // L2 (visible only when L1 selected)
  const visibleL2 = getVisibleL2Tags();
  const l2Counts = state.selectedL1Tag ? countByL2(currentTopics, state.selectedL1Tag) : {};

  // L3 (visible only when L2 selected)
  const visibleL3 = getVisibleL3Tags();
  const l3Counts = (state.selectedL2Tags.length > 0)
    ? countByL3(currentTopics, state.selectedL1Tag, state.selectedL2Tags)
    : {};

  const html = `
    <div class="sidebar">
      <div class="sidebar-content">
        ${hasFilters ? `<button class="sidebar-clear-btn" onclick="window._sidebarClear()">✕ Clear filters</button>` : ''}

        <div class="sidebar-section">
          <div class="sidebar-section-label">Skill</div>
          <div class="sidebar-tags">
            ${skillEntries.map(([name, count]) => `
              <span class="ttag ttag-${name}${state.selectedSkillTags.includes(name) ? ' sidebar-active' : ''}"
                    onclick="window._sidebarSkill('${name}')">
                ${name} <span class="sidebar-count">${count}</span>
              </span>
            `).join('')}
          </div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-section-label">Category</div>
          <div class="sidebar-tags">
            ${l1Order.map(name => `
              <span class="ctag ctag-${name.replace('/', '-')}${state.selectedL1Tag === name ? ' sidebar-active' : ''}"
                    onclick="window._sidebarL1('${name}')">
                ${name} <span class="sidebar-count">${l1Counts[name] || 0}</span>
              </span>
            `).join('')}
          </div>
        </div>

        ${visibleL2.length > 0 ? `
          <div class="sidebar-section">
            <div class="sidebar-section-label">Theme</div>
            <div class="sidebar-tags">
              ${visibleL2.map(name => {
                const c = l2Counts[name] || 0;
                if (c === 0) return '';
                return `
                  <span class="ctag ctag-tag${state.selectedL2Tags.includes(name) ? ' sidebar-active' : ''}"
                        onclick="window._sidebarL2('${name}')">
                    ${name} <span class="sidebar-count">${c}</span>
                  </span>
                `;
              }).join('')}
            </div>
          </div>
        ` : ''}

        ${visibleL3.length > 0 ? `
          <div class="sidebar-section">
            <div class="sidebar-section-label">Specific</div>
            <div class="sidebar-tags">
              ${visibleL3.map(name => {
                const c = l3Counts[name] || 0;
                if (c === 0) return '';
                return `
                  <span class="ctag ctag-tag${state.selectedL3Tags.includes(name) ? ' sidebar-active' : ''}"
                        onclick="window._sidebarL3('${name}')">
                    ${name} <span class="sidebar-count">${c}</span>
                  </span>
                `;
              }).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    </div>
  `;

  const sidebarRoot = document.getElementById('sidebar-root');
  if (sidebarRoot) sidebarRoot.innerHTML = html;
}

// ── toggle handlers ──────────────────────────────────────────────
function toggleSkillTag(name) {
  const i = state.selectedSkillTags.indexOf(name);
  if (i > -1) state.selectedSkillTags.splice(i, 1);
  else state.selectedSkillTags.push(name);
  renderSidebar();
  applyFiltersAndRender();
}

function toggleL1(name) {
  if (state.selectedL1Tag === name) {
    // Deselect L1 → clear L2/L3
    state.selectedL1Tag = null;
    state.selectedL2Tags = [];
    state.selectedL3Tags = [];
  } else {
    state.selectedL1Tag = name;
    state.selectedL2Tags = [];
    state.selectedL3Tags = [];
  }
  renderSidebar();
  applyFiltersAndRender();
}

function toggleL2(name) {
  const i = state.selectedL2Tags.indexOf(name);
  if (i > -1) {
    state.selectedL2Tags.splice(i, 1);
    // Remove L3 tags that no longer have a visible parent
    const stillVisible = getVisibleL3Tags();
    state.selectedL3Tags = state.selectedL3Tags.filter(t => stillVisible.includes(t));
  } else {
    state.selectedL2Tags.push(name);
  }
  renderSidebar();
  applyFiltersAndRender();
}

function toggleL3(name) {
  const i = state.selectedL3Tags.indexOf(name);
  if (i > -1) state.selectedL3Tags.splice(i, 1);
  else state.selectedL3Tags.push(name);
  renderSidebar();
  applyFiltersAndRender();
}

function clearAllFilters() {
  state.selectedSkillTags = [];
  state.selectedL1Tag = null;
  state.selectedL2Tags = [];
  state.selectedL3Tags = [];
  renderSidebar();
  renderGrid(state.currentTab);
}

// ── global handlers ──────────────────────────────────────────────
window._sidebarSkill = function(n) { toggleSkillTag(n); };
window._sidebarL1 = function(n) { toggleL1(n); };
window._sidebarL2 = function(n) { toggleL2(n); };
window._sidebarL3 = function(n) { toggleL3(n); };
window._sidebarClear = function() { clearAllFilters(); };

// ── sidebar collapse ─────────────────────────────────────────────
function toggleSidebar() {
  sidebarCollapsed = !sidebarCollapsed;
  const sidebarRoot = document.getElementById('sidebar-root');
  const toggleBtn = document.getElementById('sidebar-toggle');
  if (sidebarRoot) sidebarRoot.style.width = sidebarCollapsed ? '0' : '360px';
  if (toggleBtn) toggleBtn.textContent = sidebarCollapsed ? '▶ Filters' : '◀ Filters';
}

// ── tab change ───────────────────────────────────────────────────
function onTabChange(newTab) {
  state.selectedSkillTags = [];
  state.selectedL1Tag = null;
  state.selectedL2Tags = [];
  state.selectedL3Tags = [];
  state.currentTab = newTab;
  renderSidebar();
  applyFiltersAndRender();
}

// ── init ─────────────────────────────────────────────────────────
export function initSidebar() {
  const toggleBtn = document.getElementById('sidebar-toggle');
  if (toggleBtn) toggleBtn.addEventListener('click', toggleSidebar);

  const tab1Btn = document.getElementById('tab-part1');
  const tab2Btn = document.getElementById('tab-part2');
  if (tab1Btn) tab1Btn.addEventListener('click', () => onTabChange('part1'));
  if (tab2Btn) tab2Btn.addEventListener('click', () => onTabChange('part2'));
}

export { renderSidebar };
