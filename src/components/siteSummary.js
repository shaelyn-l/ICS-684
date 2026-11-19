// Site summary content shared by the site popup (overview, on hover) and the site
// card (shown while a site is focused), so both always show the same values.

export const number = (m) => Math.round(m).toLocaleString('en-US')
export const metres = (m) => `${number(m)} m`

// The four site measures shown, each with its sample size (site_summary.json).
export const SITE_SUMMARY_METRICS = [
  { key: 'mosquito_per_trap_night', label: 'Mosquitoes per trap night', sample: 'mosquito_trap_nights', digits: 3 },
  { key: 'mosq_salivary_pct', label: 'Mosquito infection (salivary glands)', sample: 'mosq_salivary_n', digits: 1, unit: '%', percentage: true },
  { key: 'bird_prevalence_pct', label: 'Bird malaria prevalence', sample: 'bird_sampled_n', digits: 1, unit: '%', percentage: true },
  { key: 'honeycreepers_per_count', label: 'Honeycreepers per count', sample: 'bird_counts_n', digits: 2 },
]

// One measure as text: value and sample size, or why there's no value.
export function siteMetricValue(site, summary, metric) {
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
