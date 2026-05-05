import { useState } from 'react'
import { useData } from './hooks/useData'
import { SITE_LABELS } from './utils/dataUtils'
import OverviewCards from './components/OverviewCards'
import DailyComparison from './components/DailyComparison'
import MonthlyTrend from './components/MonthlyTrend'
import AnnualAnalysis from './components/AnnualAnalysis'
import AnomalyDetection from './components/AnomalyDetection'

const TABS = [
  { id: 'overview', label: '개요' },
  { id: 'daily', label: '일별 비교' },
  { id: 'monthly', label: '월별 추이' },
  { id: 'annual', label: '연간 분석' },
  { id: 'anomaly', label: '이상 감지' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const { data, loading, error } = useData()

  if (loading) return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl mb-4">☀️</div>
        <p className="text-gray-300 text-lg">데이터 로딩 중...</p>
      </div>
    </div>
  )

  if (error) return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="text-center space-y-2">
        <p className="text-red-400 text-lg">데이터를 불러올 수 없습니다</p>
        <p className="text-gray-500 text-sm">{error}</p>
        <p className="text-gray-500 text-sm mt-3">
          <code className="bg-gray-800 px-2 py-1 rounded text-xs">python scripts/build_data.py</code> 를 먼저 실행하세요.
        </p>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-lg font-bold text-white">☀️ 태양광 발전 모니터링</h1>
          <p className="text-gray-400 text-xs mt-0.5">
            {SITE_LABELS.site_8023} · {SITE_LABELS.site_8024} · {data.length.toLocaleString()}개 레코드
          </p>
        </div>
      </header>

      <nav className="bg-gray-800 border-b border-gray-700 px-6">
        <div className="max-w-7xl mx-auto flex space-x-1 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {activeTab === 'overview' && <OverviewCards data={data} />}
        {activeTab === 'daily' && <DailyComparison data={data} />}
        {activeTab === 'monthly' && <MonthlyTrend data={data} />}
        {activeTab === 'annual' && <AnnualAnalysis data={data} />}
        {activeTab === 'anomaly' && <AnomalyDetection data={data} />}
      </main>
    </div>
  )
}
