import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { area, max, range, scaleLinear } from 'd3'
import { PROFILE, RISK_BANDS, RISK_KEY_TITLE, bandFor } from '../config/profile.js'
import './ProfileView.css'

const fmtM = (m) => `${Math.round(m).toLocaleString('en-US')} m`
const LABEL_FONT = 11 // px
const LABEL_CHAR_W = 6.3 // px, rough width of one label character
const LABEL_LINE = 13 // px between stacked labels
const KEY_FONT = "11px system-ui, -apple-system, 'Segoe UI', sans-serif" // matches the CSS
const KEY_PAD = 8 // px inside the key box
const KEY_SWATCH = 15 // px from a swatch's left edge to its label
const KEY_GAP = 18 // px between one item's label and the next swatch

// Width of a piece of text in px, measured with a canvas so key items can be spaced
// evenly whatever their label lengths.
let measureCtx
function textWidth(text, font) {
  measureCtx ??= document.createElement('canvas').getContext('2d')
  measureCtx.font = font
  return measureCtx.measureText(text).width
}

// Risk key layout: each item starts KEY_GAP after the previous label ends, so the
// gaps between items are equal; the box fits the wider of the title and the row.
function keyLayout() {
  let x = KEY_PAD
  const items = RISK_BANDS.map((b) => {
    const item = { ...b, x }
    x += KEY_SWATCH + textWidth(b.label, KEY_FONT) + KEY_GAP
    return item
  })
  const rowWidth = x - KEY_GAP + KEY_PAD
  const titleWidth = textWidth(RISK_KEY_TITLE, `600 ${KEY_FONT}`) + 2 * KEY_PAD
  return { items, width: Math.ceil(Math.max(rowWidth, titleWidth)) }
}

// Nudges site markers sideways so neighbours are at least markerMinGap apart, keeping
// their elevations (y) exact. Each cluster of too-close markers is spread evenly around
// the cluster's original centre; clusters that then touch are merged and re-spread.
function spreadMarkers(points, plotWidth) {
  const gap = PROFILE.markerMinGap
  let clusters = points.map((p) => ({ members: [p], centre: p.x }))
  let merged = true
  while (merged) {
    merged = false
    for (let i = 0; i < clusters.length - 1; i++) {
      const a = clusters[i]
      const b = clusters[i + 1]
      const aRight = a.centre + ((a.members.length - 1) * gap) / 2
      const bLeft = b.centre - ((b.members.length - 1) * gap) / 2
      if (bLeft - aRight < gap) {
        const members = [...a.members, ...b.members]
        const centre = members.reduce((sum, p) => sum + p.x, 0) / members.length
        clusters.splice(i, 2, { members, centre })
        merged = true
        break
      }
    }
  }
  return clusters.flatMap(({ members, centre }) => {
    const width = (members.length - 1) * gap
    const start = Math.min(Math.max(centre - width / 2, 0), plotWidth - width)
    return members.map((p, i) => ({ ...p, x: start + i * gap }))
  })
}

// Places site labels above their markers, moving a label up a line at a time while
// it overlaps one already placed, so all nine stay readable in clusters.
function placeLabels(points, plotWidth) {
  const placed = []
  return points.map((p) => {
    const text = `${p.site} · ${fmtM(p.elevation_m)}`
    const w = text.length * LABEL_CHAR_W
    const x = Math.min(Math.max(p.x, w / 2 + 2), plotWidth - w / 2 - 2)
    let y = p.y - PROFILE.markerRadius - 5
    const overlaps = () => placed.some((b) =>
      x - w / 2 < b.x2 && x + w / 2 > b.x1 && y - LABEL_FONT < b.y2 && y + 2 > b.y1)
    while (overlaps()) y -= LABEL_LINE
    placed.push({ x1: x - w / 2 - 3, x2: x + w / 2 + 3, y1: y - LABEL_FONT, y2: y + 2 })
    return { ...p, text, labelX: x, labelY: y, moved: p.y - PROFILE.markerRadius - 5 - y > 1 }
  })
}

// Side view of the slope along one line from the coast to Mauna Loa's summit
// (profile.json), drawn with D3 scales and shapes, rendered by React.
// hoveredSite / onHoverSite: shared with the map so hovering either highlights both.
// focusedSite / onSelectSite: the Step 2.5 site focus; selecting here acts like a map click.
export default function ProfileView({
  profile, hoveredSite, focusedSite, onHoverSite, onSelectSite, showLine, onToggleLine,
}) {
  const [open, setOpen] = useState(() => window.innerWidth >= PROFILE.collapsedBelow)
  const bodyRef = useRef(null)
  const [width, setWidth] = useState(0)
  const [lineInfoOpen, setLineInfoOpen] = useState(false) // the "what is this line" tooltip

  // Redraw at the strip's current width whenever it changes (window resize or the
  // side panel being resized, opened or closed).
  useLayoutEffect(() => {
    const el = bodyRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // Tell the map how much of the bottom the strip covers, so its bottom controls
  // and camera padding stay clear of it. Collapsed, only the toggle tab remains,
  // so the controls sit just above the tab instead of covering it.
  useEffect(() => {
    const root = document.documentElement.style
    root.setProperty('--profile-offset', `${open ? PROFILE.height : PROFILE.tabHeight}px`)
    return () => root.removeProperty('--profile-offset')
  }, [open])

  const chart = useMemo(() => {
    if (!profile || width <= 0) return null
    const { margin, yTickStep } = PROFILE
    const plotW = width - margin.left - margin.right
    const plotH = PROFILE.height - PROFILE.headerHeight - margin.top - margin.bottom
    const totalKm = profile.summit.distance_km
    const topM = max([...profile.profile.map((d) => d.elevation_m), ...profile.sites.map((s) => s.elevation_m)])

    // Fill the plot: x runs from the coast to the summit, y from sea level to the
    // highest point. (So the vertical exaggeration depends on the strip's width.)
    const x = scaleLinear().domain([0, totalKm]).range([0, plotW])
    const y = scaleLinear().domain([0, topM]).range([plotH, 0])
    const visibleTopM = topM

    const ground = area()
      .x((d) => x(d.distance_km))
      .y0(plotH)
      .y1((d) => y(Math.max(0, d.elevation_m)))(profile.profile)

    const sites = [...profile.sites]
      .sort((a, b) => a.distance_km - b.distance_km)
      .map((s) => ({ ...s, x: x(s.distance_km), y: y(s.elevation_m), band: bandFor(s.elevation_m) }))

    return {
      plotW, plotH, x, y, ground,
      ticks: range(0, visibleTopM + 1, yTickStep),
      bands: RISK_BANDS.map((b) => ({
        ...b, y1: Math.max(0, y(Math.min(b.to, visibleTopM))), y2: y(b.from),
      })),
      sites: placeLabels(spreadMarkers(sites, plotW), plotW),
      summit: { x: x(totalKm), y: y(Math.max(0, profile.summit.elevation_m)) },
      key: keyLayout(),
    }
  }, [profile, width])

  const { margin } = PROFILE

  return (
    <section
      className={`profile-view ${open ? 'is-open' : 'is-closed'}`}
      style={{ height: PROFILE.height }}
      aria-label="Study Site Elevations"
    >
      {/* Toggle tab on the strip's top edge, styled like the side panel's toggle, so it
          stays visible when the strip slides away. */}
      <button
        type="button"
        className="profile-view__toggle"
        aria-expanded={open}
        aria-controls="profile-view-body"
        title={open ? 'Hide Study Site Elevations' : 'Show Study Site Elevations'}
        onClick={() => setOpen((o) => !o)}
      >
        <span aria-hidden="true">{open ? '▾' : '▴'}</span>
        <span className="visually-hidden">{open ? 'Close Study Site Elevations' : 'Open Study Site Elevations'}</span>
      </button>

      <div id="profile-view-body" className="profile-view__body" inert={!open}>
        {/* Title bar above the chart: title, map-line checkbox, and an info button
            explaining the line. */}
        <div className="profile-view__header" style={{ height: PROFILE.headerHeight }}>
          <h2 className="profile-view__title">Study Site Elevations</h2>
          <label className="profile-view__line-toggle">
            <input type="checkbox" checked={showLine} onChange={(e) => onToggleLine(e.target.checked)} />
            Show line on map
          </label>
          <span
            className="profile-view__info"
            onMouseEnter={() => setLineInfoOpen(true)}
            onMouseLeave={() => setLineInfoOpen(false)}
          >
            <button
              type="button"
              className="profile-view__info-button"
              aria-label="What is the line on the map?"
              aria-describedby="profile-line-info"
              onFocus={() => setLineInfoOpen(true)}
              onBlur={() => setLineInfoOpen(false)}
              onKeyDown={(e) => { if (e.key === 'Escape') setLineInfoOpen(false) }}
            >
              i
            </button>
            <span
              id="profile-line-info"
              role="tooltip"
              className={`profile-view__tooltip${lineInfoOpen ? ' is-open' : ''}`}
            >
              The dashed line on the map is where this side view is taken: a line from the
              coast, up through the study sites, to the summit of Mauna Loa. The chart shows
              the ground along that line. Each site is placed on it at its own elevation;
              some sites are several kilometres to either side of the line.
            </span>
          </span>
        </div>
        <div ref={bodyRef} className="profile-view__chart">
        {chart && (
          <svg width={width} height={PROFILE.height - PROFILE.headerHeight} className="profile-view__svg">
            <g transform={`translate(${margin.left},${margin.top})`}>
              {/* Risk bands behind everything, low (warm) to high (cool). */}
              {chart.bands.map((b) => b.y2 > b.y1 && (
                <rect key={b.id} x={0} y={b.y1} width={chart.plotW} height={b.y2 - b.y1} fill={b.fill} />
              ))}

              {/* Elevation axis, a tick every 500 m. */}
              {chart.ticks.map((t) => (
                <g key={t} transform={`translate(0,${chart.y(t)})`} className="profile-view__tick">
                  <line x1={0} x2={chart.plotW} />
                  <text x={-6} dy="0.32em" textAnchor="end">{t.toLocaleString('en-US')}</text>
                </g>
              ))}
              <text className="profile-view__axis-title" transform={`translate(${-40},${chart.plotH / 2}) rotate(-90)`}
                textAnchor="middle">Elevation (m)</text>

              <path d={chart.ground} fill={PROFILE.groundFill} stroke={PROFILE.groundStroke} strokeWidth={1} />

              <text className="profile-view__end-label" x={2} y={chart.plotH + 15}>Coast</text>
              <text className="profile-view__end-label" x={chart.summit.x} y={chart.summit.y - 7} textAnchor="end">
                Mauna Loa Summit
              </text>

              {/* Risk band key, boxed, in the empty sky at the upper left. */}
              <g className="profile-view__key" transform="translate(8,6)">
                <rect className="profile-view__key-box" width={chart.key.width} height={42} rx={4} />
                <text className="profile-view__key-title" x={KEY_PAD} y={15}>{RISK_KEY_TITLE}</text>
                {chart.key.items.map((b) => (
                  <g key={b.id} transform={`translate(${b.x},24)`}>
                    <rect width={11} height={11} rx={2} fill={b.fill} stroke={b.marker} />
                    <text x={15} y={9.5}>{b.label}</text>
                  </g>
                ))}
              </g>

              {/* Sites: marker at distance along the line and true elevation. While one
                  is hovered (here or on the map), the others dim. */}
              <g className={`profile-view__sites${hoveredSite ? ' has-hover' : ''}`}>
              {chart.sites.map((s) => {
                const highlighted = s.site === hoveredSite || s.site === focusedSite
                return (
                  <g
                    key={s.site}
                    className={`profile-view__site${highlighted ? ' is-highlighted' : ''}${s.site === focusedSite ? ' is-focused' : ''}${s.site === hoveredSite ? ' is-hovered' : ''}`}
                    tabIndex={open ? 0 : -1}
                    role="button"
                    aria-label={`${s.site}, ${fmtM(s.elevation_m)}, ${s.band.label.toLowerCase()} band. Fly to site.`}
                    onMouseEnter={() => onHoverSite(s.site)}
                    onMouseLeave={() => onHoverSite(null)}
                    onFocus={() => onHoverSite(s.site)}
                    onBlur={() => onHoverSite(null)}
                    onClick={() => onSelectSite(s.site)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onSelectSite(s.site)
                      }
                    }}
                  >
                    {s.moved && (
                      <line className="profile-view__leader" x1={s.x} y1={s.y - PROFILE.markerRadius}
                        x2={s.labelX} y2={s.labelY + 2} />
                    )}
                    <circle
                      cx={s.x}
                      cy={s.y}
                      r={highlighted ? PROFILE.markerRadiusHighlighted : PROFILE.markerRadius}
                      fill={s.band.marker}
                    />
                    <text x={s.labelX} y={s.labelY} textAnchor="middle">{s.text}</text>
                  </g>
                )
              })}
              </g>
            </g>
          </svg>
        )}
        </div>
      </div>
    </section>
  )
}
