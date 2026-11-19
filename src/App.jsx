import { useCallback, useEffect, useRef, useState } from 'react'
import Map from './components/Map.jsx'
import SidePanel from './components/SidePanel.jsx'
import SitePicker from './components/SitePicker.jsx'
import SeasonPicker from './components/SeasonPicker.jsx'
import StationLegend from './components/StationLegend.jsx'
import StationToggle from './components/StationToggle.jsx'
import TopBar from './components/TopBar.jsx'
import InfoOverlay from './components/InfoOverlay.jsx'
import SiteLegend from './components/SiteLegend.jsx'
import ProfileView from './components/ProfileView.jsx'
import { SITES_URL } from './config/map.js'
import { TABS } from './config/tabs.js'
import { DEFAULT_PERIOD } from './config/periods.js'
import { PROFILE_URL } from './config/profile.js'

export default function App() {
  // sites.geojson is loaded once and shared by the map and the site buttons.
  const [sites, setSites] = useState(null)
  useEffect(() => {
    fetch(SITES_URL).then((r) => r.json()).then(setSites)
  }, [])

  // profile.json (mountain profile): loaded once, shared by the profile strip and
  // the map (which can draw the profile line).
  const [profile, setProfile] = useState(null)
  useEffect(() => {
    fetch(PROFILE_URL).then((r) => r.json()).then(setProfile)
  }, [])

  // A focus request: { site, id }. site is null for the overview. Every request
  // gets a new id, so asking for the same site again still moves the camera.
  const [focus, setFocus] = useState({ site: null, id: 0 })
  const focusSite = useCallback((site) => setFocus((f) => ({ site, id: f.id + 1 })), [])

  // Site hovered on the map or in the mountain profile (highlighted in both), and
  // whether the profile line is drawn on the map.
  const [hoveredSite, setHoveredSite] = useState(null)
  const [showProfileLine, setShowProfileLine] = useState(true)

  // Selected season period (a site_summary.json period id, chosen with the season
  // buttons in the side panel's Sites section) and whether station dots are shown
  // (checkbox in the Stations section). Held here so the map and side panel share them.
  const [period, setPeriod] = useState(DEFAULT_PERIOD)
  const [showStations, setShowStations] = useState(true)

  // Top bar page open in the overlay (tab id or null), and the control that opened
  // it, so focus can go back there on close.
  const [activeTab, setActiveTab] = useState(null)
  const openerRef = useRef(null)
  const openTab = useCallback((id, opener) => {
    openerRef.current = opener ?? document.activeElement
    setActiveTab(id)
  }, [])
  const closeTab = useCallback(() => setActiveTab(null), [])
  const tab = TABS.find((t) => t.id === activeTab)

  // Escape returns to the overview, like the Overview button and home control,
  // except while the overlay is open: then Escape only closes the overlay.
  useEffect(() => {
    if (activeTab) return
    const onKey = (e) => { if (e.key === 'Escape') focusSite(null) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [focusSite, activeTab])

  return (
    <>
      <TopBar activeTab={activeTab} onOpenTab={openTab} />
      <div className="app-body">
        <Map
          sites={sites}
          focus={focus}
          onFocusSite={focusSite}
          hoverDisabled={!!activeTab}
          period={period}
          showStations={showStations}
          hoveredSite={hoveredSite}
          onHoverSite={setHoveredSite}
          profileLine={profile?.line}
          showProfileLine={showProfileLine}
        />
        <ProfileView
          profile={profile}
          hoveredSite={hoveredSite}
          focusedSite={focus.site}
          onHoverSite={setHoveredSite}
          onSelectSite={focusSite}
          showLine={showProfileLine}
          onToggleLine={setShowProfileLine}
        />
        <SidePanel
          sitesContent={
            <>
              <SitePicker sites={sites} focusedSite={focus.site} onFocusSite={focusSite} />
              <SeasonPicker period={period} onChangePeriod={setPeriod} />
              <SiteLegend period={period} />
            </>
          }
          // Stations section: the show/hide checkbox is always there; the station
          // color key only appears for a focused site while stations are shown,
          // since station dots are only drawn then.
          stationsContent={
            <>
              <StationToggle checked={showStations} onChange={setShowStations} />
              {focus.site && showStations && (
                <StationLegend onExplain={(opener) => openTab('station-data', opener)} />
              )}
            </>
          }
        />
      </div>
      {tab && (
        <InfoOverlay title={tab.label} onClose={closeTab} returnFocusRef={openerRef}>
          <tab.Content />
        </InfoOverlay>
      )}
    </>
  )
}
