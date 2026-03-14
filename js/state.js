export const state = {
  part1Data: [],        // array of Part 1 topic objects from merged_part1.json
  part2Data: [],        // array of Part 2+3 topic objects from merged_part2.json
  taxonomyV2Map: new Map(), // topic -> { l1, l2, l3 } runtime mapping
  currentTab: 'part1',
  lastActiveTag: null,  // content tag name — back returns to tag summary
  lastTypeSummary: null, // type tag name — back returns to type summary
  filterMode: 'blended', // 'focused' or 'blended'
  selectedSkillTags: [], // sidebar skill filter
  selectedL1Tag: null,   // single L1 category or null
  selectedL2Tags: [],    // multiple L2 tags
  selectedL3Tags: [],    // multiple L3 tags
  selectedTimeFrame: null // 'past' | 'present' | 'future' | null
};
