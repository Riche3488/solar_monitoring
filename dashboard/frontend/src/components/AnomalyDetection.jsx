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
  const [customYAxis, setCustomYAxis] = useState(false)
  const [yMin, setYMin] = useState(0.95)
  const [yMax, setYMax] = useState(1)

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
        <div className="flex flex-wrap items-center gap-4 mt-5 pt-4 border-t border-gray-700">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={customYAxis}
              onChange={e => setCustomYAxis(e.target.checked)}
              className="w-4 h-4 accent-blue-500"
            />
            <span className="text-gray-300 text-sm">Y축 범위 직접 설정</span>
          </label>
          {customYAxis && (
            <div className="flex items-center gap-2 text-sm">
              <input
                type="number" step="0.01" value={yMin}
                onChange={e => setYMin(Number(e.target.value))}
                className="w-20 bg-gray-700 text-gray-200 rounded-lg px-2 py-1.5 border border-gray-600 focus:outline-none"
              />
              <span className="text-gray-500">~</span>
              <input
                type="number" step="0.01" value={yMax}
                onChange={e => setYMax(Number(e.target.value))}
                className="w-20 bg-gray-700 text-gray-200 rounded-lg px-2 py-1.5 border border-gray-600 focus:outline-none"
              />
            </div>
          )}
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h2 className="font-semibold text-white mb-4">
          전체 기간 비율 추이 ({S.site_8023} ÷ {S.site_8024}) — 회색 영역 = 정상 범위
        </h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={enriched} margin={{ top: 5, right: 20, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#9ca3af', fontSize: 10 }}
              tickFormatter={(v, idx) => {
                const d = enriched[idx]
                if (!d) return ''
                return d.day === 1 && d.month === 1 ? `${d.year}년` : d.day === 1 ? `${d.month}월` : ''
              }}
              interval={0}
              angle={-45}
              textAnchor="end"
            />
            <YAxis
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              domain={customYAxis ? [yMin, yMax] : ['auto', 'auto']}
              allowDataOverflow={customYAxis}
              tickFormatter={v => v.toFixed(2)}
            />
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

    </div>
  )
}
