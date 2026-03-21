/** Shared skill L1 → L2 (subtype) mapping; single source for sidebar, badges, type summary. */
export const SKILL_TO_SUBTYPES = {
  experience:   ['have_you_ever', 'remember_when', 'how_often', 'do_you_usually'],
  description:  ['what_types', 'what_is_it', 'where_when_who', 'how_to'],
  preference:   ['do_you_like', 'which_prefer'],
  evaluation:   ['is_it_important', 'should_people', 'good_or_bad', 'do_you_agree'],
  analysis:     ['why', 'what_effect', 'what_pros_cons', 'how_does_it_work'],
  comparison:   ['what_differences', 'has_it_changed', 'better_or_worse'],
  hypothetical: ['do_you_want_to', 'what_if', 'will_it_happen'],
};

const _parentBySubtype = {};
for (const [l1, subs] of Object.entries(SKILL_TO_SUBTYPES)) {
  for (const s of subs) _parentBySubtype[s] = l1;
}

export const ALL_SKILL_SUBTYPES = new Set(Object.keys(_parentBySubtype));

export function parentSkillFromSubtype(subtype) {
  return _parentBySubtype[subtype] || '';
}
