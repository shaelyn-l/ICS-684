import { useEffect, useRef, useState } from 'react'
import {
  LngLatBounds, Map as MapLibreMap, NavigationControl, Popup, setWorkerUrl,
} from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  BASEMAP_STYLE, CULEX_SCALE, DRAPE_BEFORE_LAYER, ELEVATION_TINT, HILLSHADE, INITIAL_VIEW, MAX_PITCH,
  SITE_FOCUS, SITE_MARKER, SITE_SUMMARY_URL, SKY, START_CAMERA, STATION_MARKER, STATION_SUMMARY_URL,
  STATIONS_URL, TERRAIN, siteRadius,
} from '../config/map.js'
import { PERIOD_LABELS } from '../config/periods.js'
import StationTooltip from './StationTooltip.jsx'

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

// Site features for one period (Step 4.1): each site's honeycreepers per count and
// Culex per trap night from site_summary.json, plus the circle radius. A site with
// either value missing has has_data = false and is drawn as a grey outline at the
// minimum radius, never as a zero.
function siteFeatures(sites, periodSummary) {
  return {
    ...sites,
    features: sites.features.map((f) => {
      const row = periodSummary?.[f.properties.site]
      const honeycreepers = row?.honeycreepers_per_count ?? null
      const culex = row?.mosquito_per_trap_night ?? null
      const hasData = honeycreepers != null && culex != null
      return {
        ...f,
        properties: {
          ...f.properties,
          honeycreepers_per_count: honeycreepers,
          mosquito_per_trap_night: culex,
          has_data: hasData,
          marker_radius: hasData ? siteRadius(honeycreepers) : SITE_MARKER.size.minRadius,
        },
      }
    }),
  }
}

// Site labels sit beside each circle, so their offset depends on the circle's size.
// Text anchored on the right sits to the left of the circle.
function siteLabelLayout(data) {
  const { labelSide, labelSize, labelGap, strokeWidth } = SITE_MARKER
  const isLeft = (site) => labelSide[site] === 'left'
  return {
    'text-anchor': ['match', ['get', 'site'],
      ...Object.keys(labelSide).flatMap((site) => [site, isLeft(site) ? 'right' : 'left']),
      'left'],
    // text-offset is in ems of the label's font size.
    'text-offset': ['match', ['get', 'site'],
      ...data.features.flatMap(({ properties: p }) => {
        const em = (p.marker_radius + strokeWidth + labelGap) / labelSize
        return [p.site, ['literal', [isLeft(p.site) ? -em : em, 0]]]
      }),
      ['literal', [1, 0]]],
  }
}

// Sites and stations are data-driven layers (not HTML markers) so later steps can
// restyle and animate them. Added without a beforeId, so they sit above the basemap.
// `sites` here is the output of siteFeatures for the selected period.
function addSitesAndStations(map, sites, stations) {
  // generateId gives each station a feature id, used for the hover highlight.
  map.addSource('stations', { type: 'geojson', data: stations, generateId: true })
  map.addLayer({
    id: 'stations',
    type: 'circle',
    source: 'stations',
    minzoom: STATION_MARKER.minZoom,
    paint: {
      'circle-opacity': STATION_MARKER.opacity,
      'circle-pitch-scale': 'viewport',
      ...stationPaint(null),
    },
  })
  // Invisible, larger circles on top of the dots: the hover target.
  map.addLayer({
    id: 'stations-hit',
    type: 'circle',
    source: 'stations',
    minzoom: STATION_MARKER.minZoom,
    paint: {
      'circle-radius': STATION_MARKER.hitRadius,
      'circle-opacity': 0,
      'circle-pitch-scale': 'viewport',
    },
  })

  map.addSource('sites', { type: 'geojson', data: sites })
  map.addLayer({
    id: 'sites',
    type: 'circle',
    source: 'sites',
    layout: {
      // Higher sort keys draw on top, so negating the radius puts smaller circles
      // above larger ones and close pairs (CJR/SOL, CRA/COO) don't hide each other.
      'circle-sort-key': ['-', ['get', 'marker_radius']],
    },
    paint: {
      // Radius in screen pixels, not tied to zoom; 'viewport' keeps it the same
      // at any distance from the camera, so size reads as data.
      'circle-radius': ['get', 'marker_radius'],
      'circle-color': ['case', ['get', 'has_data'],
        ['interpolate', ['linear'], ['get', 'mosquito_per_trap_night'], ...CULEX_SCALE.stops.flat()],
        'rgba(0, 0, 0, 0)'], // no data: outline only
      'circle-pitch-scale': 'viewport',
      ...sitePaint(null),
    },
  })
  map.addLayer({
    id: 'site-labels',
    type: 'symbol',
    source: 'sites',
    layout: {
      'text-field': ['get', 'site'],
      'text-font': SITE_MARKER.labelFont,
      'text-size': SITE_MARKER.labelSize,
      ...siteLabelLayout(sites),
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

// Adds each station's all-seasons totals (station_summary.json) to its point in
// stations.geojson, matched by site + station + transect.
function joinStationSummary(stationPoints, stationSummary) {
  const key = (p) => `${p.site}|${p.station}|${p.transect}`
  const byKey = new globalThis.Map(stationSummary.map((r) => [key(r), r]))
  return {
    ...stationPoints,
    features: stationPoints.features.map((f) => ({
      ...f,
      properties: { ...f.properties, ...byKey.get(key(f.properties)) },
    })),
  }
}

// Site marker paint for the focused site (or none): focused site gets a gold
// outline (keeping its data size), other sites dim. No-data sites have a grey outline.
function sitePaint(focused) {
  // (focused site's value, other sites' value, value when no site is focused)
  const pick = (yes, no, none) => (focused ? ['case', ['==', ['get', 'site'], focused], yes, no] : none)
  const { selected, dimmedOpacity } = SITE_MARKER
  const stroke = ['case', ['get', 'has_data'], SITE_MARKER.strokeColor, CULEX_SCALE.noDataColor]
  return {
    'circle-stroke-color': pick(selected.strokeColor, stroke, stroke),
    'circle-stroke-width': pick(selected.strokeWidth, SITE_MARKER.strokeWidth, SITE_MARKER.strokeWidth),
    'circle-opacity': pick(1, dimmedOpacity, 1),
    'circle-stroke-opacity': pick(1, dimmedOpacity, 1),
  }
}

// Station paint: the focused site's stations are larger and colored by Culex per
// trap night on the shared scale; all other stations keep the Step 2.3 grey style.
function stationPaint(focused) {
  const hovered = ['boolean', ['feature-state', 'hover'], false]
  const value = ['get', 'culex_per_trap_night']
  const culexColor = ['case',
    ['!=', ['typeof', value], 'number'], CULEX_SCALE.noDataColor,
    ['interpolate', ['linear'], value, ...CULEX_SCALE.stops.flat()]]
  const inFocus = ['==', ['get', 'site'], focused ?? '']
  return {
    'circle-stroke-color': ['case', hovered, STATION_MARKER.hoverStrokeColor,
      focused ? ['case', inFocus, STATION_MARKER.focusedStrokeColor, STATION_MARKER.strokeColor]
        : STATION_MARKER.strokeColor],
    'circle-color': focused ? ['case', inFocus, culexColor, STATION_MARKER.color] : STATION_MARKER.color,
    'circle-radius': focused ? ['case', inFocus, STATION_MARKER.focusedRadius, STATION_MARKER.radius]
      : STATION_MARKER.radius,
    'circle-stroke-width': ['case', hovered, STATION_MARKER.hoverStrokeWidth,
      focused ? ['case', inFocus, 1, STATION_MARKER.strokeWidth] : STATION_MARKER.strokeWidth],
  }
}

// Moves the station hover outline to feature `id` (or clears it with null).
function setStationHover(map, hoveredIdRef, id) {
  if (hoveredIdRef.current !== null) {
    map.setFeatureState({ source: 'stations', id: hoveredIdRef.current }, { hover: false })
  }
  hoveredIdRef.current = id
  if (id !== null) map.setFeatureState({ source: 'stations', id }, { hover: true })
}

function applyFocusStyle(map, focused) {
  if (!map.getLayer('sites')) return
  for (const [prop, value] of Object.entries(sitePaint(focused))) map.setPaintProperty('sites', prop, value)
  for (const [prop, value] of Object.entries(stationPaint(focused))) map.setPaintProperty('stations', prop, value)
  map.setPaintProperty('stations', 'circle-opacity', focused
    ? ['case', ['==', ['get', 'site'], focused], 1, STATION_MARKER.opacity] : STATION_MARKER.opacity)
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

const SITE_SUMMARY_METRICS = [
  { key: 'mosquito_per_trap_night', label: 'Mosquitoes per trap night', sample: 'mosquito_trap_nights', digits: 3 },
  { key: 'mosq_salivary_pct', label: 'Mosquito infection (salivary glands)', sample: 'mosq_salivary_n', digits: 1, unit: '%', percentage: true },
  { key: 'bird_prevalence_pct', label: 'Bird malaria prevalence', sample: 'bird_sampled_n', digits: 1, unit: '%', percentage: true },
  { key: 'honeycreepers_per_count', label: 'Honeycreepers per count', sample: 'bird_counts_n', digits: 2 },
]

function siteMetricValue(site, summary, metric) {
  const n = summary[metric.sample] ?? 0
  const value = summary[metric.key]
  if (value == null) {
    if (metric.key === 'mosq_salivary_pct' && ['SOL', 'CJR'].includes(site)) {
      return 'Too few mosquitoes to test.'
    }
    if (metric.percentage && n > 0) return `Too few samples (n=${n})`
    return 'No data'
  }
  return `${value.toLocaleString('en-US', { maximumFractionDigits: metric.digits })}${metric.unit ?? ''} (n=${n})`
}

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
function sitePopup(p, summary, period) {
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

  const periodHeading = document.createElement('div')
  periodHeading.className = 'site-popup__period'
  periodHeading.textContent = PERIOD_LABELS[period]
  root.appendChild(periodHeading)

  const data = document.createElement('dl')
  data.className = 'site-popup__data'
  for (const metric of SITE_SUMMARY_METRICS) {
    const label = document.createElement('dt')
    label.textContent = metric.label
    const value = document.createElement('dd')
    value.textContent = summary ? siteMetricValue(p.site, summary, metric) : 'No data'
    data.append(label, value)
  }
  root.appendChild(data)
  return root
}

// focus: { site, id } — a request to focus a site (site = null for the overview).
// A new id means a new request, so re-clicking the same site flies there again.
// stationNote: optional extra line for the station tooltip (Step 4.2 uses it).
// hoverDisabled: true while the info overlay is open; no station tooltip shows.
// period / onPeriodChange: the selected season period (held in App so the side
// panel legend can show it). showStations: false hides the station dots (Step 4.1).
export default function Map({
  sites, focus, onFocusSite, stationNote, hoverDisabled, period, onPeriodChange, showStations,
}) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const startCameraRef = useRef(null)
  const stationsRef = useRef(null)
  const popupRef = useRef(null) // { popup, site, properties }
  const siteSummariesRef = useRef({})
  const hoveredIdRef = useRef(null) // station feature with the hover outline
  const onFocusRef = useRef(onFocusSite)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [ready, setReady] = useState(false)
  const [hover, setHover] = useState(null) // { station, siteAverage, x, y } while hovering a station
  const periodRef = useRef(period)
  periodRef.current = period

  useEffect(() => { onFocusRef.current = onFocusSite }, [onFocusSite])

  // Opening the overlay drops any tooltip, so a stale one can't reappear on close.
  useEffect(() => { if (hoverDisabled) setHover(null) }, [hoverDisabled])

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
  // the markers. Sites come from App (loaded once); stations, their all-seasons
  // totals, and the site averages are loaded here.
  useEffect(() => {
    if (!mapLoaded || !sites) return
    const map = mapRef.current
    let cancelled = false
    const getJson = (url) => fetch(url).then((r) => r.json())
    Promise.all([getJson(STATIONS_URL), getJson(STATION_SUMMARY_URL), getJson(SITE_SUMMARY_URL)])
      .then(([stationPoints, stationSummary, siteSummary]) => {
      if (cancelled || map.getSource('sites')) return
      const stations = joinStationSummary(stationPoints, stationSummary)
      siteSummariesRef.current = siteSummary.reduce((periods, row) => {
        periods[row.period] ??= {}
        periods[row.period][row.site] = row
        return periods
      }, {})
      const siteAverages = Object.fromEntries(
        siteSummary.filter((r) => r.period === 'all').map((r) => [r.site, r]))
      stationsRef.current = stations
      startCameraRef.current = fitToSites(map, sites)
      addSitesAndStations(map, siteFeatures(sites, siteSummariesRef.current[periodRef.current]), stations)

      const setHoverState = (id) => setStationHover(map, hoveredIdRef, id)
      map.on('mousemove', 'stations-hit', (e) => {
        const feature = e.features[0]
        setHoverState(feature.id)
        map.getCanvas().style.cursor = 'pointer'
        setHover({
          station: feature.properties,
          siteAverage: siteAverages[feature.properties.site],
          x: e.originalEvent.clientX,
          y: e.originalEvent.clientY,
        })
      })
      map.on('mouseleave', 'stations-hit', () => {
        setHoverState(null)
        map.getCanvas().style.cursor = ''
        setHover(null)
      })
      map.on('click', 'sites', (e) => {
        const site = e.features[0].properties.site
        onFocusRef.current(site)
        popupRef.current?.popup.remove()
        const selectedPeriod = periodRef.current
        const popup = new Popup({ maxWidth: '280px' })
          .setLngLat(e.features[0].geometry.coordinates)
          .setDOMContent(sitePopup(
            e.features[0].properties,
            siteSummariesRef.current[selectedPeriod]?.[site],
            selectedPeriod,
          ))
          popup.on('close', () => {
            if (popupRef.current?.popup === popup) popupRef.current = null
          })
          popup.addTo(map)
        popupRef.current = { popup, site, properties: e.features[0].properties }
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

  // Each period change: resize and recolor the site circles (and move their labels
  // to match), and refresh any open popup.
  useEffect(() => {
    if (!ready) return
    const map = mapRef.current
    const data = siteFeatures(sites, siteSummariesRef.current[period])
    map.getSource('sites').setData(data)
    map.setLayoutProperty('site-labels', 'text-offset', siteLabelLayout(data)['text-offset'])
    const currentPopup = popupRef.current
    if (!currentPopup) return
    currentPopup.popup.setDOMContent(sitePopup(
      currentPopup.properties,
      siteSummariesRef.current[period]?.[currentPopup.site],
      period,
    ))
  }, [period, ready, sites])

  // Station toggle: hide the dots and their invisible hover targets together, so
  // no tooltip appears over empty map. Clear any hover so it can't linger.
  useEffect(() => {
    if (!ready) return
    const map = mapRef.current
    const visibility = showStations ? 'visible' : 'none'
    map.setLayoutProperty('stations', 'visibility', visibility)
    map.setLayoutProperty('stations-hit', 'visibility', visibility)
    if (!showStations) {
      setStationHover(map, hoveredIdRef, null)
      map.getCanvas().style.cursor = ''
      setHover(null)
    }
  }, [showStations, ready])

  const activeStationNote = period === 'all'
    ? stationNote
    : "Station totals don't change by season."

  return (
    <>
      <div ref={containerRef} className="map" />
      <div className="season-controls">
        <div className="season-controls__buttons" role="group" aria-label="Filter site data by season">
          {Object.entries(PERIOD_LABELS).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className="season-controls__button"
              aria-pressed={period === id}
              onClick={() => onPeriodChange(id)}
            >
              {id === 'wet' ? 'Rainy (wet)' : id === 'dry' ? 'Dry' : label}
            </button>
          ))}
        </div>
        <div className="season-controls__label" aria-live="polite">
          Site data: {PERIOD_LABELS[period]}
        </div>
      </div>
      {hover && !hoverDisabled && <StationTooltip {...hover} note={activeStationNote} />}
    </>
  )
}
