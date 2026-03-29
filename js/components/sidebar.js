import { state } from '../state.js';
import { renderGrid } from './grid.js';
import { getFilterTaxonomy } from '../utils.js';
import { SKILL_TO_SUBTYPES } from '../skillTaxonomy.js';

let sidebarCollapsed = false;

// ── hierarchy from tags.txt ──────────────────────────────────────
const L1_TO_L2 = {
  'people': ['professions', 'close_bonds', 'general'],
  'place': ['outdoor', 'indoor'],
  'object': ['tangible', 'intangible'],
  'experience_activity': ['work', 'study', 'leisure', 'routines'],
  'abstract_concepts': ['communication', 'emotion', 'personal_traits', 'values', 'personal_growth', 'influence', 'time']
};

// ── helpers ──────────────────────────────────────────────────────
function getContentTags(topic) {
  return getFilterTaxonomy(topic);
}

function getQuestions(topic) {
  return topic.questions || topic.part3 || [];
}

function matchesTimeFrame(q, timeFrame) {
  if (!timeFrame) return true;
  return q.time_frame === timeFrame;
}

function matchesSkillFilters(q, skillFilters, subtypeFilters) {
  const hasSkill = skillFilters.length > 0;
  const hasSub = subtypeFilters.length > 0;
  if (!hasSkill && !hasSub) return true;

  if (hasSub) {
    return subtypeFilters.includes(q.skill_subtype);
  }
  const primary = (q.skill_tags && q.skill_tags[0]) || '';
  if (!primary) return false;
  return skillFilters.includes(primary);
}

function matchingQuestionCount(topic, skillFilters, subtypeFilters, timeFrame) {
  const qs = getQuestions(topic);
  return qs.filter(q => {
    if (!matchesTimeFrame(q, timeFrame)) return false;
    return matchesSkillFilters(q, skillFilters, subtypeFilters);
  }).length;
}

function countByTimeFrame(topics, skillFilters, subtypeFilters) {
  const counts = { past: 0, present: 0, future: 0 };
  topics.forEach(t => {
    const qs = getQuestions(t);
    qs.forEach(q => {
      if (!matchesSkillFilters(q, skillFilters, subtypeFilters)) return;
      const tf = q.time_frame;
      if (tf && counts.hasOwnProperty(tf)) counts[tf]++;
    });
  });
  return counts;
}

function countByL1(topics, skillFilters, subtypeFilters, timeFrame) {
  const counts = {};
  topics.forEach(t => {
    const l1 = getContentTags(t).l1;
    if (!l1) return;
    const qc = matchingQuestionCount(t, skillFilters, subtypeFilters, timeFrame);
    if (qc > 0) counts[l1] = (counts[l1] || 0) + qc;
  });
  return counts;
}

function countByL2(topics, l1Filter, skillFilters, subtypeFilters, timeFrame) {
  const counts = {};
  const validL2 = l1Filter ? new Set(L1_TO_L2[l1Filter] || []) : null;
  const focused = state.filterMode === 'focused';
  topics.forEach(t => {
    const ct = getContentTags(t);
    if (l1Filter && ct.l1 !== l1Filter) return;
    const qc = matchingQuestionCount(t, skillFilters, subtypeFilters, timeFrame);
    if (qc === 0) return;
    const l2 = ct.l2 || [];
    l2.forEach(tag => {
      if (validL2 && !validL2.has(tag)) return;
      if (focused) {
        const simSelected = new Set(state.selectedL2Tags);
        simSelected.add(tag);
        if (!l2.every(t2 => simSelected.has(t2))) return;
      }
      counts[tag] = (counts[tag] || 0) + qc;
    });
  });
  return counts;
}

function countByL3(topics, l1Filter, l2Filters, skillFilters, subtypeFilters, timeFrame) {
  const counts = {};
  const focused = state.filterMode === 'focused';
  topics.forEach(t => {
    const ct = getContentTags(t);
    if (l1Filter && ct.l1 !== l1Filter) return;
    if (l2Filters.length > 0) {
      const l2 = ct.l2 || [];
      if (focused) {
        if (l2.length === 0 || !l2.every(tag => l2Filters.includes(tag))) return;
      } else {
        if (!l2.some(tag => l2Filters.includes(tag))) return;
      }
    }
    const qc = matchingQuestionCount(t, skillFilters, subtypeFilters, timeFrame);
    if (qc === 0) return;
    const l3 = ct.l3 || [];
    l3.forEach(tag => {
      if (focused) {
        const simSelected = new Set(state.selectedL3Tags);
        simSelected.add(tag);
        if (!l3.every(t3 => simSelected.has(t3))) return;
      }
      counts[tag] = (counts[tag] || 0) + qc;
    });
  });
  return counts;
}

function extractSkillTags() {
  const p1Counts = {};
  state.part1Data.forEach(topic => {
    (topic.questions || []).forEach(q => {
      const primary = (q.skill_tags && q.skill_tags[0]) || '';
      if (primary) p1Counts[primary] = (p1Counts[primary] || 0) + 1;
    });
  });
  const p2Counts = {};
  state.part2Data.forEach(topic => {
    (topic.part3 || []).forEach(q => {
      const primary = (q.skill_tags && q.skill_tags[0]) || '';
      if (primary) p2Counts[primary] = (p2Counts[primary] || 0) + 1;
    });
  });
  return { p1: p1Counts, p2: p2Counts };
}

function extractSkillSubtypes(selectedSkillTags) {
  if (selectedSkillTags.length === 0) return {};
  const validSubs = new Set();
  selectedSkillTags.forEach(st => {
    (SKILL_TO_SUBTYPES[st] || []).forEach(s => validSubs.add(s));
  });
  const data = state.currentTab === 'part1' ? state.part1Data : state.part2Data;
  const qKey = state.currentTab === 'part1' ? 'questions' : 'part3';
  const counts = {};
  data.forEach(topic => {
    (topic[qKey] || []).forEach(q => {
      const sub = q.skill_subtype;
      if (sub && validSubs.has(sub)) {
        const primary = (q.skill_tags && q.skill_tags[0]) || '';
        if (primary && selectedSkillTags.includes(primary)) {
          counts[sub] = (counts[sub] || 0) + 1;
        }
      }
    });
  });
  return counts;
}

// ── filter logic ─────────────────────────────────────────────────
function applyFilters(data, tab) {
  let filtered = [...data];
  const focused = state.filterMode === 'focused';

  if (state.selectedSkillTags.length > 0 || state.selectedSkillSubtypes.length > 0 || state.selectedTimeFrame) {
    filtered = filtered.filter(item => {
      const questions = tab === 'part1' ? (item.questions || []) : (item.part3 || []);
      return questions.some(q => {
        if (state.selectedTimeFrame && q.time_frame !== state.selectedTimeFrame) return false;
        return matchesSkillFilters(q, state.selectedSkillTags, state.selectedSkillSubtypes);
      });
    });
  }

  if (state.selectedL1Tag) {
    filtered = filtered.filter(item => getContentTags(item).l1 === state.selectedL1Tag);
  }

  if (state.selectedL2Tags.length > 0) {
    filtered = filtered.filter(item => {
      const l2 = getContentTags(item).l2 || [];
      if (focused) {
        return l2.length > 0 && l2.every(tag => state.selectedL2Tags.includes(tag));
      }
      return l2.some(tag => state.selectedL2Tags.includes(tag));
    });
  }

  if (state.selectedL3Tags.length > 0) {
    filtered = filtered.filter(item => {
      const l3 = getContentTags(item).l3 || [];
      if (focused) {
        return l3.length > 0 && l3.every(tag => state.selectedL3Tags.includes(tag));
      }
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

// ── visible L2/L3: data-driven (scan actual tags from filtered topics) ──
function getVisibleL2Tags(topics, l1Filter, skillFilters, subtypeFilters, timeFrame) {
  if (!l1Filter) return [];
  const validL2 = new Set(L1_TO_L2[l1Filter] || []);
  const tags = new Set();
  topics.forEach(t => {
    const ct = getContentTags(t);
    if (ct.l1 !== l1Filter) return;
    if (matchingQuestionCount(t, skillFilters, subtypeFilters, timeFrame) === 0) return;
    (ct.l2 || []).forEach(tag => { if (validL2.has(tag)) tags.add(tag); });
  });
  return [...tags].sort();
}

function getVisibleL3Tags(topics, l1Filter, l2Filters, skillFilters, subtypeFilters, timeFrame) {
  if (!l1Filter || l2Filters.length === 0) return [];
  const focused = state.filterMode === 'focused';
  const tags = new Set();
  topics.forEach(t => {
    const ct = getContentTags(t);
    if (ct.l1 !== l1Filter) return;
    const l2 = ct.l2 || [];
    if (focused) {
      if (l2.length === 0 || !l2.every(tag => l2Filters.includes(tag))) return;
    } else {
      if (!l2.some(tag => l2Filters.includes(tag))) return;
    }
    if (matchingQuestionCount(t, skillFilters, subtypeFilters, timeFrame) === 0) return;
    (ct.l3 || []).forEach(tag => tags.add(tag));
  });
  return [...tags].sort();
}

// ── render ───────────────────────────────────────────────────────
function renderSidebar() {
  const currentTopics = state.currentTab === 'part1' ? state.part1Data : state.part2Data;
  const skills = extractSkillTags();
  const currentSkills = state.currentTab === 'part1' ? skills.p1 : skills.p2;
  const hasFilters = state.selectedSkillTags.length > 0
    || state.selectedSkillSubtypes.length > 0
    || state.selectedTimeFrame
    || state.selectedL1Tag
    || state.selectedL2Tags.length > 0
    || state.selectedL3Tags.length > 0;

  const skillOrder = ['experience', 'description', 'preference', 'evaluation', 'analysis', 'comparison', 'hypothetical'];
  const skillEntries = skillOrder
    .filter(name => currentSkills[name] > 0)
    .map(name => [name, currentSkills[name]]);

  const activeSkills = state.selectedSkillTags;
  const activeSubs = state.selectedSkillSubtypes;

  const subtypeCounts = extractSkillSubtypes(activeSkills);
  const visibleSubtypes = activeSkills.length > 0
    ? activeSkills.flatMap(st => SKILL_TO_SUBTYPES[st] || []).filter(s => subtypeCounts[s] > 0)
    : [];

  const tfCounts = countByTimeFrame(currentTopics, activeSkills, activeSubs);
  const tfOrder = ['past', 'present', 'future'];
  const activeTF = state.selectedTimeFrame;

  const l1Counts = countByL1(currentTopics, activeSkills, activeSubs, activeTF);
  const l1Order = ["people", "place", "object", "experience_activity", "abstract_concepts"];

  const visibleL2 = getVisibleL2Tags(currentTopics, state.selectedL1Tag, activeSkills, activeSubs, activeTF);
  const l2Counts = state.selectedL1Tag
    ? countByL2(currentTopics, state.selectedL1Tag, activeSkills, activeSubs, activeTF) : {};

  const visibleL3 = getVisibleL3Tags(currentTopics, state.selectedL1Tag, state.selectedL2Tags, activeSkills, activeSubs, activeTF);
  const l3Counts = (state.selectedL2Tags.length > 0)
    ? countByL3(currentTopics, state.selectedL1Tag, state.selectedL2Tags, activeSkills, activeSubs, activeTF)
    : {};

  const html = `
    <div class="sidebar">
      <div class="sidebar-content">
        ${hasFilters ? `<button class="sidebar-clear-btn" onclick="window._sidebarClear()">Clear filters</button>` : ''}

        <div class="sidebar-section">
          <div class="sidebar-section-label">Mode</div>
          <div class="sidebar-tags">
            <span class="sidebar-mode-btn${state.filterMode === 'focused' ? ' sidebar-mode-active' : ''}"
                  onclick="window._sidebarMode('focused')">focused mode</span>
            <span class="sidebar-mode-btn${state.filterMode === 'blended' ? ' sidebar-mode-active' : ''}"
                  onclick="window._sidebarMode('blended')">blended mode</span>
          </div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-section-label">Skill</div>
          <div class="sidebar-tags">
            ${skillEntries.map(([name, count]) => `
              <span class="stag stag-skill${activeSkills.includes(name) ? ' sidebar-active' : ''}"
                    onclick="window._sidebarSkill('${name}')">
                ${name} <span class="sidebar-count">${count}</span>
              </span>
            `).join('')}
          </div>
        </div>

        ${visibleSubtypes.length > 0 ? `
          <div class="sidebar-section">
            <div class="sidebar-section-label">Subtype</div>
            <div class="sidebar-tags">
              ${visibleSubtypes.map(name => {
                const c = subtypeCounts[name] || 0;
                return `
                  <span class="stag stag-subtype${activeSubs.includes(name) ? ' sidebar-active' : ''}"
                        onclick="window._sidebarSubtype('${name}')">
                    ${name.replace(/_/g, ' ')} <span class="sidebar-count">${c}</span>
                  </span>
                `;
              }).join('')}
            </div>
          </div>
        ` : ''}

        <div class="sidebar-section">
          <div class="sidebar-section-label">Time Frame</div>
          <div class="sidebar-tags">
            ${tfOrder.map(name => `
              <span class="stag stag-tf${state.selectedTimeFrame === name ? ' sidebar-active' : ''}"
                    onclick="window._sidebarTF('${name}')">
                ${name} <span class="sidebar-count">${tfCounts[name] || 0}</span>
              </span>
            `).join('')}
          </div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-section-label">Category</div>
          <div class="sidebar-tags">
            ${l1Order.map(name => `
              <span class="stag stag-l1${state.selectedL1Tag === name ? ' sidebar-active' : ''}"
                    onclick="window._sidebarL1('${name}')">
                ${name === 'experience_activity' ? 'experience/activity' : name} <span class="sidebar-count">${l1Counts[name] || 0}</span>
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
                  <span class="stag stag-l2${state.selectedL2Tags.includes(name) ? ' sidebar-active' : ''}"
                        onclick="window._sidebarL2('${name}')">
                    ${name.replace(/_/g, ' ')} <span class="sidebar-count">${c}</span>
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
                  <span class="stag stag-l3${state.selectedL3Tags.includes(name) ? ' sidebar-active' : ''}"
                        onclick="window._sidebarL3('${name}')">
                    ${name.replace(/_/g, ' ')} <span class="sidebar-count">${c}</span>
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
  if (i > -1) {
    state.selectedSkillTags.splice(i, 1);
    state.selectedSkillSubtypes = [];
  } else {
    state.selectedSkillTags.push(name);
    state.selectedSkillSubtypes = [];
  }
  renderSidebar();
  applyFiltersAndRender();
}

function toggleSkillSubtype(name) {
  const i = state.selectedSkillSubtypes.indexOf(name);
  if (i > -1) state.selectedSkillSubtypes.splice(i, 1);
  else state.selectedSkillSubtypes.push(name);
  renderSidebar();
  applyFiltersAndRender();
}

function toggleTimeFrame(name) {
  state.selectedTimeFrame = state.selectedTimeFrame === name ? null : name;
  renderSidebar();
  applyFiltersAndRender();
}

function toggleL1(name) {
  if (state.selectedL1Tag === name) {
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
    state.selectedL3Tags = [];
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
  state.selectedSkillSubtypes = [];
  state.selectedTimeFrame = null;
  state.selectedL1Tag = null;
  state.selectedL2Tags = [];
  state.selectedL3Tags = [];
  renderSidebar();
  renderGrid(state.currentTab);
}

function setFilterMode(mode) {
  state.filterMode = mode;
  renderSidebar();
  applyFiltersAndRender();
}

// ── global handlers ──────────────────────────────────────────────
window._sidebarMode = function(m) { setFilterMode(m); };
window._sidebarSkill = function(n) { toggleSkillTag(n); };
window._sidebarSubtype = function(n) { toggleSkillSubtype(n); };
window._sidebarTF = function(n) { toggleTimeFrame(n); };
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
  state.selectedSkillSubtypes = [];
  state.selectedTimeFrame = null;
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
}

export { renderSidebar };
