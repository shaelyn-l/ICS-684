import { useCallback, useEffect, useRef, useState } from 'react'
import Map from './components/Map.jsx'
import SidePanel from './components/SidePanel.jsx'
import SitePicker from './components/SitePicker.jsx'
import SeasonPicker from './components/SeasonPicker.jsx'
import TopBar from './components/TopBar.jsx'
import InfoOverlay from './components/InfoOverlay.jsx'
import { SITES_URL } from './config/map.js'
import { TABS } from './config/tabs.js'
import { DEFAULT_PERIOD } from './config/periods.js'

export default function App() {
  // sites.geojson is loaded once and shared by the map and the site buttons.
  const [sites, setSites] = useState(null)
  useEffect(() => {
    fetch(SITES_URL).then((r) => r.json()).then(setSites)
  }, [])

  // A focus request: { site, id }. site is null for the overview. Every request
  // gets a new id, so asking for the same site again still moves the camera.
  const [focus, setFocus] = useState({ site: null, id: 0 })
  const focusSite = useCallback((site) => setFocus((f) => ({ site, id: f.id + 1 })), [])

  // Period shown in the site popups (a site_summary.json period id), chosen in the
  // side panel's Layers section.
  const [period, setPeriod] = useState(DEFAULT_PERIOD)

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
        />
        <SidePanel
          sitesContent={
            <SitePicker
              sites={sites}
              focusedSite={focus.site}
              onFocusSite={focusSite}
              onExplainStations={(opener) => openTab('station-data', opener)}
            />
          }
          layersContent={<SeasonPicker period={period} onChangePeriod={setPeriod} />}
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
