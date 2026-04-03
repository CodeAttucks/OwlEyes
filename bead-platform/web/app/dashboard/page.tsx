'use client'

import { useState, useEffect } from 'react'
import { fetchProjects, fetchFiberRoutes, fetchReports } from '../../lib/api'
import { useI18n } from '../../lib/i18n'
import LanguageSwitcher from '../../components/LanguageSwitcher'

interface Project {
  id: string
  name: string
  state: string
  status: string
}

interface FiberRoute {
  id: number
  project_id: string
  geometry: string
  miles: number
}

interface FiberStats {
  total_routes: number
  total_miles: number
  average_miles: number
}

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [fiberRoutes, setFiberRoutes] = useState<FiberRoute[]>([])
  const [stats, setStats] = useState<FiberStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { t, formatNumber } = useI18n()

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const [projectsData, fiberData, reportsData] = await Promise.all([
          fetchProjects(),
          fetchFiberRoutes(),
          fetchReports()
        ])
        
        setProjects(projectsData.projects || [])
        setFiberRoutes(fiberData.routes || [])
        
        // Calculate stats
        if (fiberData.routes && fiberData.routes.length > 0) {
          const totalMiles = fiberData.routes.reduce((sum: number, route: FiberRoute) => sum + (route.miles || 0), 0)
          setStats({
            total_routes: fiberData.routes.length,
            total_miles: totalMiles,
            average_miles: totalMiles / fiberData.routes.length
          })
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl font-semibold">{t('dashboard.loadingDashboard')}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="md:flex md:items-center md:justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{t('dashboard.title')}</h1>
            <p className="mt-2 text-gray-600">{t('dashboard.subtitle')}</p>
          </div>
          <div className="mt-4 md:mt-0 flex items-center gap-3">
            <LanguageSwitcher />
            <a
              href="/ai-dashboard"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-500 transition-colors shadow"
            >
              🦉 {t('nav.aiDashboard')}
            </a>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-gray-500 text-sm font-medium uppercase">{t('dashboard.stats.totalRoutes')}</div>
              <div className="text-3xl font-bold text-gray-900 mt-2">{formatNumber(stats.total_routes)}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-gray-500 text-sm font-medium uppercase">{t('dashboard.stats.totalMiles')}</div>
              <div className="text-3xl font-bold text-gray-900 mt-2">{formatNumber(stats.total_miles, { maximumFractionDigits: 2 })}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-gray-500 text-sm font-medium uppercase">{t('dashboard.stats.averageMiles')}</div>
              <div className="text-3xl font-bold text-gray-900 mt-2">{formatNumber(stats.average_miles, { maximumFractionDigits: 2 })}</div>
            </div>
          </div>
        )}

        {/* Projects Section */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">{t('dashboard.projects.title')}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">{t('dashboard.projects.columnName')}</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">{t('dashboard.projects.columnState')}</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">{t('dashboard.projects.columnStatus')}</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">{t('dashboard.projects.columnRoutes')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {projects.length > 0 ? (
                  projects.map((project) => (
                    <tr key={project.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900">{project.name}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{project.state}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          project.status === 'active' 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {project.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {fiberRoutes.filter(r => r.project_id === project.id).length}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-6 py-4 text-center text-gray-500">
                      {t('dashboard.projects.noProjects')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Fiber Routes Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">{t('dashboard.fiberRoutes.title')}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">{t('dashboard.fiberRoutes.columnRouteId')}</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">{t('dashboard.fiberRoutes.columnProjectId')}</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">{t('dashboard.fiberRoutes.columnMiles')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {fiberRoutes.length > 0 ? (
                  fiberRoutes.map((route) => (
                    <tr key={route.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900">{route.id}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{route.project_id}</td>
                      <td className="px-6 py-4 text-sm text-gray-600">{route.miles}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={3} className="px-6 py-4 text-center text-gray-500">
                      {t('dashboard.fiberRoutes.noRoutes')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}