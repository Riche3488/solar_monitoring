import { useMemo } from 'react'
import { getMonthlyTotals, getAnnualTotals, getLatestDay, SITE_LABELS, fmt } from '../utils/dataUtils'

const RATED_KW = 99.5
const S = SITE_LABELS

function Card({ title, value, sub, valueClass = 'text-white' }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
      <p className="text-gray-400 text-xs mb-1 leading-tight">{title}</p>
      <p className={`text-xl sm:text-2xl font-bold ${valueClass}`}>{value}</p>
      {sub && <p className="text-gray-500 text-xs mt-1">{sub}</p>}
    </div>
  )
}

export default function OverviewCards({ data }) {
  const monthly = useMemo(() => getMonthlyTotals(data), [data])
  const annual = useMemo(() => getAnnualTotals(data), [data])
  const latestDay = useMemo(() => getLatestDay(data), [data])

  const latestMonthly = monthly[monthly.length - 1]
  const curYear = annual[annual.length - 1]
  const prevYear = annual[annual.length - 2]

  const yoy8023 = curYear && prevYear && prevYear.site_8023 > 0
    ? ((curYear.site_8023 - prevYear.site_8023) / prevYear.site_8023) * 100
    : null

  const ratioOk = latestMonthly?.ratio !== null && latestMonthly?.ratio !== undefined
    && Math.abs(latestMonthly.ratio - 1) < 0.15

  const kwh8023 = latestDay?.site_8023 ?? null
  const kwh8024 = latestDay?.site_8024 ?? null
  const hours8023 = kwh8023 !== null ? kwh8023 / RATED_KW : null
  const hours8024 = kwh8024 !== null ? kwh8024 / RATED_KW : null

  const dayLabel = latestDay
    ? `${latestDay.year}년 ${latestDay.month}월 ${latestDay.day}일`
    : ''

  return (
    <div className="space-y-5">
      {dayLabel && (
        <p className="text-gray-400 text-sm">
          최신 데이터: <span className="text-white font-medium">{dayLabel}</span>
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 sm:gap-4">
        <Card
          title={`${S.site_8023} 발전량`}
          value={kwh8023 !== null ? `${fmt(kwh8023, 1)} kWh` : '-'}
          sub={hours8023 !== null ? `발전시간 ${fmt(hours8023, 1)}h` : undefined}
          valueClass="text-blue-400"
        />
        <Card
          title={`${S.site_8024} 발전량`}
          value={kwh8024 !== null ? `${fmt(kwh8024, 1)} kWh` : '-'}
          sub={hours8024 !== null ? `발전시간 ${fmt(hours8024, 1)}h` : undefined}
          valueClass="text-orange-400"
        />
        <Card
          title={`이번 달 비율${latestMonthly ? ` · ${latestMonthly.year}년 ${latestMonthly.month}월` : ''}`}
          value={latestMonthly?.ratio !== null && latestMonthly?.ratio !== undefined
            ? `${fmt(latestMonthly.ratio * 100, 1)}%`
            : '-'}
          sub="정상 범위: 85~115%"
          valueClass={ratioOk ? 'text-green-400' : 'text-red-400'}
        />
        <Card
          title={`올해 누적 (${curYear?.year ?? ''}년, ${curYear?.months_count ?? 0}개월)`}
          value={curYear ? `${fmt(curYear.site_8023 + curYear.site_8024)} kWh` : '-'}
          sub={yoy8023 !== null
            ? `전년비 ${S.site_8023}: ${yoy8023 > 0 ? '+' : ''}${fmt(yoy8023, 1)}%`
            : ''}
          valueClass={yoy8023 === null ? 'text-white' : yoy8023 >= 0 ? 'text-green-400' : 'text-red-400'}
        />
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-700">
          <h2 className="font-semibold text-white text-sm sm:text-base">최근 12개월 발전량</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs sm:text-sm">
            <thead>
              <tr className="text-gray-400 text-xs border-b border-gray-700">
                <th className="px-3 sm:px-5 py-3 text-left">월</th>
                <th className="px-3 sm:px-5 py-3 text-right">{S.site_8023}</th>
                <th className="px-3 sm:px-5 py-3 text-right">{S.site_8024}</th>
                <th className="px-3 sm:px-5 py-3 text-right">비율</th>
                <th className="hidden sm:table-cell px-5 py-3 text-right">합계 (kWh)</th>
              </tr>
            </thead>
            <tbody>
              {monthly.slice(-12).reverse().map(row => {
                const abnormal = row.ratio !== null && Math.abs(row.ratio - 1) > 0.15
                return (
                  <tr key={row.key} className="border-b border-gray-700/40 hover:bg-gray-700/30 transition">
                    <td className="px-3 sm:px-5 py-2 text-gray-300 whitespace-nowrap">{row.year}년 {row.month}월</td>
                    <td className="px-3 sm:px-5 py-2 text-right text-blue-300">{fmt(row.site_8023)}</td>
                    <td className="px-3 sm:px-5 py-2 text-right text-orange-300">{fmt(row.site_8024)}</td>
                    <td className={`px-3 sm:px-5 py-2 text-right font-medium ${row.ratio === null ? 'text-gray-500' : abnormal ? 'text-red-400' : 'text-green-400'}`}>
                      {row.ratio !== null ? `${fmt(row.ratio * 100, 1)}%` : '-'}
                    </td>
                    <td className="hidden sm:table-cell px-5 py-2 text-right text-gray-300">{fmt(row.site_8023 + row.site_8024)}</td>
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
