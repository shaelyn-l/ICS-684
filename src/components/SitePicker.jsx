import StationLegend from './StationLegend.jsx'
import './SitePicker.css'

// Navigation only: buttons move the camera; site information stays in the map popup.
export default function SitePicker({ sites, focusedSite, onFocusSite, onExplainStations }) {
  if (!sites) return <p className="site-picker__loading">Loading sites…</p>

  const ordered = [...sites.features]
    .map((f) => f.properties)
    .sort((a, b) => a.elevation_m - b.elevation_m)

  return (
    <div className="site-picker">
      <button
        type="button"
        className="site-picker__overview"
        onClick={() => onFocusSite(null)}
      >
        Overview
      </button>
      <div className="site-picker__grid" role="group" aria-label="Fly to a site (lowest to highest)">
        {ordered.map(({ site }) => (
          <button
            key={site}
            type="button"
            className="site-picker__site"
            aria-pressed={focusedSite === site}
            onClick={() => onFocusSite(site)}
          >
            {site}
          </button>
        ))}
      </div>
      {/* Station colors only apply to a focused site, so the legend only shows then. */}
      {focusedSite && <StationLegend onExplain={onExplainStations} />}
    </div>
  )
}
