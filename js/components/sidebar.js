import { state } from '../state.js';
import { renderGrid } from './grid.js';


// Sidebar state lives in state.js (state.selectedSkillTags, state.selectedTopicTags)
let sidebarCollapsed = false;

// Extract tags from data
function extractTags() {
  // Part 1 skill tags
  const part1SkillCounts = {};
  state.part1Data.forEach(topic => {
    (topic.questions || []).forEach(q => {
      (q.type_tags || []).forEach(tag => {
        part1SkillCounts[tag] = (part1SkillCounts[tag] || 0) + 1;
      });
    });
  });

  // Part 2 skill tags
  const part2SkillCounts = {};
  state.part2Data.forEach(topic => {
    (topic.part3 || []).forEach(q => {
      (q.type_tags || []).forEach(tag => {
        part2SkillCounts[tag] = (part2SkillCounts[tag] || 0) + 1;
      });
    });
  });

  // Topic tags (skip first category tag, use semantic tags)
  const topicTagCounts = {};
  [...state.part1Data, ...state.part2Data].forEach(topic => {
    (topic.content_tags || []).slice(1).forEach(tag => {
      topicTagCounts[tag] = (topicTagCounts[tag] || 0) + 1;
    });
  });

  return {
    part1Skills: Object.entries(part1SkillCounts).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count),
    part2Skills: Object.entries(part2SkillCounts).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count),
    topicTags: Object.entries(topicTagCounts).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count)
  };
}

// Apply filters to data
function applyFilters(data, tab) {
  let filteredData = [...data];
  
  // Apply skill tag filters (only within current part)
  if (state.selectedSkillTags.length > 0) {
    filteredData = filteredData.filter(item => {
      const questions = tab === 'part1' ? (item.questions || []) : (item.part3 || []);
      return questions.some(q => 
        q.type_tags && q.type_tags.some(tag => state.selectedSkillTags.includes(tag))
      );
    });
  }
  
  // Apply topic tag filters
  if (state.selectedTopicTags.length > 0) {
    filteredData = filteredData.filter(item => 
      item.content_tags && item.content_tags.slice(1).some(tag => state.selectedTopicTags.includes(tag))
    );
  }
  
  return filteredData;
}

// Render sidebar HTML
function renderSidebar() {
  const tags = extractTags();
  const currentSkills = state.currentTab === 'part1' ? tags.part1Skills : tags.part2Skills;
  const hasFilters = state.selectedSkillTags.length > 0 || state.selectedTopicTags.length > 0;

  const sidebarHTML = `
    <div class="sidebar">
      <div class="sidebar-content">
        ${hasFilters ? `<button class="sidebar-clear-btn" onclick="window._sidebarClear()">✕ Clear filters</button>` : ''}
        <div class="sidebar-cols">
          <div class="sidebar-col">
            <div class="sidebar-col-label">Skill</div>
            ${currentSkills.map(tag => `
              <span class="ttag ttag-${tag.name}${state.selectedSkillTags.includes(tag.name) ? ' sidebar-active' : ''}"
                    onclick="window._sidebarSkill('${tag.name}')">
                ${tag.name} <span class="sidebar-count">${tag.count}</span>
              </span>
            `).join('')}
          </div>
          <div class="sidebar-col">
            <div class="sidebar-col-label">Topic</div>
            ${tags.topicTags.map(tag => `
              <span class="ctag ctag-tag${state.selectedTopicTags.includes(tag.name) ? ' sidebar-active' : ''}"
                    onclick="window._sidebarTopic('${tag.name}')">
                ${tag.name} <span class="sidebar-count">${tag.count}</span>
              </span>
            `).join('')}
          </div>
        </div>
      </div>
    </div>
  `;

  const sidebarRoot = document.getElementById('sidebar-root');
  if (sidebarRoot) sidebarRoot.innerHTML = sidebarHTML;
}

// Toggle functions
function toggleSkillTag(tagName) {
  const index = state.selectedSkillTags.indexOf(tagName);
  if (index > -1) state.selectedSkillTags.splice(index, 1);
  else state.selectedSkillTags.push(tagName);
  renderSidebar();
  applyFiltersAndRender();
}

function toggleTopicTag(tagName) {
  const index = state.selectedTopicTags.indexOf(tagName);
  if (index > -1) state.selectedTopicTags.splice(index, 1);
  else state.selectedTopicTags.push(tagName);
  renderSidebar();
  applyFiltersAndRender();
}

function clearAllFilters() {
  state.selectedSkillTags = [];
  state.selectedTopicTags = [];
  renderSidebar();
  renderGrid(state.currentTab);
}

function applyFiltersAndRender() {
  const data = state.currentTab === 'part1' ? state.part1Data : state.part2Data;
  const filteredData = applyFilters(data, state.currentTab);
  renderGrid(state.currentTab, filteredData);
}

// Global handlers called by inline onclick — bypasses any event delegation issues
window._sidebarSkill = function(tagName) { toggleSkillTag(tagName); };
window._sidebarTopic = function(tagName) { toggleTopicTag(tagName); };
window._sidebarClear = function() { clearAllFilters(); };

// Toggle sidebar visibility
function toggleSidebar() {
  sidebarCollapsed = !sidebarCollapsed;
  const sidebarRoot = document.getElementById('sidebar-root');
  const toggleBtn = document.getElementById('sidebar-toggle');
  if (sidebarRoot) sidebarRoot.style.width = sidebarCollapsed ? '0' : '360px';
  if (toggleBtn) toggleBtn.textContent = sidebarCollapsed ? '▶ Filters' : '◀ Filters';
}

// Tab change handler - clear skill tags but keep topic tags
function onTabChange(newTab) {
  state.selectedSkillTags = []; // Clear skill tags when switching tabs
  renderSidebar(); // Re-render sidebar with new skill tags
}

// Export init function — wires static listeners once; renderSidebar() called after data loads
export function initSidebar() {
  const toggleBtn = document.getElementById('sidebar-toggle');
  if (toggleBtn) toggleBtn.addEventListener('click', toggleSidebar);

  const tab1Btn = document.getElementById('tab-part1');
  const tab2Btn = document.getElementById('tab-part2');
  if (tab1Btn) tab1Btn.addEventListener('click', () => onTabChange('part1'));
  if (tab2Btn) tab2Btn.addEventListener('click', () => onTabChange('part2'));
}

// Called by data.js after JSON is loaded
export { renderSidebar };
