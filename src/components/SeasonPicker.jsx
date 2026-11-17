import { PERIOD_GROUPS, PERIOD_HEADINGS } from '../config/periods.js'
import './SeasonPicker.css'

// Chooses which period the site popups show. Station values stay all seasons.
export default function SeasonPicker({ period, onChangePeriod }) {
  return (
    <div className="season-picker">
      <h3 className="season-picker__title">Site data season</h3>
      {PERIOD_GROUPS.map((group, i) => (
        <div key={group.label} className="season-picker__group">
          <div className="season-picker__group-label" id={`season-group-${i}`}>
            {group.label}
          </div>
          <div
            className="season-picker__buttons"
            role="group"
            aria-labelledby={`season-group-${i}`}
          >
            {group.periods.map((p) => (
              <button
                key={p.id}
                type="button"
                className="season-picker__button"
                aria-pressed={period === p.id}
                title={p.heading}
                onClick={() => onChangePeriod(p.id)}
              >
                {p.button}
              </button>
            ))}
          </div>
        </div>
      ))}
      <p className="season-picker__current" aria-live="polite">
        Showing: {PERIOD_HEADINGS[period]}
      </p>
      <p className="season-picker__note">
        Changes the numbers in site popups. Station values stay all seasons.
      </p>
    </div>
  )
}
