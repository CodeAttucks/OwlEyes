'use client'

import { useEffect, useState } from 'react'
import { CheckCircleIcon, ExclamationIcon, SparklesIcon } from '@heroicons/react/outline'

interface InsightData {
  cost_per_location: number
  total_projects: number
  total_locations: number
  total_miles: number
  coverage_percent: number
  insights: string[]
}

const iconMap: Record<string, React.ReactNode> = {
  '⚠️': <ExclamationIcon className="w-5 h-5 text-yellow-500" />,
  '✅': <CheckCircleIcon className="w-5 h-5 text-green-500" />,
  '🎯': <SparklesIcon className="w-5 h-5 text-blue-500" />
}

export default function Insights() {
  const [data, setData] = useState<InsightData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/reports/insights`)
        if (!res.ok) throw new Error('Failed to fetch insights')
        const result = await res.json()
        setData(result)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchInsights()
  }, [])

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-xl shadow animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-32 mb-4"></div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 p-6 rounded-xl shadow border border-red-200">
        <h2 className="font-bold text-red-900 mb-2">Error Loading Insights</h2>
        <p className="text-red-700 text-sm">{error}</p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <SparklesIcon className="w-6 h-6 text-blue-600" />
          AI Insights & Analytics
        </h2>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg">
          <p className="text-xs text-gray-600 uppercase tracking-wide">Cost/Location</p>
          <p className="text-2xl font-bold text-blue-900 mt-1">${data.cost_per_location.toLocaleString()}</p>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg">
          <p className="text-xs text-gray-600 uppercase tracking-wide">Projects</p>
          <p className="text-2xl font-bold text-green-900 mt-1">{data.total_projects}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg">
          <p className="text-xs text-gray-600 uppercase tracking-wide">Locations</p>
          <p className="text-2xl font-bold text-purple-900 mt-1">{data.total_locations.toLocaleString()}</p>
        </div>
        <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-lg">
          <p className="text-xs text-gray-600 uppercase tracking-wide">Fiber Miles</p>
          <p className="text-2xl font-bold text-orange-900 mt-1">{data.total_miles.toLocaleString()}</p>
        </div>
        <div className="bg-gradient-to-br from-red-50 to-red-100 p-4 rounded-lg">
          <p className="text-xs text-gray-600 uppercase tracking-wide">Coverage</p>
          <p className="text-2xl font-bold text-red-900 mt-1">{data.coverage_percent}%</p>
        </div>
      </div>

      {/* Insights List */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-4">Key Observations</h3>
        <ul className="space-y-3">
          {data.insights.map((insight, idx) => (
            <li
              key={idx}
              className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
            >
              <div className="flex-shrink-0 mt-0.5">
                {insight.includes('⚠️') && <ExclamationIcon className="w-5 h-5 text-yellow-500" />}
                {insight.includes('✅') && <CheckCircleIcon className="w-5 h-5 text-green-500" />}
                {insight.includes('🎯') && <SparklesIcon className="w-5 h-5 text-blue-500" />}
                {!['⚠️', '✅', '🎯'].some(emoji => insight.includes(emoji)) && (
                  <SparklesIcon className="w-5 h-5 text-gray-400" />
                )}
              </div>
              <span className="text-sm text-gray-700">
                {insight.replace(/^[⚠️✅🎯🛣️📈🚀📊] /, '')}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}