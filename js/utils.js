// Builds the colored question-type tag badges (describe / analyze / evaluate / predict)
// shown next to each Part 3 question.
export function renderTypeTags(tags) {
  if (!tags || !tags.length) return '';
  return `<span class="type-tags">
    ${tags.map(t =>
      `<span class="ttag ttag-${t}" data-type-tag="${t}">${t}</span>`
    ).join('')}
  </span>`;
}

// Builds the content tag row shown on each card.
// First tag gets a category color class; the rest get the neutral .ctag-tag style.
export function renderContentTags(tags) {
  if (!tags || !tags.length) return '';
  const badges = tags.map((tag, i) => {
    const colorClass = i === 0
      ? `ctag-${tag.replace('/', '-')}`  // e.g. ctag-experience-activity
      : 'ctag-tag';                       // all semantic tags use neutral purple
    return `<span class="ctag ${colorClass}" data-content-tag="${tag}">${tag}</span>`;
  }).join('');
  return `<div class="tag-row">${badges}</div>`;
}

// Cleans up Part 2 cue card prompts: removes "Describe", "You should say...", zero-width chars.
export function cleanTitle(raw) {
  return (raw || '')
    .replace(/[\u200b\u200c\u200d\ufeff]/g, '')
    .replace(/\s*You should say.*/is, '')
    .replace(/^\s*Describe\s+/i, '')
    .trim();
}
