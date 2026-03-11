export const state = {
  part1Data: [],        // array of Part 1 topic objects from merged_part1.json
  part2Data: [],        // array of Part 2+3 topic objects from merged_part2.json
  currentTab: 'part1',
  lastActiveTag: null,  // content tag name — back returns to tag summary
  lastTypeSummary: null, // type tag name — back returns to type summary
  selectedSkillTags: [], // sidebar skill filter
  selectedL1Tag: null,   // single L1 category or null
  selectedL2Tags: [],    // multiple L2 tags
  selectedL3Tags: []     // multiple L3 tags
};
