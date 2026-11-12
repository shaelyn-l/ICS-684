// Top bar tabs (Step 2.7). Each tab opens its page in the info overlay.
// To add a tab, add an entry here with its content component.
import StationExplainer from '../content/stationExplainer.jsx'

export const TOP_BAR_TITLE = 'Hawaiʻi Island Avian Malaria'

export const TABS = [
  { id: 'station-data', label: 'About the station data', Content: StationExplainer },
]
