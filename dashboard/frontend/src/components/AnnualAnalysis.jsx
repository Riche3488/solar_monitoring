import { useState, useMemo } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell, LabelList,
} from 'recharts'
import { getAnnualTotals, getMonthlyTotals, SITE_LABELS, SITE_COLORS, fmt } from '../utils/dataUtils'

const S = SITE_LABELS
const C = SITE_COLORS

const TOOLTIP_STYLE = {
  contentStyle: { backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' },
  labelStyle: { color: '#e5e7eb' },
}

function HoursBarLabel({ x, y, width, value, index, annualData, yoyKey }) {
  const row = annualData?.[index]
  const yoy = row?.[yoyKey] ?? null
  const yoyColor = yoy === null ? '#9ca3af' : yoy >= 0 ? '#22c55e' : '#ef4444'
  return (
    <text textAnchor="middle" fontSize={10}>
      <tspan x={x + width / 2} y={y - 18} fill="#e5e7eb">
        {value != null ? `${value.toFixed(2)}h` : ''}
      </tspan>
      {yoy !== null && (
        <tspan x={x + width / 2} y={y - 6} fill={yoyColor}>
          {`(${yoy > 0 ? '+' : ''}${fmt(yoy, 1)}%)`}
        </tspan>
      )}
    </text>
  )
}

export default function AnnualAnalysis({ data }) {
  const [sameMonth, setSameMonth] = useState(6)
  const [siteTab, setSiteTab] = useState('site_8023')

  const annual = useMemo(() => getAnnualTotals(data), [data])
  const monthly = useMemo(() => getMonthlyTotals(data), [data])

  const annualWithYoY = useMemo(() =>
    annual.map((row, i) => {
      const prev = annual[i - 1]
      return {
        ...row,
        yoy8023: prev && prev.avg_hours_8023 > 0 ? ((row.avg_hours_8023 - prev.avg_hours_8023) / prev.avg_hours_8023) * 100 : null,
        yoy8024: prev && prev.avg_hours_8024 > 0 ? ((row.avg_hours_8024 - prev.avg_hours_8024) / prev.avg_hours_8024) * 100 : null,
      }
    }), [annual])

  const sameMonthData = useMemo(() =>
    monthly.filter(d => d.month === sameMonth), [monthly, sameMonth])

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h2 className="font-semibold text-white mb-4">연간 총 발전량 (kWh)</h2>
        <p className="text-gray-500 text-xs mb-3">* 표시 연도 = 해당 연도 데이터 일부만 존재</p>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={annual} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="year"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickFormatter={y => {
                const row = annual.find(r => r.year === y)
                return row?.months_count < 12 ? `${y}*` : `${y}`
              }}
            />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v, name) => [`${fmt(v)} kWh`, name === 'site_8023' ? S.site_8023 : S.site_8024]}
              labelFormatter={y => {
                const row = annual.find(r => r.year === y)
                return `${y}년 (${row?.months_count ?? '?'}개월)`
              }}
            />
            <Legend formatter={v => v === 'site_8023' ? S.site_8023 : S.site_8024} wrapperStyle={{ color: '#9ca3af', fontSize: 13 }} />
            <Bar dataKey="site_8023" name="site_8023" fill={C.site_8023} radius={[3, 3, 0, 0]} />
            <Bar dataKey="site_8024" name="site_8024" fill={C.site_8024} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-white">일평균 발전시간 연도별 추이</h2>
          <div className="flex gap-1">
            {['site_8023', 'site_8024'].map(s => (
              <button
                key={s}
                onClick={() => setSiteTab(s)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                  siteTab === s
                    ? s === 'site_8023' ? 'bg-blue-600 text-white' : 'bg-orange-500 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {S[s]}
              </button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={annualWithYoY} margin={{ top: 36, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="year" tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={v => `${v.toFixed(1)}h`} domain={[0, 'auto']} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v, _, props) => {
                const row = props.payload
                const yoy = siteTab === 'site_8023' ? row?.yoy8023 : row?.yoy8024
                const yoyStr = yoy != null ? ` (${yoy > 0 ? '+' : ''}${fmt(yoy, 1)}%)` : ''
                return [`${v != null ? v.toFixed(2) : '-'}h${yoyStr}`, '일평균 발전시간']
              }}
              labelFormatter={y => `${y}년`}
            />
            <Bar
              dataKey={siteTab === 'site_8023' ? 'avg_hours_8023' : 'avg_hours_8024'}
              fill={C[siteTab]}
              radius={[3, 3, 0, 0]}
            >
              <LabelList
                dataKey={siteTab === 'site_8023' ? 'avg_hours_8023' : 'avg_hours_8024'}
                content={(props) => (
                  <HoursBarLabel
                    {...props}
                    annualData={annualWithYoY}
                    yoyKey={siteTab === 'site_8023' ? 'yoy8023' : 'yoy8024'}
                  />
                )}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-white">동일 월 연도별 비교 (노후화 모니터링)</h2>
            <p className="text-gray-500 text-xs mt-0.5">같은 계절 발전량이 해를 거듭할수록 감소하면 시설 노후화 신호</p>
          </div>
          <select
            value={sameMonth}
            onChange={e => setSameMonth(Number(e.target.value))}
            className="bg-gray-700 text-gray-200 rounded-lg px-3 py-2 text-sm border border-gray-600 focus:outline-none"
          >
            {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
              <option key={m} value={m}>{m}월</option>
            ))}
          </select>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={sameMonthData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="year" tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v, name) => [`${fmt(v)} kWh`, name === 'site_8023' ? S.site_8023 : S.site_8024]}
              labelFormatter={y => `${y}년 ${sameMonth}월`}
            />
            <Legend formatter={v => v === 'site_8023' ? S.site_8023 : S.site_8024} wrapperStyle={{ color: '#9ca3af', fontSize: 13 }} />
            <Line type="monotone" dataKey="site_8023" name="site_8023" stroke={C.site_8023} strokeWidth={2} dot={{ r: 4, fill: C.site_8023 }} />
            <Line type="monotone" dataKey="site_8024" name="site_8024" stroke={C.site_8024} strokeWidth={2} dot={{ r: 4, fill: C.site_8024 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700">
          <h2 className="font-semibold text-white">연간 발전량 요약</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-xs border-b border-gray-700">
                <th className="px-5 py-3 text-left">연도</th>
                <th className="px-5 py-3 text-right">{S.site_8023} (kWh)</th>
                <th className="px-5 py-3 text-right">일평균 발전시간</th>
                <th className="px-5 py-3 text-right">전년비 (발전시간)</th>
                <th className="px-5 py-3 text-right">{S.site_8024} (kWh)</th>
                <th className="px-5 py-3 text-right">일평균 발전시간</th>
                <th className="px-5 py-3 text-right">전년비 (발전시간)</th>
                <th className="px-5 py-3 text-right">비율</th>
                <th className="px-5 py-3 text-right">데이터</th>
              </tr>
            </thead>
            <tbody>
              {annualWithYoY.map(row => (
                <tr key={row.year} className="border-b border-gray-700/40 hover:bg-gray-700/30 transition">
                  <td className="px-5 py-2.5 font-medium text-white">{row.year}년</td>
                  <td className="px-5 py-2.5 text-right text-blue-300">{fmt(row.site_8023)}</td>
                  <td className="px-5 py-2.5 text-right text-gray-300">{row.avg_hours_8023 !== null ? `${fmt(row.avg_hours_8023, 1)}h` : '-'}</td>
                  <td className={`px-5 py-2.5 text-right font-medium ${row.yoy8023 === null ? 'text-gray-500' : row.yoy8023 >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {row.yoy8023 !== null ? `${row.yoy8023 > 0 ? '+' : ''}${fmt(row.yoy8023, 1)}%` : '-'}
                  </td>
                  <td className="px-5 py-2.5 text-right text-orange-300">{fmt(row.site_8024)}</td>
                  <td className="px-5 py-2.5 text-right text-gray-300">{row.avg_hours_8024 !== null ? `${fmt(row.avg_hours_8024, 1)}h` : '-'}</td>
                  <td className={`px-5 py-2.5 text-right font-medium ${row.yoy8024 === null ? 'text-gray-500' : row.yoy8024 >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {row.yoy8024 !== null ? `${row.yoy8024 > 0 ? '+' : ''}${fmt(row.yoy8024, 1)}%` : '-'}
                  </td>
                  <td className={`px-5 py-2.5 text-right font-medium ${row.ratio === null ? 'text-gray-500' : Math.abs(row.ratio - 1) > 0.15 ? 'text-red-400' : 'text-green-400'}`}>
                    {row.ratio !== null ? `${fmt(row.ratio * 100, 1)}%` : '-'}
                  </td>
                  <td className="px-5 py-2.5 text-right text-xs">
                    {row.months_count < 12 ? <span className="text-yellow-500">{row.months_count}개월</span> : <span className="text-gray-500">12개월</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
