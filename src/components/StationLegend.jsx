import { CULEX_SCALE } from '../config/map.js'

// Legend for the focused site's station colors: the shared Culex scale (Step 2.6).
// onExplain opens the "About the station data" page (Step 2.7).
export default function StationLegend({ onExplain }) {
  const { stops, noDataColor } = CULEX_SCALE
  const gradient = `linear-gradient(to right, ${stops.map(([, c], i) => `${c} ${(i / (stops.length - 1)) * 100}%`).join(', ')})`
  return (
    <div className="station-legend">
      <div className="station-legend__title"><i>Culex</i> per trap night, all seasons</div>
      <div className="station-legend__bar" style={{ background: gradient }} />
      <div className="station-legend__labels">
        {stops.map(([v], i) => (
          <span key={v}>{i === stops.length - 1 ? `${v}+` : v}</span>
        ))}
      </div>
      <div className="station-legend__note">
        Same scale at every site. Hover a station for details.
        <span className="station-legend__nodata" style={{ background: noDataColor }} /> no data
      </div>
      {onExplain && (
        <button
          type="button"
          className="station-legend__explain"
          aria-haspopup="dialog"
          onClick={(e) => onExplain(e.currentTarget)}
        >
          What do these numbers mean?
        </button>
      )}
    </div>
  )
}
