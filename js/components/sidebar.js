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
  
  const sidebarHTML = `
    <div class="sidebar">
      <div class="sidebar-content">
        <!-- Active Filters Summary -->
        <div class="active-filters" id="active-filters" style="display: none;">
          <p class="active-filters-label">已选 Selected:</p>
          <div class="active-filters-list" id="active-filters-list"></div>
        </div>
        
        <!-- Clear Filters Button -->
        <button class="clear-filters-btn" id="clear-filters" style="display: none;">清除 Clear</button>
        
        <!-- Two Column Grid -->
        <div class="sidebar-grid">
          <!-- Skills Column -->
          <div class="sidebar-column">
            <div class="section-label">题型 Skill</div>
            ${currentSkills.map(tag => `
              <span class="ttag ttag-${tag.name} ${selectedSkillTags.includes(tag.name) ? 'active' : ''}" 
                    data-sidebar-skill="${tag.name}" 
                    style="cursor: pointer;">
                ${tag.name} (${tag.count})
              </span>
            `).join('')}
          </div>
          
          <!-- Topics Column -->
          <div class="sidebar-column">
            <div class="section-label">话题 Topics</div>
            ${tags.topicTags.map(tag => `
              <span class="ctag ctag-tag ${selectedTopicTags.includes(tag.name) ? 'active' : ''}" 
                    data-sidebar-topic="${tag.name}" 
                    style="cursor: pointer;">
                ${tag.name} (${tag.count})
              </span>
            `).join('')}
          </div>
          
          <!-- Filter Logic Info -->
          <div class="filter-info">
            <p><strong>筛选逻辑：</strong><span id="filter-logic-text">点击标签开始筛选</span></p>
          </div>
        </div>
      </div>
    </div>
  `;
  
  const sidebarRoot = document.getElementById('sidebar-root');
  if (sidebarRoot) {
    sidebarRoot.innerHTML = sidebarHTML;
    updateFilterStates();
    updateActiveFiltersDisplay();
    updateFilterLogicText();
    updateSidebarToggleText();
  }
}

// Toggle functions
function toggleSkillTag(tagName) {
  const index = selectedSkillTags.indexOf(tagName);
  if (index > -1) {
    selectedSkillTags.splice(index, 1);
  } else {
    selectedSkillTags.push(tagName);
  }
  updateFilterStates();
  updateActiveFiltersDisplay();
  updateFilterLogicText();
  applyFiltersAndRender();
}

function toggleTopicTag(tagName) {
  const index = selectedTopicTags.indexOf(tagName);
  if (index > -1) {
    selectedTopicTags.splice(index, 1);
  } else {
    selectedTopicTags.push(tagName);
  }
  updateFilterStates();
  updateActiveFiltersDisplay();
  updateFilterLogicText();
  applyFiltersAndRender();
}

function clearAllFilters() {
  selectedSkillTags = [];
  selectedTopicTags = [];
  updateFilterStates();
  updateActiveFiltersDisplay();
  updateFilterLogicText();
  renderGrid(state.currentTab);
}

function applyFiltersAndRender() {
  const data = state.currentTab === 'part1' ? state.part1Data : state.part2Data;
  const filteredData = applyFilters(data, state.currentTab);
  renderGrid(state.currentTab, filteredData);
}

// Update functions
function updateFilterStates() {
  // Update skill tag active states
  document.querySelectorAll('[data-sidebar-skill]').forEach(tag => {
    const tagName = tag.dataset.sidebarSkill;
    tag.classList.toggle('active', selectedSkillTags.includes(tagName));
  });
  
  // Update topic tag active states
  document.querySelectorAll('[data-sidebar-topic]').forEach(tag => {
    const tagName = tag.dataset.sidebarTopic;
    tag.classList.toggle('active', selectedTopicTags.includes(tagName));
  });
  
  // Show/hide clear button
  const hasFilters = selectedSkillTags.length > 0 || selectedTopicTags.length > 0;
  const clearBtn = document.getElementById('clear-filters');
  const activeFilters = document.getElementById('active-filters');
  if (clearBtn) clearBtn.style.display = hasFilters ? 'block' : 'none';
  if (activeFilters) activeFilters.style.display = hasFilters ? 'block' : 'none';
}

function updateActiveFiltersDisplay() {
  const container = document.getElementById('active-filters-list');
  if (!container) return;
  
  const tags = [
    ...selectedSkillTags.map(tag => ({ type: 'skill', name: tag })),
    ...selectedTopicTags.map(tag => ({ type: 'topic', name: tag }))
  ];
  
  container.innerHTML = tags.map(tag => `
    <span class="active-filter-tag ${tag.type}">
      ${tag.name}
      <button onclick="window.removeFilter('${tag.type}', '${tag.name}')">×</button>
    </span>
  `).join('');
}

function updateFilterLogicText() {
  const text = document.getElementById('filter-logic-text');
  if (!text) return;
  
  const hasSkills = selectedSkillTags.length > 0;
  const hasTopics = selectedTopicTags.length > 0;
  
  if (hasSkills && hasTopics) {
    text.textContent = '题型 + 话题 同时匹配 (AND 逻辑)';
  } else if (hasSkills && !hasTopics) {
    text.textContent = '仅筛选当前 Part 内的题型';
  } else if (!hasSkills && hasTopics) {
    text.textContent = '话题标签跨 Part 全局搜索';
  } else {
    text.textContent = '点击标签开始筛选';
  }
}

// Make removeFilter globally accessible
window.removeFilter = function(type, tagName) {
  if (type === 'skill') {
    toggleSkillTag(tagName);
  } else {
    toggleTopicTag(tagName);
  }
};

// Event listeners — only called once from initSidebar(), not on re-render
function attachStaticEventListeners() {
  // Sidebar toggle button in tabs bar
  const sidebarToggleBtn = document.getElementById('sidebar-toggle');
  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', toggleSidebar);
  }

  // Delegate all sidebar tag/button clicks on the persistent #sidebar-root element
  const sidebarRoot = document.getElementById('sidebar-root');
  if (sidebarRoot) {
    sidebarRoot.addEventListener('click', e => {
      // Clear filters button
      if (e.target.id === 'clear-filters') { clearAllFilters(); return; }

      // Skill tag click
      const skillTag = e.target.closest('[data-sidebar-skill]');
      if (skillTag) { toggleSkillTag(skillTag.dataset.sidebarSkill); return; }

      // Topic tag click
      const topicTag = e.target.closest('[data-sidebar-topic]');
      if (topicTag) { toggleTopicTag(topicTag.dataset.sidebarTopic); return; }
    });
  }
}

// Toggle sidebar visibility
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle');
  
  if (sidebar.classList.contains('collapsed')) {
    sidebar.classList.remove('collapsed');
    if (toggleBtn) toggleBtn.textContent = '◀ 收起筛选';
  } else {
    sidebar.classList.add('collapsed');
    if (toggleBtn) toggleBtn.textContent = '▶ 展开筛选';
  }
}

// Update sidebar toggle button text
function updateSidebarToggleText() {
  const toggleBtn = document.getElementById('sidebar-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.textContent = sidebar.classList.contains('collapsed') ? '▶ 展开筛选' : '◀ 收起筛选';
  }
}

// Tab change handler - clear skill tags but keep topic tags
function onTabChange(newTab) {
  selectedSkillTags = []; // Clear skill tags when switching tabs
  renderSidebar(); // Re-render sidebar with new skill tags
}

// Export init function — wires all static listeners once; renderSidebar() called after data loads
export function initSidebar() {
  attachStaticEventListeners();

  const tab1Btn = document.getElementById('tab-part1');
  const tab2Btn = document.getElementById('tab-part2');
  if (tab1Btn) tab1Btn.addEventListener('click', () => onTabChange('part1'));
  if (tab2Btn) tab2Btn.addEventListener('click', () => onTabChange('part2'));
}

// Called by data.js after JSON is loaded
export { renderSidebar };
