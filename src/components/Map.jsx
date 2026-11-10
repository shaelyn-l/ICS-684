import { useEffect, useRef, useState } from 'react'
import {
  LngLatBounds, Map as MapLibreMap, NavigationControl, Popup, setWorkerUrl,
} from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  BASEMAP_STYLE, DRAPE_BEFORE_LAYER, ELEVATION_TINT, HILLSHADE, INITIAL_VIEW, MAX_PITCH,
  SITE_FOCUS, SITE_MARKER, SKY, START_CAMERA, STATION_MARKER, STATIONS_URL, TERRAIN,
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

// Fits the starting view to the sites and returns it, so Overview can return to
// exactly this camera.
function fitToSites(map, sites) {
  const bounds = new LngLatBounds()
  sites.features.forEach((f) => bounds.extend(f.geometry.coordinates))
  map.fitBounds(bounds, { ...START_CAMERA, duration: 0 })
  return { center: map.getCenter(), zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing() }
}

// Sites and stations are data-driven layers (not HTML markers) so later steps can
// restyle and animate them. Added without a beforeId, so they sit above the basemap.
function addSitesAndStations(map, sites, stations) {
  map.addSource('stations', { type: 'geojson', data: stations })
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
      'circle-color': SITE_MARKER.color,
      // Same size at any distance from the camera, so size can encode data later.
      'circle-pitch-scale': 'viewport',
      ...sitePaint(null),
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

  map.on('mouseenter', 'sites', () => { map.getCanvas().style.cursor = 'pointer' })
  map.on('mouseleave', 'sites', () => { map.getCanvas().style.cursor = '' })
}

// Site marker paint for the focused site (or none): focused site larger with a
// gold outline, other sites dimmed.
function sitePaint(focused) {
  // (focused site's value, other sites' value, value when no site is focused)
  const pick = (yes, no, none) => (focused ? ['case', ['==', ['get', 'site'], focused], yes, no] : none)
  const { selected, dimmedOpacity } = SITE_MARKER
  return {
    'circle-radius': pick(selected.radius, SITE_MARKER.radius, SITE_MARKER.radius),
    'circle-stroke-color': pick(selected.strokeColor, SITE_MARKER.strokeColor, SITE_MARKER.strokeColor),
    'circle-stroke-width': pick(selected.strokeWidth, SITE_MARKER.strokeWidth, SITE_MARKER.strokeWidth),
    'circle-opacity': pick(1, dimmedOpacity, 1),
    'circle-stroke-opacity': pick(1, dimmedOpacity, 1),
  }
}

function applyFocusStyle(map, focused) {
  if (!map.getLayer('sites')) return
  for (const [prop, value] of Object.entries(sitePaint(focused))) map.setPaintProperty('sites', prop, value)
  map.setPaintProperty('site-labels', 'text-opacity',
    focused ? ['case', ['==', ['get', 'site'], focused], 1, SITE_MARKER.dimmedOpacity] : 1)
}

// Camera for a focused site: fitted to its stations, clear of the side panel.
function siteCamera(map, site, stations) {
  const bounds = new LngLatBounds()
  stations.features.filter((f) => f.properties.site === site)
    .forEach((f) => bounds.extend(f.geometry.coordinates))
  const panel = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--panel-offset')) || 0
  const { padding, pitch, bearing } = SITE_FOCUS
  const fitted = map.cameraForBounds(bounds, {
    padding: { ...padding, right: padding.right + panel }, pitch, bearing,
  })
  return { ...fitted, pitch, bearing, ...SITE_FOCUS.overrides[site] }
}

const prefersReducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

function moveCamera(map, camera) {
  if (prefersReducedMotion()) map.jumpTo(camera)
  else map.flyTo({ ...camera, duration: SITE_FOCUS.duration, essential: false })
}

// Home button shown under the navigation controls; returns to the overview.
class HomeControl {
  constructor(onHome) { this.onHome = onHome }

  onAdd() {
    this.container = document.createElement('div')
    this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group'
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'map-home-button'
    button.title = 'Back to overview'
    button.setAttribute('aria-label', 'Back to overview')
    button.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">'
      + '<path d="M12 3 2 12h3v8h5v-5h4v5h5v-8h3z" fill="currentColor"/></svg>'
    button.addEventListener('click', () => this.onHome())
    this.container.appendChild(button)
    return this.container
  }

  onRemove() { this.container.remove() }
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

// focus: { site, id } — a request to focus a site (site = null for the overview).
// A new id means a new request, so re-clicking the same site flies there again.
export default function Map({ sites, focus, onFocusSite }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const startCameraRef = useRef(null)
  const stationsRef = useRef(null)
  const popupRef = useRef(null) // { popup, site }
  const onFocusRef = useRef(onFocusSite)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [ready, setReady] = useState(false)

  useEffect(() => { onFocusRef.current = onFocusSite }, [onFocusSite])

  useEffect(() => {
    // MapLibre tracks window resizes itself (trackResize defaults to true).
    const map = new MapLibreMap({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: INITIAL_VIEW.center,
      zoom: INITIAL_VIEW.zoom,
      maxPitch: MAX_PITCH,
    })
    mapRef.current = map
    map.addControl(new NavigationControl({ visualizePitch: true }), 'top-right')
    map.addControl(new HomeControl(() => onFocusRef.current(null)), 'top-right')
    map.on('load', () => {
      addTerrain(map)
      setMapLoaded(true)
    })
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Once the basemap and the site data are both in, fit the starting view and add
  // the markers. Sites come from App (loaded once); stations are loaded here.
  useEffect(() => {
    if (!mapLoaded || !sites) return
    const map = mapRef.current
    let cancelled = false
    fetch(STATIONS_URL).then((r) => r.json()).then((stations) => {
      if (cancelled || map.getSource('sites')) return
      stationsRef.current = stations
      startCameraRef.current = fitToSites(map, sites)
      addSitesAndStations(map, sites, stations)
      map.on('click', 'sites', (e) => {
        const site = e.features[0].properties.site
        onFocusRef.current(site)
        popupRef.current?.popup.remove()
        const popup = new Popup({ maxWidth: '280px' })
          .setLngLat(e.features[0].geometry.coordinates)
          .setDOMContent(sitePopup(e.features[0].properties))
          .addTo(map)
        popupRef.current = { popup, site }
      })
      setReady(true)
    })
    return () => { cancelled = true }
  }, [mapLoaded, sites])

  // Each focus request: restyle the markers, close any popup for another site,
  // and move the camera to the site or back to the starting view.
  useEffect(() => {
    if (!ready) return
    const map = mapRef.current
    applyFocusStyle(map, focus.site)
    if (popupRef.current && popupRef.current.site !== focus.site) {
      popupRef.current.popup.remove()
      popupRef.current = null
    }
    if (focus.id === 0) return // initial state: stay on the starting view
    moveCamera(map, focus.site ? siteCamera(map, focus.site, stationsRef.current) : startCameraRef.current)
  }, [focus, ready])

  return <div ref={containerRef} className="map" />
}
