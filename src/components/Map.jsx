import { useEffect, useRef } from 'react'
import { Map as MapLibreMap, NavigationControl, setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { BASEMAP_STYLE, INITIAL_VIEW } from '../config/map.js'

// MapLibre 6 finds its worker relative to its own file, which Vite moves when
// bundling. Point it at the worker explicitly so dev and build both work.
setWorkerUrl(workerUrl)

export default function Map() {
  const containerRef = useRef(null)

  useEffect(() => {
    // MapLibre tracks window resizes itself (trackResize defaults to true).
    const map = new MapLibreMap({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: INITIAL_VIEW.center,
      zoom: INITIAL_VIEW.zoom,
    })
    map.addControl(new NavigationControl(), 'top-right')

    return () => map.remove()
  }, [])

  return <div ref={containerRef} className="map" />
}
