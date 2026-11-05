import { useCallback, useEffect, useState } from 'react'
import { PANEL } from '../config/panel.js'
import './SidePanel.css'

const mobileQuery = `(max-width: ${PANEL.mobileBreakpoint - 1}px)`

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia(mobileQuery).matches)
  useEffect(() => {
    const mq = window.matchMedia(mobileQuery)
    const onChange = (e) => setIsMobile(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return isMobile
}

const clampWidth = (w) =>
  Math.round(Math.min(Math.max(w, PANEL.minWidth), window.innerWidth * PANEL.maxWidthFraction))

// Open/closed state and width live in component state, so they last while the
// page is open (not across reloads).
export default function SidePanel() {
  const isMobile = useIsMobile()
  const [open, setOpen] = useState(true)
  const [width, setWidth] = useState(() => clampWidth(PANEL.defaultWidth))
  const [dragging, setDragging] = useState(false)

  // Keep the width within bounds when the window shrinks.
  useEffect(() => {
    const onResize = () => setWidth((w) => clampWidth(w))
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // Tell the map controls how much space the panel covers, so they move clear of it.
  useEffect(() => {
    const root = document.documentElement.style
    root.setProperty('--panel-offset', open && !isMobile ? `${width}px` : '0px')
    // On narrow screens the toggle tab sits above the sheet, open or closed.
    root.setProperty('--sheet-offset', !isMobile ? '0px'
      : open ? `calc(${PANEL.sheetHeight} + ${PANEL.toggleSize}px)` : `${PANEL.toggleSize}px`)
    root.setProperty('--panel-transition', dragging ? 'none' : '')
  }, [open, isMobile, width, dragging])

  const onPointerDown = useCallback((e) => {
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    setDragging(true)
  }, [])
  const onPointerMove = useCallback((e) => {
    if (dragging) setWidth(clampWidth(window.innerWidth - e.clientX))
  }, [dragging])
  const onPointerUp = useCallback(() => setDragging(false), [])
  const onHandleKey = useCallback((e) => {
    if (e.key === 'ArrowLeft') setWidth((w) => clampWidth(w + PANEL.keyboardStep))
    if (e.key === 'ArrowRight') setWidth((w) => clampWidth(w - PANEL.keyboardStep))
  }, [])

  const classes = ['side-panel', open ? 'is-open' : 'is-closed',
    isMobile ? 'is-sheet' : 'is-side', dragging ? 'is-dragging' : ''].join(' ')

  return (
    <aside
      className={classes}
      style={isMobile ? { height: PANEL.sheetHeight } : { width }}
      aria-label="Map controls"
    >
      <button
        type="button"
        className="side-panel__toggle"
        aria-expanded={open}
        aria-controls="side-panel-content"
        onClick={() => setOpen((o) => !o)}
      >
        <span aria-hidden="true">{toggleArrow(open, isMobile)}</span>
        <span className="visually-hidden">{open ? 'Close panel' : 'Open panel'}</span>
      </button>

      {!isMobile && (
        <div
          className="side-panel__resize"
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize panel"
          aria-valuemin={PANEL.minWidth}
          aria-valuemax={Math.round(window.innerWidth * PANEL.maxWidthFraction)}
          aria-valuenow={width}
          tabIndex={open ? 0 : -1}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onKeyDown={onHandleKey}
        />
      )}

      <div id="side-panel-content" className="side-panel__content" inert={!open}>
        <section className="side-panel__section" aria-labelledby="panel-sites">
          <h2 id="panel-sites">Sites</h2>
          <p className="side-panel__placeholder">Site buttons will go here (Step 2.5).</p>
        </section>
        <section className="side-panel__section" aria-labelledby="panel-layers">
          <h2 id="panel-layers">Layers</h2>
          <p className="side-panel__placeholder">Layer and measure controls will go here (Phases 3 and 4).</p>
        </section>
      </div>
    </aside>
  )
}

function toggleArrow(open, isMobile) {
  if (isMobile) return open ? '▾' : '▴'
  return open ? '›' : '‹'
}
