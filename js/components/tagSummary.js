import { state } from '../state.js';
import { hasContentTag } from '../utils.js';
import { openOverlay } from './modal.js';

export function openTagSummary(tagName) {
  state.lastActiveTag = tagName;
  state.lastTypeSummary = null;

  const matches = [];
  state.part1Data.forEach((item, idx) => {
    if (hasContentTag(item.content_tags, tagName))
      matches.push({ label: item.topic_en, idx, tab: 'part1' });
  });
  state.part2Data.forEach((item, idx) => {
    if (hasContentTag(item.content_tags, tagName))
      matches.push({ label: item.topic || item.topic_en, idx, tab: 'part2' });
  });

  const items = matches.map(m =>
    `<div class="summary-item" data-modal-idx="${m.idx}" data-modal-tab="${m.tab}">
      <span style="font-size:0.7rem;color:#aaa;margin-right:4px">Part ${m.tab === 'part1' ? '1' : '2'}</span>${m.label}
    </div>`
  ).join('');

  document.getElementById('modal-content').innerHTML = `
    <h2>Topics tagged: ${tagName}</h2>
    <div class="section-label">${matches.length} matches</div>
    <div class="cue-card">
      <div class="prompt">Topics in this category:</div>
      <div style="margin-top:10px">${items}</div>
    </div>
  `;
  openOverlay();
}

export function openTypeSummary(typeName) {
  state.lastTypeSummary = typeName;
  state.lastActiveTag = null;

  const results = [];
  state.part1Data.forEach((topic, idx) => {
    (topic.questions || [])
      .filter(q => q.type_tags && q.type_tags.includes(typeName))
      .forEach(q => results.push({ topicTitle: topic.topic_en, text: q.text, part: 1, idx }));
  });
  state.part2Data.forEach((topic, idx) => {
    (topic.part3 || [])
      .filter(q => q.type_tags && q.type_tags.includes(typeName))
      .forEach(q => results.push({ topicTitle: topic.topic || topic.topic_en, text: q.text, part: 2, idx }));
  });

  const rows = results.map(res => {
    const tab = res.part === 1 ? 'part1' : 'part2';
    return `
      <div class="summary-item" data-modal-idx="${res.idx}" data-modal-tab="${tab}"
           style="margin-bottom:12px; border-bottom:1px solid #eee; padding-bottom:8px;">
        <div style="font-weight:bold; color:#6366f1; font-size:0.75rem;">Part ${res.part} · ${res.topicTitle}</div>
        <div>${res.text}</div>
      </div>
    `;
  }).join('');

  document.getElementById('modal-content').innerHTML = `
    <h2>Question Type: ${typeName}</h2>
    <div class="section-label">${results.length} questions found</div>
    <div class="cue-card">
      <div class="prompt">Questions categorized as ${typeName}:</div>
      <div style="margin-top:10px; font-size:0.85rem;">${rows}</div>
    </div>
  `;
  openOverlay();
}
