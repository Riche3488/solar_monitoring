import { useState, useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { getMonthlyTotals, SITE_LABELS, SITE_COLORS, fmt } from '../utils/dataUtils'

const S = SITE_LABELS
const C = SITE_COLORS

const TOOLTIP_STYLE = {
  contentStyle: { backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' },
  labelStyle: { color: '#e5e7eb' },
}

const METRICS = {
  cumulative: { key8023: 'site_8023', key8024: 'site_8024', unit: 'kWh', digits: 0, label: '누적', title: '월별 발전량 추이 (누적 kWh)' },
  average: { key8023: 'avg_site_8023', key8024: 'avg_site_8024', unit: 'kWh/일', digits: 1, label: '일평균 발전량', title: '월별 발전량 추이 (일평균 kWh)' },
  hours: { key8023: 'avg_hours_8023', key8024: 'avg_hours_8024', unit: '시간', digits: 2, label: '일평균 발전시간', title: '월별 일평균 발전시간 추이' },
}

export default function MonthlyTrend({ data }) {
  const [metric, setMetric] = useState('cumulative')
  const [normalized, setNormalized] = useState(false)
  const monthly = useMemo(() => getMonthlyTotals(data), [data])
  const metricCfg = METRICS[metric]

  const chartData = useMemo(() => {
    if (!normalized || !monthly.length) return monthly
    const first12 = monthly.slice(0, 12)
    const vals8023 = first12.map(d => d[metricCfg.key8023]).filter(v => v !== null)
    const vals8024 = first12.map(d => d[metricCfg.key8024]).filter(v => v !== null)
    const base8023 = vals8023.length ? vals8023.reduce((s, v) => s + v, 0) / vals8023.length : 0
    const base8024 = vals8024.length ? vals8024.reduce((s, v) => s + v, 0) / vals8024.length : 0
    return monthly.map(d => ({
      ...d,
      [metricCfg.key8023]: base8023 > 0 && d[metricCfg.key8023] !== null ? (d[metricCfg.key8023] / base8023) * 100 : null,
      [metricCfg.key8024]: base8024 > 0 && d[metricCfg.key8024] !== null ? (d[metricCfg.key8024] / base8024) * 100 : null,
    }))
  }, [monthly, normalized, metricCfg])

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
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex gap-1">
          {Object.entries(METRICS).map(([key, cfg]) => (
            <button
              key={key}
              onClick={() => setMetric(key)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                metric === key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {cfg.label}
            </button>
          ))}
        </div>
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
          {metricCfg.title} {normalized ? '→ 정규화 (%)' : ''}
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
                normalized ? `${fmt(v, 1)}%` : `${fmt(v, metricCfg.digits)} ${metricCfg.unit}`,
                name === metricCfg.key8023 ? S.site_8023 : S.site_8024,
              ]}
              labelFormatter={labelFormatter}
            />
            <Legend
              formatter={v => v === metricCfg.key8023 ? S.site_8023 : S.site_8024}
              wrapperStyle={{ color: '#9ca3af', fontSize: 13 }}
            />
            <Line type="monotone" dataKey={metricCfg.key8023} name={metricCfg.key8023} stroke={C.site_8023} strokeWidth={2} dot={false} connectNulls={false} />
            <Line type="monotone" dataKey={metricCfg.key8024} name={metricCfg.key8024} stroke={C.site_8024} strokeWidth={2} dot={false} connectNulls={false} />
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
            <ReferenceLine y={1} stroke="#6b7280" strokeDasharray="4 4" label={{ value: '1.0', fill: '#6b7280', fontSize: 11 }} />
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
