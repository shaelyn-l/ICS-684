// Map settings: basemap, terrain, and camera for Hawaiʻi Island.

// OpenFreeMap: free vector basemap, no account or API key.
export const BASEMAP_STYLE = 'https://tiles.openfreemap.org/styles/liberty'

// View used while the basemap loads, before the camera is fitted to the sites.
export const INITIAL_VIEW = {
  center: [-155.5, 19.6], // [longitude, latitude], middle of Hawaiʻi Island
  zoom: 8.3,
}

// AWS Terrain Tiles (Terrarium encoding): free, no key. Visual only; elevations
// shown to users come from the data (elevation_m), not from these tiles.
export const TERRAIN = {
  tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
  encoding: 'terrarium',
  tileSize: 256,
  maxzoom: 15,
  attribution:
    '<a href="https://github.com/tilezen/joerd/blob/master/docs/attribution.md">Terrain Tiles</a> (USGS 3DEP and others)',
  // 3× so the 28–1,836 m study gradient stands out on the gentle shield slope.
  // Summits look steeper than reality; this is for readability only.
  exaggeration: 3,
}

// Draped layers (hillshade now; land cover and malaria zones later) are inserted
// before this basemap layer: above land and vegetation, below waterways, water,
// roads, and labels. The water layer covers the hillshade offshore, where the
// terrain tiles include sea-floor depth.
export const DRAPE_BEFORE_LAYER = 'waterway_tunnel'

export const HILLSHADE = {
  exaggeration: 0.75,
  shadowColor: '#2b2b2b',
  highlightColor: '#ffffff',
}

// Elevation tint (color relief), drawn under the hillshade. Most of the color
// change falls in 0–2,000 m, where the study sites are; above that it fades to
// grey and white toward the summits (Mauna Loa ~4,170 m).
export const ELEVATION_TINT = {
  opacity: 0.45,
  stops: [
    [0, '#2e7d32'],
    [400, '#7cb342'],
    [800, '#c0ca33'],
    [1200, '#e6c35c'],
    [1600, '#c8894a'],
    [2000, '#a1704f'],
    [3000, '#9e9289'],
    [4200, '#f5f5f5'],
  ],
}

// Starting camera, fitted to the bounds of sites.geojson once the map loads.
// Bearing 270 looks west: upslope from the ocean side, low sites in the
// foreground and Mauna Loa rising behind the high sites.
export const SITES_URL = `${import.meta.env.BASE_URL}data/sites.geojson`
export const STATIONS_URL = `${import.meta.env.BASE_URL}data/stations.geojson`
export const START_CAMERA = {
  pitch: 60,
  bearing: 270,
  // Room around the sites; the extra right padding keeps them clear of the
  // side panel (about 350px wide, Step 2.4).
  padding: { top: 120, bottom: 80, left: 80, right: 430 },
  maxZoom: 11,
}
// Site and station markers, drawn above all basemap layers.
export const SITE_MARKER = {
  radius: 9,
  color: '#1f4e79',
  strokeColor: '#ffffff',
  strokeWidth: 2,
  labelFont: ['Noto Sans Bold'],
  labelSize: 13,
  labelColor: '#1a1a1a',
  labelHaloColor: '#ffffff',
  labelHaloWidth: 2,
  // Labels sit to the right of each circle, except where sites are close
  // together (CJR is just west of SOL, CRA just west of COO).
  labelSide: { CJR: 'left', CRA: 'left' },
  // Focused site (Step 2.5): larger, with a gold outline. Other sites dim.
  selected: { radius: 12, strokeColor: '#f5b700', strokeWidth: 3.5 },
  dimmedOpacity: 0.35,
}

// Camera when a site is focused (Step 2.5). The zoom is fitted to the site's 45
// stations so all of them are in view; the side panel's width is added to the
// right padding at fly time. `overrides` sets a fixed { zoom, pitch } for a site
// if its fitted view needs adjusting.
export const SITE_FOCUS = {
  pitch: 55,
  bearing: 270, // same upslope, west-facing direction as the starting view
  duration: 2000, // ms
  padding: { top: 80, bottom: 80, left: 80, right: 80 },
  overrides: {},
}

export const STATION_MARKER = {
  // Each site's 45 stations fit in about 1 km², so they only appear zoomed in.
  minZoom: 11,
  radius: 3,
  color: '#555555',
  opacity: 0.7,
  strokeColor: '#ffffff',
  strokeWidth: 0.75,
}

// How far the camera can tilt toward the horizon (MapLibre's default is 60).
export const MAX_PITCH = 80

export const SKY = {
  'sky-color': '#9ec7ea',
  'horizon-color': '#eaf2f8',
  'fog-color': '#eaf2f8',
  'sky-horizon-blend': 0.5,
  'horizon-fog-blend': 0.6,
  'fog-ground-blend': 0.85,
}
