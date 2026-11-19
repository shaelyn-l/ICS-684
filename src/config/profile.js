// Mountain profile (side view) settings. Data: public/data/profile.json, written by
// data-pipeline/scripts/05_profile.py.

export const PROFILE_URL = `${import.meta.env.BASE_URL}data/profile.json`

export const PROFILE = {
  height: 228, // px, the open strip. Collapsed, only its toggle tab shows (like the side panel).
  headerHeight: 28, // px, the title bar above the chart (chart height = height − headerHeight)
  tabHeight: 28, // px, the toggle tab above the strip's top edge
  collapsedBelow: 768, // px window width: narrower screens start collapsed

  // The profile stretches to fill the strip's width and height, so the vertical
  // exaggeration varies with screen width (about ×2.5–4 on desktop screens).

  margin: { top: 26, right: 20, bottom: 22, left: 52 }, // px around the plot (top leaves room for the summit label)
  yTickStep: 500, // m between elevation ticks

  groundFill: '#8d7b68',
  groundStroke: '#4f4335',
  markerRadius: 6,
  markerRadiusHighlighted: 9,
  // Minimum px between neighbouring site markers. Clustered sites are nudged
  // sideways (never up or down) to keep this gap, so elevations stay exact.
  markerMinGap: 17,

  // Dashed line on the map showing where the slice was taken.
  mapLine: { color: '#1a1a1a', width: 1.5, dash: [3, 2] },
}

// Malaria risk bands by elevation, warm (low, high risk) to cool (high, refuge).
// APPROXIMATE PLACEHOLDERS: these elevations stand in for the temperature thresholds
// (high risk >21°C, episodic 13–21°C, refuge <13°C; LaPointe et al. 2010) and will be
// replaced by temperature-derived elevations in Step 3.3.
// Labels are a parallel set (High / Moderate / Low risk) standing for high risk /
// episodic / refuge. `fill` is the background band, `marker` the color of site
// markers in the band.
export const RISK_KEY_TITLE = 'Avian malaria risk by elevation (approx.)'
export const RISK_BANDS = [
  { id: 'high_risk', label: 'High risk', from: 0, to: 900, fill: '#f8c9b4', marker: '#d6604d' },
  { id: 'episodic', label: 'Moderate risk', from: 900, to: 1500, fill: '#fbe6a8', marker: '#d9a21b' },
  { id: 'refuge', label: 'Low risk', from: 1500, to: Infinity, fill: '#c6dcef', marker: '#3f87c0' },
]

export const bandFor = (elevation) =>
  RISK_BANDS.find((b) => elevation >= b.from && elevation < b.to) ?? RISK_BANDS[RISK_BANDS.length - 1]
