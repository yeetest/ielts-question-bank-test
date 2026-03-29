import { loadData, sectionFromURL, setSectionInURL, writingTabFromURL } from './shared/data.js';
import { openModal, closeOverlay } from './speaking/modal.js';
import { openTagSummary, openTypeSummary } from './speaking/tagSummary.js';
import { initSidebar, renderSidebar } from './speaking/sidebar.js';
import { renderGrid } from './components/grid.js';
import { closeAuthModal, refreshSession } from './writing/auth.js';
import { state } from './shared/state.js';

function resetSpeakingFilters() {
  state.selectedSkillTags = [];
  state.selectedSkillSubtypes = [];
  state.selectedL1Tag = null;
  state.selectedL2Tags = [];
  state.selectedL3Tags = [];
  state.selectedTimeFrame = null;
  state.lastActiveTag = null;
  state.lastTypeSummary = null;
}

function updateNav() {
  document.getElementById('nav-speaking').classList.toggle('active', state.currentSection === 'speaking');
  document.getElementById('nav-writing').classList.toggle('active', state.currentSection === 'writing');
}

function updatePageChrome() {
  const pageTitle = document.getElementById('page-title');
  const sectionMeta = document.getElementById('section-meta');
  const tabs = document.querySelector('.tabs');
  const sidebarRoot = document.getElementById('sidebar-root');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const tab1 = document.getElementById('tab-part1');
  const tab2 = document.getElementById('tab-part2');

  tabs.style.display = 'flex';
  if (state.currentSection === 'speaking') {
    document.title = 'IELTS Speaking Question Bank';
    pageTitle.textContent = 'IELTS Speaking Question Bank';
    sectionMeta.textContent = 'Jan–Apr 2026';
    tab1.textContent = 'Part 1';
    tab2.textContent = 'Part 2 + Part 3';
    sidebarToggle.style.display = '';
    sidebarRoot.style.display = '';
    return;
  }

  document.title = 'IELTS Writing Question Bank';
  pageTitle.textContent = 'IELTS Writing Question Bank';
  sectionMeta.textContent = 'IELTS General Training Writing';
  tab1.textContent = 'Task 1';
  tab2.textContent = 'Task 2';
  sidebarToggle.style.display = 'none';
  sidebarRoot.innerHTML = '';
  sidebarRoot.style.display = 'none';
}

function switchSection(section) {
  if (!['speaking', 'writing'].includes(section)) return;
  closeOverlay();
  state.currentSection = section;
  setSectionInURL(section);
  resetSpeakingFilters();

  if (section === 'speaking') {
    state.currentTab = 'part1';
    renderSidebar();
  } else if (section === 'writing') {
    state.currentTab = 'task1';
  }

  updateNav();
  updatePageChrome();
  renderGrid(state.currentTab);
  refreshSession();
}

function switchSubtab(tab) {
  if (state.currentSection === 'speaking' && !['part1', 'part2'].includes(tab)) return;
  if (state.currentSection === 'writing' && !['task1', 'task2'].includes(tab)) return;
  closeOverlay();
  if (state.currentSection === 'speaking') {
    resetSpeakingFilters();
    state.currentTab = tab;
    renderSidebar();
  } else {
    state.currentTab = tab;
  }
  renderGrid(state.currentTab);
}

document.addEventListener('DOMContentLoaded', async () => {
  initSidebar();

  document.getElementById('nav-speaking').addEventListener('click', () => switchSection('speaking'));
  document.getElementById('nav-writing').addEventListener('click', () => switchSection('writing'));

  document.getElementById('tab-part1').addEventListener('click', () => {
    switchSubtab(state.currentSection === 'writing' ? 'task1' : 'part1');
  });
  document.getElementById('tab-part2').addEventListener('click', () => {
    switchSubtab(state.currentSection === 'writing' ? 'task2' : 'part2');
  });

  document.getElementById('close-btn').addEventListener('click', closeOverlay);
  document.getElementById('auth-close-btn').addEventListener('click', closeAuthModal);
  document.getElementById('overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('overlay')) closeOverlay();
  });
  document.getElementById('auth-overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('auth-overlay')) closeAuthModal();
  });

  document.getElementById('grid').addEventListener('click', e => {
    if (state.currentSection === 'speaking') {
      const ctag = e.target.closest('[data-content-tag]');
      if (ctag) {
        e.stopPropagation();
        openTagSummary(ctag.dataset.contentTag);
        return;
      }
    }

    const card = e.target.closest('.card');
    if (card) {
      state.lastActiveTag = null;
      state.lastTypeSummary = null;
      if (state.currentSection === 'writing') {
        const practiceId = card.dataset.practiceId;
        if (!practiceId) return;
        window.location.assign(`./practice.html?practice=${encodeURIComponent(practiceId)}`);
        return;
      }
      openModal(card.dataset.tab, parseInt(card.dataset.idx, 10));
    }
  });

  document.getElementById('modal-content').addEventListener('click', e => {
    if (state.currentSection !== 'speaking') return;

    const ctag = e.target.closest('[data-content-tag]');
    if (ctag) { openTagSummary(ctag.dataset.contentTag); return; }

    const ttag = e.target.closest('[data-type-tag]');
    if (ttag) { openTypeSummary(ttag.dataset.typeTag); return; }

    const summaryItem = e.target.closest('[data-modal-idx]');
    if (summaryItem) {
      openModal(summaryItem.dataset.modalTab, parseInt(summaryItem.dataset.modalIdx, 10));
    }
  });

  try {
    await loadData();
    await refreshSession();
  } catch (e) {
    console.error(e);
    alert('Could not load data. See console for details.');
    return;
  }

  state.currentSection = sectionFromURL();
  if (state.currentSection === 'speaking') {
    state.currentTab = 'part1';
    renderSidebar();
  } else if (state.currentSection === 'writing') {
    state.currentTab = writingTabFromURL();
  }

  updateNav();
  updatePageChrome();
  renderGrid(state.currentTab);
  await refreshSession();
});
