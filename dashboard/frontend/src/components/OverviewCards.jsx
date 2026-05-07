import { useMemo } from 'react'
import { getMonthlyTotals, getAnnualTotals, getLatestDay, getLastNDays, getKSTTargetDate, SITE_LABELS, fmt } from '../utils/dataUtils'

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
  const kstTarget = useMemo(() => getKSTTargetDate(), [])
  const latestDay = useMemo(() => getLatestDay(data, kstTarget.dateStr), [data, kstTarget])
  const last10Days = useMemo(() => getLastNDays(data, 10, kstTarget.dateStr), [data, kstTarget])

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
  const hours8023 = latestDay?.hours_8023 ?? null
  const hours8024 = latestDay?.hours_8024 ?? null

  const todayStr = `${kstTarget.year}년 ${kstTarget.month}월 ${kstTarget.day}일`

  const dayLabel = useMemo(() => {
    if (!latestDay) return ''
    const { year, month, day } = latestDay
    const base = `${year}년 ${month}월 ${day}일`
    if (year === kstTarget.year && month === kstTarget.month && day === kstTarget.day) return `${base} (오늘)`
    const prev = new Date(Date.UTC(kstTarget.year, kstTarget.month - 1, kstTarget.day - 1))
    if (year === prev.getUTCFullYear() && month === prev.getUTCMonth() + 1 && day === prev.getUTCDate()) return `${base} (어제)`
    return base
  }, [latestDay, kstTarget])

  const isLatestToday = latestDay?.year === kstTarget.year
    && latestDay?.month === kstTarget.month
    && latestDay?.day === kstTarget.day

  return (
    <div className="space-y-5">
      <p className="text-gray-400 text-sm">
        오늘: <span className="text-white font-medium">{todayStr}</span>
        {dayLabel && !isLatestToday && (
          <span className="ml-3 text-gray-500">최신 데이터: {dayLabel}</span>
        )}
      </p>

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
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-700">
          <h2 className="font-semibold text-white text-sm sm:text-base">최근 10일 발전량</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs sm:text-sm">
            <thead>
              <tr className="text-gray-400 text-xs border-b border-gray-700">
                <th className="px-3 sm:px-5 py-3 text-left">날짜</th>
                <th className="px-3 sm:px-5 py-3 text-right">{S.site_8023} (kWh)</th>
                <th className="px-3 sm:px-5 py-3 text-right">{S.site_8024} (kWh)</th>
                <th className="px-3 sm:px-5 py-3 text-right">비율</th>
              </tr>
            </thead>
            <tbody>
              {last10Days.map(row => {
                const abnormal = row.ratio !== null && Math.abs(row.ratio - 1) > 0.15
                const isToday = row.year === kstTarget.year && row.month === kstTarget.month && row.day === kstTarget.day
                return (
                  <tr key={row.date} className={`border-b border-gray-700/40 hover:bg-gray-700/30 transition ${isToday ? 'bg-gray-700/20' : ''}`}>
                    <td className="px-3 sm:px-5 py-2 text-gray-300 whitespace-nowrap">
                      {row.month}월 {row.day}일
                      {isToday && <span className="ml-1 text-gray-500 text-xs">(오늘)</span>}
                    </td>
                    <td className="px-3 sm:px-5 py-2 text-right text-blue-300">{fmt(row.site_8023, 1)}</td>
                    <td className="px-3 sm:px-5 py-2 text-right text-orange-300">{fmt(row.site_8024, 1)}</td>
                    <td className={`px-3 sm:px-5 py-2 text-right font-medium ${row.ratio === null ? 'text-gray-500' : abnormal ? 'text-red-400' : 'text-green-400'}`}>
                      {row.ratio !== null ? `${fmt(row.ratio * 100, 1)}%` : '-'}
                    </td>
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
