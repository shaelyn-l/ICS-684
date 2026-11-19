import { PERIOD_HEADINGS } from '../config/periods.js'
import SiteLegend from './SiteLegend.jsx'
import StationLegend from './StationLegend.jsx'
import './MapKey.css'

// The side panel's Key: only the key for what the map is showing right now.
// Zoomed in to a site with stations shown: the station color key (all seasons).
// Otherwise (overview, or stations hidden): the site circle key for the season.
export default function MapKey({ focusedSite, showStations, period, onExplainStations }) {
  const stationView = focusedSite && showStations
  return (
    <div className="map-key" aria-live="polite">
      <div className="map-key__heading">
        {stationView
          ? `${focusedSite} stations · all seasons`
          : `Site circles · ${PERIOD_HEADINGS[period]}`}
      </div>
      {stationView
        ? <StationLegend onExplain={onExplainStations} />
        : <SiteLegend />}
    </div>
  )
}
