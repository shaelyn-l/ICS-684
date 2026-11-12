import { useLayoutEffect, useRef, useState } from 'react'
import './StationTooltip.css'

const OFFSET = 14 // px from the cursor

const fmt = (n, digits) => n.toLocaleString('en-US', { maximumFractionDigits: digits })
const plural = (n, word) => `${fmt(n, 0)} ${word}${n === 1 ? '' : 's'}`

// One infection test as its own line. The two tests don't nest (a mosquito can be
// salivary-positive without showing malaria in the gut), so each gets its own count.
function infectionLine(label, infected, n) {
  if (!n) return `${label}: not tested`
  return `${label}: ${fmt(infected, 0)} of ${plural(n, 'mosquito')}`.replace('mosquitos', 'mosquitoes')
}

// Station values are all-seasons totals (station_summary.json); site averages are
// the site's `all` values from site_summary.json, never a seasonal one.
export default function StationTooltip({ station: s, siteAverage: avg, x, y, note }) {
  const ref = useRef(null)
  const [pos, setPos] = useState({ left: x + OFFSET, top: y + OFFSET })

  // Keep the tooltip on screen: flip to the other side of the cursor near an edge.
  useLayoutEffect(() => {
    const { width, height } = ref.current.getBoundingClientRect()
    const left = x + OFFSET + width > window.innerWidth ? x - OFFSET - width : x + OFFSET
    const top = y + OFFSET + height > window.innerHeight ? y - OFFSET - height : y + OFFSET
    setPos({ left: Math.max(4, left), top: Math.max(4, top) })
  }, [x, y])

  const midgutN = s.mosq_midgut_n ?? 0
  const salivaryN = s.mosq_salivary_n ?? 0
  const countsN = s.bird_counts_n ?? 0

  return (
    <div ref={ref} className="station-tooltip" style={pos} role="tooltip">
      <div className="station-tooltip__heading">All seasons combined (May 2002 – Oct 2004)</div>
      <div className="station-tooltip__title">
        {s.site} · Station {s.station}, transect {s.transect} · {fmt(s.elevation_m, 0)} m
      </div>

      <dl className="station-tooltip__rows">
        <dt><i>Culex</i> per trap night</dt>
        <dd>
          {s.culex_per_trap_night == null ? 'no trap data'
            : `${fmt(s.culex_per_trap_night, 3)} (${plural(s.trap_nights, 'trap night')})`}
          {/* Pooled site rate: all Culex caught ÷ all trap nights. Every site had CO2
              traps at all 45 stations (checked in station_summary.json). A trap night is
              one trap for one night, so same-night traps at different stations add up. */}
          {avg && (
            <span className="station-tooltip__avg">
              Site-wide, all seasons: {fmt(avg.mosquito_per_trap_night, 3)} per trap night
              ({plural(avg.mosquito_trap_nights, 'trap night')} across 45 stations)
            </span>
          )}
        </dd>

        <dt>Mosquito infection</dt>
        <dd>
          {midgutN === 0 && salivaryN === 0 ? 'No mosquitoes tested here.' : (
            <>
              <span>{infectionLine('Malaria in the gut', s.mosq_midgut_infected, midgutN)}</span>
              <span>{infectionLine('Malaria in the salivary glands (can pass it to birds)',
                s.mosq_salivary_infected, salivaryN)}</span>
            </>
          )}
        </dd>

        {countsN > 0 && (
          <>
            <dt>Honeycreepers per count</dt>
            <dd>
              {fmt(s.honeycreepers_per_count, 2)} ({plural(countsN, 'count')})
              {avg && (
                <span className="station-tooltip__avg">
                  Site average, all seasons: {fmt(avg.honeycreepers_per_count, 2)} ({plural(avg.bird_counts_n, 'count')})
                </span>
              )}
            </dd>
            <dt>Non-native birds per count</dt>
            <dd>
              {fmt(s.nonnative_birds_per_count, 2)} ({plural(countsN, 'count')})
              {avg && (
                <span className="station-tooltip__avg">
                  Site average, all seasons: {fmt(avg.nonnative_birds_per_count, 2)} ({plural(avg.bird_counts_n, 'count')})
                </span>
              )}
            </dd>
          </>
        )}
      </dl>

      {note && <div className="station-tooltip__note">{note}</div>}
    </div>
  )
}
