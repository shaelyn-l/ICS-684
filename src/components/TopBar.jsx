import { TABS, TOP_BAR_TITLE } from '../config/tabs.js'
import './TopBar.css'

// Always-visible bar above the map: project title and tabs for reference pages.
// activeTab is the id of the tab whose page is open in the overlay, or null.
export default function TopBar({ activeTab, onOpenTab }) {
  return (
    <header className="top-bar">
      <div className="top-bar__title">{TOP_BAR_TITLE}</div>
      <nav className="top-bar__tabs" aria-label="About this map">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className="top-bar__tab"
            aria-haspopup="dialog"
            aria-expanded={activeTab === id}
            onClick={(e) => onOpenTab(id, e.currentTarget)}
          >
            {label}
          </button>
        ))}
      </nav>
    </header>
  )
}
