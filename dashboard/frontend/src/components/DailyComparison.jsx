import { useState, useMemo } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { getDailyForMonth, getAvailableMonths, computeRatioStats, SITE_LABELS, SITE_COLORS, fmt } from '../utils/dataUtils'

const S = SITE_LABELS
const C = SITE_COLORS

const TOOLTIP_STYLE = {
  contentStyle: { backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' },
  labelStyle: { color: '#e5e7eb' },
}

export default function DailyComparison({ data }) {
  const months = useMemo(() => getAvailableMonths(data), [data])
  const [selected, setSelected] = useState(() => months[months.length - 1] ?? '')

  const [year, month] = selected ? selected.split('-').map(Number) : [0, 0]
  const daily = useMemo(() => getDailyForMonth(data, year, month), [data, year, month])
  const { mean } = useMemo(() => computeRatioStats(daily), [daily])

  const CustomDot = (props) => {
    const { cx, cy, payload } = props
    if (payload.ratio === null) return null
    const bad = Math.abs(payload.ratio - mean) / mean > 0.1
    return <circle cx={cx} cy={cy} r={3} fill={bad ? '#ef4444' : '#22c55e'} key={`dot-${payload.day}`} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <span className="text-gray-400 text-sm">월 선택</span>
        <select
          value={selected}
          onChange={e => setSelected(e.target.value)}
          className="bg-gray-700 text-gray-200 rounded-lg px-3 py-2 text-sm border border-gray-600 focus:outline-none"
        >
          {[...months].reverse().map(m => {
            const [y, mo] = m.split('-')
            return <option key={m} value={m}>{y}년 {parseInt(mo)}월</option>
          })}
        </select>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h2 className="font-semibold text-white mb-4">일별 발전량 비교 (kWh)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={daily} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="day" tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={v => `${v}일`} />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v, name) => [v !== null ? `${fmt(v, 1)} kWh` : '-', name]}
              labelFormatter={l => `${l}일`}
            />
            <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 13 }} />
            <Bar dataKey="site_8023" name={S.site_8023} fill={C.site_8023} opacity={0.85} radius={[2, 2, 0, 0]} />
            <Bar dataKey="site_8024" name={S.site_8024} fill={C.site_8024} opacity={0.85} radius={[2, 2, 0, 0]} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-semibold text-white">발전소 간 비율 ({S.site_8023} ÷ {S.site_8024})</h2>
          <span className="text-gray-400 text-xs">평균 {fmt(mean, 3)} | 빨간 점 = ±10% 이탈</span>
        </div>
        <p className="text-gray-500 text-xs mb-4">적색 점선 = 평균 ±10% 경계</p>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={daily} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="day" tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={v => `${v}일`} />
            <YAxis domain={['auto', 'auto']} tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={v => v.toFixed(2)} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={v => [v !== null ? fmt(v, 4) : '-', '비율']}
              labelFormatter={l => `${l}일`}
            />
            <ReferenceLine y={mean} stroke="#6b7280" strokeDasharray="4 4" label={{ value: '평균', fill: '#6b7280', fontSize: 10 }} />
            <ReferenceLine y={mean * 0.9} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={mean * 1.1} stroke="#ef4444" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="ratio"
              name="비율"
              stroke="#22c55e"
              strokeWidth={2}
              dot={<CustomDot />}
              connectNulls={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
