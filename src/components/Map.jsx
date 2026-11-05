import { useEffect, useRef } from 'react'
import { LngLatBounds, Map as MapLibreMap, NavigationControl, setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  BASEMAP_STYLE, DRAPE_BEFORE_LAYER, ELEVATION_TINT, HILLSHADE, INITIAL_VIEW, MAX_PITCH,
  SITES_URL, SKY, START_CAMERA, TERRAIN,
} from '../config/map.js'

// MapLibre 6 finds its worker relative to its own file, which Vite moves when
// bundling. Point it at the worker explicitly so dev and build both work.
setWorkerUrl(workerUrl)

const demSource = () => ({
  type: 'raster-dem',
  tiles: TERRAIN.tiles,
  encoding: TERRAIN.encoding,
  tileSize: TERRAIN.tileSize,
  maxzoom: TERRAIN.maxzoom,
})

// Insert draped layers before DRAPE_BEFORE_LAYER, or before the first label
// layer if the basemap style no longer has it.
function drapeBeforeId(map) {
  if (map.getLayer(DRAPE_BEFORE_LAYER)) return DRAPE_BEFORE_LAYER
  return map.getStyle().layers.find((l) => l.type === 'symbol')?.id
}

function addTerrain(map) {
  // Separate sources for terrain and hillshade, as MapLibre recommends; the
  // browser caches the shared tiles.
  map.addSource('terrain-dem', { ...demSource(), attribution: TERRAIN.attribution })
  map.addSource('hillshade-dem', demSource())
  const beforeId = drapeBeforeId(map)
  map.addLayer({
    id: 'elevation-tint',
    type: 'color-relief',
    source: 'hillshade-dem',
    paint: {
      'color-relief-opacity': ELEVATION_TINT.opacity,
      'color-relief-color': ['interpolate', ['linear'], ['elevation'], ...ELEVATION_TINT.stops.flat()],
    },
  }, beforeId)
  map.addLayer({
    id: 'hillshade',
    type: 'hillshade',
    source: 'hillshade-dem',
    paint: {
      'hillshade-exaggeration': HILLSHADE.exaggeration,
      'hillshade-shadow-color': HILLSHADE.shadowColor,
      'hillshade-highlight-color': HILLSHADE.highlightColor,
    },
  }, beforeId)
  map.setTerrain({ source: 'terrain-dem', exaggeration: TERRAIN.exaggeration })
  map.setSky(SKY)
}

async function fitToSites(map) {
  const sites = await fetch(SITES_URL).then((r) => r.json())
  const bounds = new LngLatBounds()
  sites.features.forEach((f) => bounds.extend(f.geometry.coordinates))
  map.fitBounds(bounds, { ...START_CAMERA, duration: 0 })
}

export default function Map() {
  const containerRef = useRef(null)

  useEffect(() => {
    // MapLibre tracks window resizes itself (trackResize defaults to true).
    const map = new MapLibreMap({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: INITIAL_VIEW.center,
      zoom: INITIAL_VIEW.zoom,
      maxPitch: MAX_PITCH,
    })
    map.addControl(new NavigationControl({ visualizePitch: true }), 'top-right')
    map.on('load', () => {
      addTerrain(map)
      fitToSites(map)
    })

    return () => map.remove()
  }, [])

  return <div ref={containerRef} className="map" />
}
