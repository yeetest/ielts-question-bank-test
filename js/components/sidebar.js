import { state } from '../state.js';
import { renderGrid } from './grid.js';


// Sidebar state
let selectedSkillTags = [];
let selectedTopicTags = [];
let isSkillsExpanded = true;
let isTopicsExpanded = true;

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
  if (selectedSkillTags.length > 0) {
    filteredData = filteredData.filter(item => {
      const questions = tab === 'part1' ? (item.questions || []) : (item.part3 || []);
      return questions.some(q => 
        q.type_tags && q.type_tags.some(tag => selectedSkillTags.includes(tag))
      );
    });
  }
  
  // Apply topic tag filters
  if (selectedTopicTags.length > 0) {
    filteredData = filteredData.filter(item => 
      item.content_tags && item.content_tags.slice(1).some(tag => selectedTopicTags.includes(tag))
    );
  }
  
  return filteredData;
}

// Render sidebar HTML
function renderSidebar() {
  const tags = extractTags();
  const currentSkills = state.currentTab === 'part1' ? tags.part1Skills : tags.part2Skills;
  const hasFilters = selectedSkillTags.length > 0 || selectedTopicTags.length > 0;

  const sidebarHTML = `
    <div class="sidebar">
      <div class="sidebar-content">
        ${hasFilters ? `<button class="sidebar-clear-btn" onclick="window._sidebarClear()">✕ Clear filters</button>` : ''}
        <div class="sidebar-cols">
          <div class="sidebar-col">
            <div class="sidebar-col-label">Skill</div>
            ${currentSkills.map(tag => `
              <span class="ttag ttag-${tag.name}${selectedSkillTags.includes(tag.name) ? ' sidebar-active' : ''}"
                    onclick="window._sidebarSkill('${tag.name}')">
                ${tag.name} <span class="sidebar-count">${tag.count}</span>
              </span>
            `).join('')}
          </div>
          <div class="sidebar-col">
            <div class="sidebar-col-label">Topic</div>
            ${tags.topicTags.map(tag => `
              <span class="ctag ctag-tag${selectedTopicTags.includes(tag.name) ? ' sidebar-active' : ''}"
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
  const index = selectedSkillTags.indexOf(tagName);
  if (index > -1) selectedSkillTags.splice(index, 1);
  else selectedSkillTags.push(tagName);
  renderSidebar();
  applyFiltersAndRender();
}

function toggleTopicTag(tagName) {
  const index = selectedTopicTags.indexOf(tagName);
  if (index > -1) selectedTopicTags.splice(index, 1);
  else selectedTopicTags.push(tagName);
  renderSidebar();
  applyFiltersAndRender();
}

function clearAllFilters() {
  selectedSkillTags = [];
  selectedTopicTags = [];
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
  const sidebar = document.querySelector('.sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle');
  if (!sidebar) return;
  const collapsed = sidebar.classList.toggle('collapsed');
  if (toggleBtn) toggleBtn.textContent = collapsed ? '▶ Filters' : '◀ Filters';
}

// Tab change handler - clear skill tags but keep topic tags
function onTabChange(newTab) {
  selectedSkillTags = []; // Clear skill tags when switching tabs
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
