import './StationToggle.css'

// Shows or hides the station dots and their tooltips (Step 4.1 toggle).
export default function StationToggle({ checked, onChange }) {
  return (
    <label className="station-toggle">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      Show sampling stations
      <span className="station-toggle__hint">(visible when zoomed in to a site)</span>
    </label>
  )
}
