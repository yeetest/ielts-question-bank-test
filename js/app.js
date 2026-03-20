import { loadData, quarterFromURL, setQuarterInURL, QUARTER_IDS } from './data.js';
import { openModal, openOverlay, closeOverlay } from './components/modal.js';
import { openTagSummary, openTypeSummary } from './components/tagSummary.js';
import { initSidebar } from './components/sidebar.js';
import { state } from './state.js';

function resetFiltersForQuarterSwitch() {
  state.selectedSkillTags = [];
  state.selectedL1Tag = null;
  state.selectedL2Tags = [];
  state.selectedL3Tags = [];
  state.selectedTimeFrame = null;
  state.lastActiveTag = null;
  state.lastTypeSummary = null;
}

async function applyQuarter(quarterId) {
  if (!QUARTER_IDS.includes(quarterId)) return;
  closeOverlay();
  resetFiltersForQuarterSwitch();
  state.currentTab = 'part1';
  setQuarterInURL(quarterId);
  try {
    await loadData(quarterId);
  } catch (e) {
    console.error(e);
    alert('Could not load quarter data. See console for details.');
  }
}

document.addEventListener('DOMContentLoaded', () => {

  initSidebar();

  document.getElementById('close-btn').addEventListener('click', closeOverlay);

  document.getElementById('overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('overlay')) closeOverlay();
  });

  document.getElementById('grid').addEventListener('click', e => {
    const ctag = e.target.closest('[data-content-tag]');
    if (ctag) {
      e.stopPropagation();
      openTagSummary(ctag.dataset.contentTag);
      return;
    }
    const card = e.target.closest('.card');
    if (card) {
      state.lastActiveTag = null;
      state.lastTypeSummary = null;
      openModal(card.dataset.tab, parseInt(card.dataset.idx));
    }
  });

  document.getElementById('modal-content').addEventListener('click', e => {
    const ctag = e.target.closest('[data-content-tag]');
    if (ctag) { openTagSummary(ctag.dataset.contentTag); return; }

    const ttag = e.target.closest('[data-type-tag]');
    if (ttag) { openTypeSummary(ttag.dataset.typeTag); return; }

    const summaryItem = e.target.closest('[data-modal-idx]');
    if (summaryItem) {
      openModal(summaryItem.dataset.modalTab, parseInt(summaryItem.dataset.modalIdx));
    }
  });

  const sel = document.getElementById('quarter-select');
  if (sel) {
    sel.addEventListener('change', () => applyQuarter(sel.value));
  }

  const initial = quarterFromURL();
  if (sel) sel.value = initial;
  applyQuarter(initial);
});
