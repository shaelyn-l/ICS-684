import { useCallback, useEffect, useState } from 'react'
import Map from './components/Map.jsx'
import SidePanel from './components/SidePanel.jsx'
import SitePicker from './components/SitePicker.jsx'
import { SITES_URL } from './config/map.js'

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

  // Escape returns to the overview, like the Overview button and home control.
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') focusSite(null) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [focusSite])

  return (
    <>
      <Map sites={sites} focus={focus} onFocusSite={focusSite} />
      <SidePanel
        sitesContent={<SitePicker sites={sites} focusedSite={focus.site} onFocusSite={focusSite} />}
      />
    </>
  )
}
