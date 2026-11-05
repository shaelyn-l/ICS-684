import { useEffect, useRef } from 'react'
import {
  LngLatBounds, Map as MapLibreMap, NavigationControl, Popup, setWorkerUrl,
} from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  BASEMAP_STYLE, DRAPE_BEFORE_LAYER, ELEVATION_TINT, HILLSHADE, INITIAL_VIEW, MAX_PITCH,
  SITE_MARKER, SITES_URL, SKY, START_CAMERA, STATION_MARKER, STATIONS_URL, TERRAIN,
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

function fitToSites(map, sites) {
  const bounds = new LngLatBounds()
  sites.features.forEach((f) => bounds.extend(f.geometry.coordinates))
  map.fitBounds(bounds, { ...START_CAMERA, duration: 0 })
}

// Sites and stations are data-driven layers (not HTML markers) so later steps can
// restyle and animate them. Added without a beforeId, so they sit above the basemap.
function addSitesAndStations(map, sites) {
  map.addSource('stations', { type: 'geojson', data: STATIONS_URL })
  map.addLayer({
    id: 'stations',
    type: 'circle',
    source: 'stations',
    minzoom: STATION_MARKER.minZoom,
    paint: {
      'circle-radius': STATION_MARKER.radius,
      'circle-color': STATION_MARKER.color,
      'circle-opacity': STATION_MARKER.opacity,
      'circle-stroke-color': STATION_MARKER.strokeColor,
      'circle-stroke-width': STATION_MARKER.strokeWidth,
      'circle-pitch-scale': 'viewport',
    },
  })

  map.addSource('sites', { type: 'geojson', data: sites })
  map.addLayer({
    id: 'sites',
    type: 'circle',
    source: 'sites',
    paint: {
      'circle-radius': SITE_MARKER.radius,
      'circle-color': SITE_MARKER.color,
      'circle-stroke-color': SITE_MARKER.strokeColor,
      'circle-stroke-width': SITE_MARKER.strokeWidth,
      // Same size at any distance from the camera, so size can encode data later.
      'circle-pitch-scale': 'viewport',
    },
  })
  // Label side per site: text anchored on the right sits to the left of the circle.
  const labelAnchor = ['match', ['get', 'site'],
    ...Object.entries(SITE_MARKER.labelSide).flatMap(([site, side]) => [site, side === 'left' ? 'right' : 'left']),
    'left']
  const labelOffset = ['match', ['get', 'site'],
    ...Object.entries(SITE_MARKER.labelSide).flatMap(([site, side]) => [site, ['literal', side === 'left' ? [-1, 0] : [1, 0]]]),
    ['literal', [1, 0]]]
  map.addLayer({
    id: 'site-labels',
    type: 'symbol',
    source: 'sites',
    layout: {
      'text-field': ['get', 'site'],
      'text-font': SITE_MARKER.labelFont,
      'text-size': SITE_MARKER.labelSize,
      'text-anchor': labelAnchor,
      'text-offset': labelOffset,
      'text-allow-overlap': true, // always show all nine site codes
    },
    paint: {
      'text-color': SITE_MARKER.labelColor,
      'text-halo-color': SITE_MARKER.labelHaloColor,
      'text-halo-width': SITE_MARKER.labelHaloWidth,
    },
  })

  map.on('click', 'sites', (e) => {
    const feature = e.features[0]
    new Popup({ maxWidth: '280px' })
      .setLngLat(feature.geometry.coordinates)
      .setDOMContent(sitePopup(feature.properties))
      .addTo(map)
  })
  map.on('mouseenter', 'sites', () => { map.getCanvas().style.cursor = 'pointer' })
  map.on('mouseleave', 'sites', () => { map.getCanvas().style.cursor = '' })
}

const number = (m) => Math.round(m).toLocaleString('en-US')
const metres = (m) => `${number(m)} m`

// Popup content built as DOM nodes (site names come from data, so no innerHTML).
function sitePopup(p) {
  const root = document.createElement('div')
  const lines = [
    ['strong', p.site],
    ['div', p.site_name ?? 'Site name not available'],
    ['div', `${metres(p.elevation_m)} (${number(p.elevation_min_m)}–${metres(p.elevation_max_m)})`],
    ['div', `${p.n_stations} sampling points (9 stations × 5 transects)`],
  ]
  for (const [tag, text] of lines) {
    const el = document.createElement(tag)
    el.textContent = text
    root.appendChild(el)
  }
  return root
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
    let removed = false
    map.on('load', async () => {
      addTerrain(map)
      // Load sites once: used for the starting camera and the site markers.
      const sites = await fetch(SITES_URL).then((r) => r.json())
      if (removed) return
      fitToSites(map, sites)
      addSitesAndStations(map, sites)
    })

    return () => {
      removed = true
      map.remove()
    }
  }, [])

  return <div ref={containerRef} className="map" />
}
