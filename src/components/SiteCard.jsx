import { PERIOD_HEADINGS } from '../config/periods.js'
import { SITE_CARD } from '../config/map.js'
import { SITE_SUMMARY_METRICS, metres, number, siteMetricValue } from './siteSummary.js'
import './SiteCard.css'

// Summary of the focused site, shown at the top-left of the map while zoomed in to
// its stations (the site's own circle is hidden then, so it doesn't cover them).
// Same content as the overview hover popup. The site values follow the season
// buttons; the station dots stay all seasons.
// site: the site's sites.geojson properties. summary: its site_summary.json row for
// the selected period. onBack: return to the overview.
export default function SiteCard({ site: p, summary, period, onBack }) {
  return (
    <section
      className="site-card"
      style={{ width: SITE_CARD.width, top: SITE_CARD.inset, left: SITE_CARD.inset }}
      aria-label={`${p.site} site summary`}
    >
      <div className="site-card__title">
        <strong>{p.site}</strong> · {p.site_name ?? 'Site name not available'}
      </div>
      <div className="site-card__meta">
        {metres(p.elevation_m)} ({number(p.elevation_min_m)}–{metres(p.elevation_max_m)}) ·{' '}
        {p.n_stations} sampling points
      </div>

      <div className="site-card__period">Site as a whole · {PERIOD_HEADINGS[period]}</div>
      <dl className="site-card__data">
        {SITE_SUMMARY_METRICS.map((metric) => (
          <div key={metric.key}>
            <dt>{metric.label}</dt>
            <dd>{summary ? siteMetricValue(p.site, summary, metric) : 'No data'}</dd>
          </div>
        ))}
      </dl>
      <p className="site-card__note">The station dots show each station across all seasons.</p>

      <button type="button" className="site-card__back" onClick={onBack}>
        ← Back to overview
      </button>
    </section>
  )
}
