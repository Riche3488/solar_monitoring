import { useMemo } from 'react'
import { getMonthlyTotals, getAnnualTotals, SITE_LABELS, fmt } from '../utils/dataUtils'

const S = SITE_LABELS

function Card({ title, value, sub, valueClass = 'text-white' }) {
  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
      <p className="text-gray-400 text-xs mb-1">{title}</p>
      <p className={`text-2xl font-bold ${valueClass}`}>{value}</p>
      {sub && <p className="text-gray-500 text-xs mt-1">{sub}</p>}
    </div>
  )
}

export default function OverviewCards({ data }) {
  const monthly = useMemo(() => getMonthlyTotals(data), [data])
  const annual = useMemo(() => getAnnualTotals(data), [data])

  const latest = monthly[monthly.length - 1]
  const curYear = annual[annual.length - 1]
  const prevYear = annual[annual.length - 2]

  const yoy8023 = curYear && prevYear && prevYear.site_8023 > 0
    ? ((curYear.site_8023 - prevYear.site_8023) / prevYear.site_8023) * 100
    : null

  const latestRatio = latest?.ratio
  const ratioOk = latestRatio !== null && latestRatio !== undefined && Math.abs(latestRatio - 1) < 0.15

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          title={`이번 달 발전량 — ${S.site_8023}${latest ? ` (${latest.year}년 ${latest.month}월)` : ''}`}
          value={latest ? `${fmt(latest.site_8023)} kWh` : '-'}
          valueClass="text-blue-400"
        />
        <Card
          title={`이번 달 발전량 — ${S.site_8024}${latest ? ` (${latest.year}년 ${latest.month}월)` : ''}`}
          value={latest ? `${fmt(latest.site_8024)} kWh` : '-'}
          valueClass="text-orange-400"
        />
        <Card
          title={`이번 달 비율 (${S.site_8023} ÷ ${S.site_8024})`}
          value={latestRatio !== null && latestRatio !== undefined ? `${fmt(latestRatio * 100, 1)}%` : '-'}
          sub="정상 범위: 85~115%"
          valueClass={ratioOk ? 'text-green-400' : 'text-red-400'}
        />
        <Card
          title={`올해 누적 발전량 (${curYear?.year ?? ''}년, ${curYear?.months_count ?? 0}개월)`}
          value={curYear ? `${fmt(curYear.site_8023 + curYear.site_8024)} kWh` : '-'}
          sub={yoy8023 !== null ? `전년비 ${S.site_8023}: ${yoy8023 > 0 ? '+' : ''}${fmt(yoy8023, 1)}%` : ''}
          valueClass={yoy8023 === null ? 'text-white' : yoy8023 >= 0 ? 'text-green-400' : 'text-red-400'}
        />
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700">
          <h2 className="font-semibold text-white">최근 12개월 발전량</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-xs border-b border-gray-700">
                <th className="px-5 py-3 text-left">월</th>
                <th className="px-5 py-3 text-right">{S.site_8023} (kWh)</th>
                <th className="px-5 py-3 text-right">{S.site_8024} (kWh)</th>
                <th className="px-5 py-3 text-right">비율</th>
                <th className="px-5 py-3 text-right">합계 (kWh)</th>
              </tr>
            </thead>
            <tbody>
              {monthly.slice(-12).reverse().map(row => {
                const abnormal = row.ratio !== null && Math.abs(row.ratio - 1) > 0.15
                return (
                  <tr key={row.key} className="border-b border-gray-700/40 hover:bg-gray-700/30 transition">
                    <td className="px-5 py-2.5 text-gray-300">{row.year}년 {row.month}월</td>
                    <td className="px-5 py-2.5 text-right text-blue-300">{fmt(row.site_8023)}</td>
                    <td className="px-5 py-2.5 text-right text-orange-300">{fmt(row.site_8024)}</td>
                    <td className={`px-5 py-2.5 text-right font-medium ${row.ratio === null ? 'text-gray-500' : abnormal ? 'text-red-400' : 'text-green-400'}`}>
                      {row.ratio !== null ? `${fmt(row.ratio * 100, 1)}%` : '-'}
                    </td>
                    <td className="px-5 py-2.5 text-right text-gray-300">{fmt(row.site_8023 + row.site_8024)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
