// Builds the colored skill tag badges (8-type unified taxonomy)
// shown next to each question.
export function renderSkillTags(tags) {
  if (!tags || !tags.length) return '';
  return `<span class="type-tags">
    ${tags.map(t =>
      `<span class="ttag ttag-${t}" data-type-tag="${t}">${t}</span>`
    ).join('')}
  </span>`;
}

// Renders the lowest-level topic tags (L3, or L2 if no L3) inline after a question.
export function renderInlineTopicTags(ct) {
  if (!ct || Array.isArray(ct)) return '';
  const tags = (ct.l3 && ct.l3.length > 0) ? ct.l3 : (ct.l2 || []);
  if (!tags.length) return '';
  return `<span class="inline-topic-tags">
    ${tags.map(t =>
      `<span class="itag" data-content-tag="${t}">${t.replace(/_/g, ' ')}</span>`
    ).join('')}
  </span>`;
}

// Builds the content tag row shown on each card.
// Handles both old flat array and new structured {l1, l2, l3} format.
export function renderContentTags(ct) {
  if (!ct) return '';

  // New structured format
  if (!Array.isArray(ct) && typeof ct === 'object') {
    const badges = [];
    if (ct.l1) {
      badges.push(`<span class="ctag ctag-${ct.l1.replace('/', '-')}" data-content-tag="${ct.l1}">${ct.l1}</span>`);
    }
    (ct.l2 || []).forEach(tag => {
      badges.push(`<span class="ctag ctag-tag" data-content-tag="${tag}">${tag.replace(/_/g, ' ')}</span>`);
    });
    (ct.l3 || []).forEach(tag => {
      badges.push(`<span class="ctag ctag-tag" data-content-tag="${tag}">${tag.replace(/_/g, ' ')}</span>`);
    });
    if (!badges.length) return '';
    return `<div class="tag-row">${badges.join('')}</div>`;
  }

  // Old flat array format (fallback)
  if (!ct.length) return '';
  const badges = ct.map((tag, i) => {
    const colorClass = i === 0
      ? `ctag-${tag.replace('/', '-')}`
      : 'ctag-tag';
    return `<span class="ctag ${colorClass}" data-content-tag="${tag}">${tag}</span>`;
  }).join('');
  return `<div class="tag-row">${badges}</div>`;
}

// Returns true if a topic's content_tags contains a given tag name (any layer).
export function hasContentTag(ct, tagName) {
  if (!ct) return false;
  if (Array.isArray(ct)) return ct.includes(tagName);
  return ct.l1 === tagName
    || (ct.l2 || []).includes(tagName)
    || (ct.l3 || []).includes(tagName);
}

// Cleans up Part 2 cue card prompts: removes "Describe", "You should say...", zero-width chars.
export function cleanTitle(raw) {
  return (raw || '')
    .replace(/[\u200b\u200c\u200d\ufeff]/g, '')
    .replace(/\s*You should say.*/is, '')
    .replace(/^\s*Describe\s+/i, '')
    .trim();
}
