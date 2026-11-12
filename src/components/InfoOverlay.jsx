import { useEffect, useRef } from 'react'
import './InfoOverlay.css'

// A large reading panel over the dimmed map (Step 2.7). Uses the native <dialog>
// in modal mode: the browser moves focus into it, keeps Tab inside it, and makes
// the page behind it inert. Closes with the X, Escape, or a click on the dimmed
// area. The map underneath is never touched, so it comes back as it was.
// returnFocusRef: the control that opened the overlay; focus goes back to it on close.
export default function InfoOverlay({ title, onClose, returnFocusRef, children }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    const dialog = dialogRef.current
    const returnTo = returnFocusRef?.current
    if (!dialog.open) dialog.showModal() // guard: StrictMode runs effects twice in dev
    return () => {
      dialog.close()
      // Only after close: while the modal is open the rest of the page is inert.
      returnTo?.focus()
    }
  }, [returnFocusRef])

  return (
    <dialog
      ref={dialogRef}
      className="info-overlay"
      aria-labelledby="info-overlay-title"
      // Escape: let React close it (instead of the browser), so state stays in sync.
      onCancel={(e) => { e.preventDefault(); onClose() }}
      // Clicks on the dialog element itself land on the dimmed backdrop around the panel.
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="info-overlay__panel">
        <header className="info-overlay__header">
          <h1 id="info-overlay-title">{title}</h1>
          <button type="button" className="info-overlay__close" onClick={onClose} aria-label="Close">
            <span aria-hidden="true">×</span>
          </button>
        </header>
        <div className="info-overlay__body">{children}</div>
      </div>
    </dialog>
  )
}
