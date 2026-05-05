import { useState, useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { getMonthlyTotals, SITE_LABELS, SITE_COLORS, fmt } from '../utils/dataUtils'

const S = SITE_LABELS
const C = SITE_COLORS

const TOOLTIP_STYLE = {
  contentStyle: { backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' },
  labelStyle: { color: '#e5e7eb' },
}

export default function MonthlyTrend({ data }) {
  const [normalized, setNormalized] = useState(false)
  const monthly = useMemo(() => getMonthlyTotals(data), [data])

  const chartData = useMemo(() => {
    if (!normalized || !monthly.length) return monthly
    const first12 = monthly.slice(0, 12)
    const base8023 = first12.reduce((s, d) => s + d.site_8023, 0) / first12.length
    const base8024 = first12.reduce((s, d) => s + d.site_8024, 0) / first12.length
    return monthly.map(d => ({
      ...d,
      site_8023: base8023 > 0 ? (d.site_8023 / base8023) * 100 : null,
      site_8024: base8024 > 0 ? (d.site_8024 / base8024) * 100 : null,
    }))
  }, [monthly, normalized])

  const tickFormatter = (val, idx) => {
    const d = chartData[idx]
    if (!d) return ''
    if (d.month === 1) return `${d.year}`
    if (d.month % 3 === 1) return `${d.month}월`
    return ''
  }

  const labelFormatter = key => {
    const [y, m] = key.split('-')
    return `${y}년 ${parseInt(m)}월`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={normalized}
            onChange={e => setNormalized(e.target.checked)}
            className="w-4 h-4 accent-blue-500"
          />
          <span className="text-gray-300 text-sm">정규화 표시 (초기 12개월 평균 대비 %)</span>
        </label>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h2 className="font-semibold text-white mb-4">
          월별 발전량 추이 {normalized ? '(정규화 %)' : '(kWh)'}
        </h2>
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="key"
              tick={{ fill: '#9ca3af', fontSize: 10 }}
              tickFormatter={tickFormatter}
              angle={-45}
              textAnchor="end"
              interval={2}
            />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} unit={normalized ? '%' : ''} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v, name) => [
                normalized ? `${fmt(v, 1)}%` : `${fmt(v)} kWh`,
                name === 'site_8023' ? S.site_8023 : S.site_8024,
              ]}
              labelFormatter={labelFormatter}
            />
            <Legend
              formatter={v => v === 'site_8023' ? S.site_8023 : S.site_8024}
              wrapperStyle={{ color: '#9ca3af', fontSize: 13 }}
            />
            <Line type="monotone" dataKey="site_8023" name="site_8023" stroke={C.site_8023} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="site_8024" name="site_8024" stroke={C.site_8024} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h2 className="font-semibold text-white mb-4">
          월별 비율 추이 ({S.site_8023} ÷ {S.site_8024})
        </h2>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={monthly} margin={{ top: 5, right: 20, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="key"
              tick={{ fill: '#9ca3af', fontSize: 10 }}
              tickFormatter={tickFormatter}
              angle={-45}
              textAnchor="end"
              interval={2}
            />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={v => v.toFixed(2)} domain={['auto', 'auto']} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={v => [v !== null ? fmt(v, 4) : '-', `비율 (${S.site_8023}/${S.site_8024})`]}
              labelFormatter={labelFormatter}
            />
            <Line
              type="monotone"
              dataKey="ratio"
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
