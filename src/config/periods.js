// Periods the site data can be shown for. Each id is a `period` value in
// public/data/site_summary.json. Seasons follow the pipeline (04_site_summary.py):
// dry = May–Oct, wet = Nov–Apr, and a wet season is named by the year it starts,
// so "Wet 2002" is Nov 2002 – Apr 2003. The data ends in Oct 2004, so there is no
// 2004 wet season.
//
// button: text on the side panel button. heading: full name shown in the site
// popup and under the buttons.
export const PERIOD_GROUPS = [
  {
    label: 'Combined seasons',
    periods: [
      { id: 'all', button: 'All seasons', heading: 'All seasons · May 2002 – Oct 2004' },
      { id: 'wet', button: 'Rainy (wet)', heading: 'Rainy (wet) seasons combined · Nov–Apr' },
      { id: 'dry', button: 'Dry', heading: 'Dry seasons combined · May–Oct' },
    ],
  },
  {
    label: 'By season',
    periods: [
      { id: '2002-dry', button: 'Dry 2002', heading: 'Dry 2002 · May – Oct 2002' },
      { id: '2002-wet', button: 'Wet 2002', heading: 'Wet 2002 · Nov 2002 – Apr 2003' },
      { id: '2003-dry', button: 'Dry 2003', heading: 'Dry 2003 · May – Oct 2003' },
      { id: '2003-wet', button: 'Wet 2003', heading: 'Wet 2003 · Nov 2003 – Apr 2004' },
      { id: '2004-dry', button: 'Dry 2004', heading: 'Dry 2004 · May – Oct 2004' },
    ],
  },
]

export const DEFAULT_PERIOD = 'all'

// period id -> heading, for the popup
export const PERIOD_HEADINGS = Object.fromEntries(
  PERIOD_GROUPS.flatMap((g) => g.periods).map((p) => [p.id, p.heading]))
