import { loadData } from './data.js';
import { renderGrid } from './components/grid.js';
import { openModal, openOverlay, closeOverlay } from './components/modal.js';
import { openTagSummary, openTypeSummary } from './components/tagSummary.js';
import { state } from './state.js';

document.addEventListener('DOMContentLoaded', () => {

  // Tab buttons
  document.getElementById('tab-part1').addEventListener('click', () => renderGrid('part1'));
  document.getElementById('tab-part2').addEventListener('click', () => renderGrid('part2'));

  // Close button inside modal
  document.getElementById('close-btn').addEventListener('click', closeOverlay);

  // Click outside modal to close
  document.getElementById('overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('overlay')) closeOverlay();
  });

  // Event delegation on grid: card clicks, content tag clicks
  document.getElementById('grid').addEventListener('click', e => {
    // Content tag click (ctag) — stop propagation so card doesn't also open
    const ctag = e.target.closest('[data-content-tag]');
    if (ctag) {
      e.stopPropagation();
      openTagSummary(ctag.dataset.contentTag);
      return;
    }
    // Card click — open topic detail modal (no back button)
    const card = e.target.closest('.card');
    if (card) {
      state.lastActiveTag = null;
      state.lastTypeSummary = null;
      openModal(card.dataset.tab, parseInt(card.dataset.idx));
    }
  });

  // Event delegation on modal: content tag clicks, type tag clicks, summary item clicks
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

  // Load data and render initial grid
  loadData();
});
