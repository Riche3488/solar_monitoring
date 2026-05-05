import { useState, useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea,
} from 'recharts'
import { getDailyByDate, computeRatioStats, SITE_LABELS, fmt } from '../utils/dataUtils'

const S = SITE_LABELS

const TOOLTIP_STYLE = {
  contentStyle: { backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' },
  labelStyle: { color: '#e5e7eb' },
}

export default function AnomalyDetection({ data }) {
  const [threshold, setThreshold] = useState(15)

  const allDaily = useMemo(() => getDailyByDate(data), [data])
  const { mean, std } = useMemo(() => computeRatioStats(allDaily), [allDaily])

  const enriched = useMemo(() =>
    allDaily
      .filter(d => d.ratio !== null)
      .map(d => ({
        ...d,
        deviation: mean > 0 ? ((d.ratio - mean) / mean) * 100 : 0,
        isAnomaly: mean > 0 && Math.abs((d.ratio - mean) / mean) * 100 > threshold,
      })),
    [allDaily, mean, threshold])

  const anomalies = useMemo(() =>
    enriched.filter(d => d.isAnomaly).sort((a, b) => Math.abs(b.deviation) - Math.abs(a.deviation)),
    [enriched])

  const hi = mean * (1 + threshold / 100)
  const lo = mean * (1 - threshold / 100)

  const getJudgement = (row) => {
    if (row.site_8023 !== null && row.site_8024 !== null) {
      if (row.site_8023 < row.site_8024 * 0.6) return { label: `⚠ ${S.site_8023} 저발전`, cls: 'text-red-400' }
      if (row.site_8024 < row.site_8023 * 0.6) return { label: `⚠ ${S.site_8024} 저발전`, cls: 'text-orange-400' }
    }
    return { label: '△ 편차 감지', cls: 'text-yellow-400' }
  }

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <div className="flex flex-wrap items-center gap-8">
          <div>
            <label className="text-gray-400 text-sm block mb-2">
              이상 임계값: <span className="text-white font-semibold">±{threshold}%</span>
            </label>
            <input
              type="range" min={5} max={50} value={threshold}
              onChange={e => setThreshold(Number(e.target.value))}
              className="w-56 accent-blue-500"
            />
          </div>
          <div className="flex gap-6 text-sm">
            <div>
              <span className="text-gray-400">이상 일수 </span>
              <span className="text-red-400 font-bold text-xl">{anomalies.length}</span>
              <span className="text-gray-500"> / {enriched.length}일</span>
            </div>
            <div>
              <span className="text-gray-400">평균 비율 </span>
              <span className="text-green-400 font-semibold">{fmt(mean, 4)}</span>
            </div>
            <div>
              <span className="text-gray-400">표준편차 </span>
              <span className="text-gray-300">{fmt(std, 4)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h2 className="font-semibold text-white mb-4">
          전체 기간 비율 추이 ({S.site_8023} ÷ {S.site_8024}) — 회색 영역 = 정상 범위
        </h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={enriched} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#9ca3af', fontSize: 10 }}
              tickFormatter={v => v?.slice(0, 7) ?? ''}
              interval={Math.floor(enriched.length / 12)}
            />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} domain={['auto', 'auto']} tickFormatter={v => v.toFixed(2)} />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={v => [fmt(v, 4), `비율 (${S.site_8023}/${S.site_8024})`]}
            />
            <ReferenceArea y1={lo} y2={hi} fill="#374151" opacity={0.5} />
            <ReferenceLine y={mean} stroke="#6b7280" strokeDasharray="4 4" />
            <ReferenceLine y={hi} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={lo} stroke="#ef4444" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="ratio" stroke="#22c55e" strokeWidth={1} dot={false} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700">
          <h2 className="font-semibold text-white">이상 감지 목록 — 편차 큰 순</h2>
        </div>
        {anomalies.length === 0 ? (
          <div className="px-5 py-10 text-center text-gray-400">
            임계값 ±{threshold}% 기준으로 이상 없음
          </div>
        ) : (
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-800">
                <tr className="text-gray-400 text-xs border-b border-gray-700">
                  <th className="px-5 py-3 text-left">날짜</th>
                  <th className="px-5 py-3 text-right">{S.site_8023} (kWh)</th>
                  <th className="px-5 py-3 text-right">{S.site_8024} (kWh)</th>
                  <th className="px-5 py-3 text-right">비율</th>
                  <th className="px-5 py-3 text-right">편차</th>
                  <th className="px-5 py-3 text-right">판정</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.slice(0, 200).map(row => {
                  const { label, cls } = getJudgement(row)
                  return (
                    <tr key={row.date} className="border-b border-gray-700/40 hover:bg-gray-700/30 transition">
                      <td className="px-5 py-2 text-gray-300">{row.date}</td>
                      <td className="px-5 py-2 text-right text-blue-300">{row.site_8023 !== null ? fmt(row.site_8023, 1) : '-'}</td>
                      <td className="px-5 py-2 text-right text-orange-300">{row.site_8024 !== null ? fmt(row.site_8024, 1) : '-'}</td>
                      <td className="px-5 py-2 text-right text-white">{fmt(row.ratio, 4)}</td>
                      <td className={`px-5 py-2 text-right font-medium ${row.deviation > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {row.deviation > 0 ? '+' : ''}{fmt(row.deviation, 1)}%
                      </td>
                      <td className={`px-5 py-2 text-right text-xs font-medium ${cls}`}>{label}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
