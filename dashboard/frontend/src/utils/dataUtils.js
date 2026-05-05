export const SITE_LABELS = { site_8023: '호란발전소', site_8024: '소미발전소' }
export const SITE_COLORS = { site_8023: '#3b82f6', site_8024: '#f97316' }
export const SITES = ['site_8023', 'site_8024']

export function getAvailableMonths(data) {
  const set = new Set(data.map(d => `${d.year}-${String(d.month).padStart(2, '0')}`))
  return Array.from(set).sort()
}

export function getYears(data) {
  return [...new Set(data.map(d => d.year))].sort()
}

export function getMonthlyTotals(data) {
  const map = {}
  for (const d of data) {
    if (d.generation_kwh === null) continue
    const key = `${d.year}-${String(d.month).padStart(2, '0')}`
    if (!map[key]) map[key] = { key, year: d.year, month: d.month, site_8023: 0, site_8024: 0 }
    map[key][d.site_id] = (map[key][d.site_id] || 0) + d.generation_kwh
  }
  return Object.values(map)
    .sort((a, b) => a.key.localeCompare(b.key))
    .map(r => ({ ...r, ratio: r.site_8024 > 0 ? r.site_8023 / r.site_8024 : null }))
}

export function getAnnualTotals(data) {
  const map = {}
  for (const d of data) {
    if (d.generation_kwh === null) continue
    const y = d.year
    if (!map[y]) map[y] = { year: y, site_8023: 0, site_8024: 0, _months: new Set() }
    map[y][d.site_id] = (map[y][d.site_id] || 0) + d.generation_kwh
    map[y]._months.add(d.month)
  }
  return Object.values(map)
    .sort((a, b) => a.year - b.year)
    .map(({ _months, ...r }) => ({
      ...r,
      months_count: _months.size,
      ratio: r.site_8024 > 0 ? r.site_8023 / r.site_8024 : null,
    }))
}

export function getDailyForMonth(data, year, month) {
  const map = {}
  for (const d of data) {
    if (d.year !== year || d.month !== month) continue
    if (!map[d.day]) map[d.day] = { day: d.day, site_8023: null, site_8024: null }
    map[d.day][d.site_id] = d.generation_kwh
  }
  return Object.values(map)
    .sort((a, b) => a.day - b.day)
    .map(d => ({
      ...d,
      ratio: d.site_8023 !== null && d.site_8024 !== null && d.site_8024 > 0
        ? d.site_8023 / d.site_8024
        : null,
    }))
}

export function getDailyByDate(data) {
  const map = {}
  for (const d of data) {
    if (!map[d.date]) map[d.date] = { date: d.date, year: d.year, month: d.month, day: d.day, site_8023: null, site_8024: null }
    map[d.date][d.site_id] = d.generation_kwh
  }
  return Object.values(map)
    .sort((a, b) => a.date.localeCompare(b.date))
    .map(d => ({
      ...d,
      ratio: d.site_8023 !== null && d.site_8024 !== null && d.site_8024 > 0
        ? d.site_8023 / d.site_8024
        : null,
    }))
}

export function getLatestDay(data) {
  const byDate = {}
  for (const d of data) {
    if (d.generation_kwh === null) continue
    if (!byDate[d.date]) byDate[d.date] = { date: d.date, year: d.year, month: d.month, day: d.day, site_8023: null, site_8024: null }
    byDate[d.date][d.site_id] = d.generation_kwh
  }
  const dates = Object.keys(byDate).sort()
  return dates.length ? byDate[dates[dates.length - 1]] : null
}

export function computeRatioStats(dailyAll) {
  const valid = dailyAll.filter(d => d.ratio !== null)
  if (!valid.length) return { mean: 1, std: 0 }
  const mean = valid.reduce((s, d) => s + d.ratio, 0) / valid.length
  const std = Math.sqrt(valid.reduce((s, d) => s + (d.ratio - mean) ** 2, 0) / valid.length)
  return { mean, std }
}

export function fmt(n, digits = 0) {
  if (n === null || n === undefined) return '-'
  return n.toLocaleString('ko-KR', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}
