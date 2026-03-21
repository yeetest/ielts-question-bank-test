import { parentSkillFromSubtype } from './skillTaxonomy.js';

export function renderSkillBadge(q) {
  const subtype = q.skill_subtype;
  const primaryL1 = (q.skill_tags && q.skill_tags[0]) || '';
  const parentForStyle = parentSkillFromSubtype(subtype) || primaryL1;
  if (!subtype && !primaryL1) return '';
  const display = subtype || primaryL1;
  const summaryKey = subtype || primaryL1;
  return `<span class="type-tags">
    <span class="ttag ttag-${parentForStyle}" data-type-tag="${summaryKey}" data-skill-parent="${parentForStyle}">${display.replace(/_/g, ' ')}</span>
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
  const normalizedTag = tagName === 'experience/activity' ? 'experience_activity' : tagName;
  if (!ct) return false;
  if (Array.isArray(ct)) return ct.includes(tagName) || ct.includes(normalizedTag);
  if (typeof ct === 'object' && !Array.isArray(ct) && ('l1' in ct || 'l2' in ct || 'l3' in ct)) {
    const l2 = Array.isArray(ct.l2) ? ct.l2 : (ct.l2 ? [ct.l2] : []);
    const l3 = Array.isArray(ct.l3) ? ct.l3 : (ct.l3 ? [ct.l3] : []);
    return ct.l1 === tagName || ct.l1 === normalizedTag || l2.includes(tagName) || l2.includes(normalizedTag) || l3.includes(tagName) || l3.includes(normalizedTag);
  }
  return ct.l1 === tagName
    || ct.l1 === normalizedTag
    || (ct.l2 || []).includes(tagName)
    || (ct.l2 || []).includes(normalizedTag)
    || (ct.l3 || []).includes(tagName)
    || (ct.l3 || []).includes(normalizedTag);
}

// Returns taxonomy used specifically for filtering (v2 mapping first, legacy fallback second).
export function getFilterTaxonomy(topic) {
  const tx = topic?.taxonomy_v2_primary;
  if (tx && typeof tx === 'object') {
    return {
      l1: tx.l1 || '',
      l2: tx.l2 ? [tx.l2] : [],
      l3: tx.l3 ? [tx.l3] : [],
    };
  }
  const ct = topic?.content_tags;
  if (!ct) return { l1: '', l2: [], l3: [] };
  if (Array.isArray(ct)) return { l1: ct[0] || '', l2: ct.slice(1), l3: [] };
  return {
    l1: ct.l1 || '',
    l2: Array.isArray(ct.l2) ? ct.l2 : (ct.l2 ? [ct.l2] : []),
    l3: Array.isArray(ct.l3) ? ct.l3 : (ct.l3 ? [ct.l3] : []),
  };
}

// Cleans up Part 2 cue card prompts: removes "Describe", "You should say...", zero-width chars.
export function cleanTitle(raw) {
  return (raw || '')
    .replace(/[\u200b\u200c\u200d\ufeff]/g, '')
    .replace(/\s*You should say.*/is, '')
    .replace(/^\s*Describe\s+/i, '')
    .trim();
}
