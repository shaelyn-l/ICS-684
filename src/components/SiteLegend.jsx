import { CULEX_SCALE, SITE_MARKER, siteRadius } from '../config/map.js'
import { PERIOD_LABELS } from '../config/periods.js'
import './SiteLegend.css'

// Legend for the site circles (Step 4.1): size = honeycreepers per count, color =
// Culex per trap night, both for the selected period. Also holds the checkbox
// that shows or hides the station dots.
export default function SiteLegend({ period, showStations, onToggleStations }) {
  const { legendValues } = SITE_MARKER.size
  const radii = legendValues.map(siteRadius)
  const pad = 2 // room for the outline
  const height = 2 * Math.max(...radii) + 2 * pad
  const gap = 10
  // Circles side by side, bottoms aligned, each with its value centered below.
  let x = pad
  const circles = legendValues.map((value, i) => {
    const r = radii[i]
    const cx = x + r
    x += 2 * r + gap
    return { value, r, cx }
  })
  const width = x - gap + pad

  const { stops, noDataColor } = CULEX_SCALE
  const gradient = `linear-gradient(to right, ${stops.map(([, c], i) => `${c} ${(i / (stops.length - 1)) * 100}%`).join(', ')})`

  return (
    <div className="site-legend">
      <div className="site-legend__period">Site circles · {PERIOD_LABELS[period]}</div>

      <div className="site-legend__title">Size: honeycreepers per count</div>
      <svg
        className="site-legend__sizes"
        width={width}
        height={height + 16}
        role="img"
        aria-label={`Circle sizes for ${legendValues.join(', ')} honeycreepers per count; larger circles mean more honeycreepers`}
      >
        {circles.map(({ value, r, cx }) => (
          <g key={value}>
            <circle
              cx={cx}
              cy={height - pad - r}
              r={r}
              fill="#e6e6e6"
              stroke={SITE_MARKER.strokeColor}
              strokeWidth={SITE_MARKER.strokeWidth}
            />
            <text x={cx} y={height + 12} textAnchor="middle">{value}</text>
          </g>
        ))}
      </svg>

      <div className="site-legend__title">Color: <i>Culex</i> per trap night</div>
      <div className="site-legend__bar" style={{ background: gradient }} />
      <div className="site-legend__labels">
        {stops.map(([v], i) => (
          <span key={v}>{i === stops.length - 1 ? `${v}+` : v}</span>
        ))}
      </div>
      <div className="site-legend__note">
        CO2 traps only. Same color scale as the stations.
        <span className="site-legend__nodata" style={{ borderColor: noDataColor }} /> no data
      </div>

      <label className="site-legend__toggle">
        <input
          type="checkbox"
          checked={showStations}
          onChange={(e) => onToggleStations(e.target.checked)}
        />
        Show sampling stations
        <span className="site-legend__hint">(visible when zoomed in)</span>
      </label>
    </div>
  )
}
