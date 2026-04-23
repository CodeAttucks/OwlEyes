'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  AIAnalysisResult,
  AgentResult,
  runAIAnalysis,
  fetchLatestAIDecisions,
  testAlerts,
  broadcastAlert,
} from '../../lib/api'
import AIDecision from '../../components/AIDecision'
import { useI18n } from '../../lib/i18n'
import LanguageSwitcher from '../../components/LanguageSwitcher'

// ---------------------------------------------------------------------------
// KPI summary strip
// ---------------------------------------------------------------------------
function KPIStrip({ results }: { results: AgentResult[] }) {
  const { t, formatNumber } = useI18n()
  const risk = results.find((r) => r.agent === 'RiskAgent')
  const compliance = results.find((r) => r.agent === 'ComplianceAgent')
  const planner = results.find((r) => r.agent === 'PlannerAgent')

  const tiles = [
    {
      label: t('aiDashboard.kpi.totalProjects'),
      value: planner?.project_count != null ? formatNumber(planner.project_count) : '—',
      colour: 'from-blue-500 to-blue-600',
    },
    {
      label: t('aiDashboard.kpi.overdueProjects'),
      value: planner?.overdue_count != null ? formatNumber(planner.overdue_count) : '—',
      colour: 'from-orange-500 to-orange-600',
    },
    {
      label: t('aiDashboard.kpi.riskItems'),
      value: risk?.total_risks != null ? formatNumber(risk.total_risks) : '—',
      colour: 'from-red-500 to-red-600',
    },
    {
      label: t('aiDashboard.kpi.highSeverityRisks'),
      value: risk?.high_severity != null ? formatNumber(risk.high_severity) : '—',
      colour: 'from-rose-600 to-rose-700',
    },
    {
      label: t('aiDashboard.kpi.complianceFlags'),
      value: compliance?.total_flags != null ? formatNumber(compliance.total_flags) : '—',
      colour: 'from-purple-500 to-purple-600',
    },
    {
      label: t('aiDashboard.kpi.criticalFlags'),
      value: compliance?.high_severity != null ? formatNumber(compliance.high_severity) : '—',
      colour: 'from-violet-600 to-violet-700',
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {tiles.map((tile) => (
        <div
          key={tile.label}
          className={`bg-gradient-to-br ${tile.colour} rounded-xl p-4 text-white shadow`}
        >
          <p className="text-xs font-medium opacity-80 uppercase tracking-wide">{tile.label}</p>
          <p className="text-3xl font-bold mt-1">{tile.value}</p>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Alert control panel
// ---------------------------------------------------------------------------
function AlertPanel() {
  const { t } = useI18n()
  const [status, setStatus] = useState<Record<string, boolean> | null>(null)
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [broadcastMsg, setBroadcastMsg] = useState('')
  const [broadcastSeverity, setBroadcastSeverity] = useState('info')

  const handleTest = async () => {
    setSending(true)
    try {
      const res = await testAlerts()
      setStatus(res.channels)
      setMessage(res.message)
    } catch {
      setMessage(t('aiDashboard.alerts.testFailed'))
    } finally {
      setSending(false)
    }
  }

  const handleBroadcast = async () => {
    if (!broadcastMsg.trim()) return
    setSending(true)
    try {
      const res = await broadcastAlert({
        title: '🦉 BEAD Platform Alert',
        message: broadcastMsg,
        severity: broadcastSeverity,
      })
      setStatus(res.channels)
      setMessage(t('aiDashboard.alerts.broadcastSent'))
      setBroadcastMsg('')
    } catch {
      setMessage(t('aiDashboard.alerts.broadcastFailed'))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow p-6 space-y-4">
      <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
        <span>🔔</span> {t('aiDashboard.alerts.title')}
      </h2>

      {/* Channel status */}
      <div className="flex gap-4">
        {[
          { key: 'slack', labelKey: 'aiDashboard.alerts.slack', icon: '💬' },
          { key: 'teams', labelKey: 'aiDashboard.alerts.teams', icon: '🟦' },
        ].map(({ key, labelKey, icon }) => {
          const ok = status?.[key]
          return (
            <div
              key={key}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium ${
                status === null
                  ? 'border-gray-200 text-gray-400 bg-gray-50'
                  : ok
                  ? 'border-green-200 text-green-700 bg-green-50'
                  : 'border-yellow-200 text-yellow-700 bg-yellow-50'
              }`}
            >
              <span>{icon}</span>
              {t(labelKey)}
              {status !== null && (
                <span>{ok ? '✓' : t('aiDashboard.alerts.notConfigured')}</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Test button */}
      <button
        onClick={handleTest}
        disabled={sending}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 text-white text-sm font-medium hover:bg-gray-700 disabled:opacity-50 transition-colors"
      >
        {sending ? t('common.sending') : t('aiDashboard.alerts.sendTest')}
      </button>

      {/* Broadcast */}
      <div className="border-t pt-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-700">{t('aiDashboard.alerts.broadcastTitle')}</h3>
        <textarea
          value={broadcastMsg}
          onChange={(e) => setBroadcastMsg(e.target.value)}
          rows={2}
          placeholder={t('aiDashboard.alerts.messagePlaceholder')}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
        />
        <div className="flex items-center gap-3">
          <select
            value={broadcastSeverity}
            onChange={(e) => setBroadcastSeverity(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="info">{t('aiDashboard.alerts.severityInfo')}</option>
            <option value="low">{t('aiDashboard.alerts.severityLow')}</option>
            <option value="medium">{t('aiDashboard.alerts.severityMedium')}</option>
            <option value="high">{t('aiDashboard.alerts.severityHigh')}</option>
          </select>
          <button
            onClick={handleBroadcast}
            disabled={sending || !broadcastMsg.trim()}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 transition-colors"
          >
            {sending ? t('common.sending') : t('aiDashboard.alerts.broadcast')}
          </button>
        </div>
      </div>

      {message && (
        <p className="text-sm text-gray-600 bg-gray-50 rounded px-3 py-2">{message}</p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function AIDashboard() {
  const [analysis, setAnalysis] = useState<AIAnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [extraContext, setExtraContext] = useState('')
  const [error, setError] = useState<string | null>(null)
  const { t } = useI18n()

  // Load latest cached result on mount
  useEffect(() => {
    fetchLatestAIDecisions()
      .then(setAnalysis)
      .catch(() => setAnalysis(null))
      .finally(() => setLoading(false))
  }, [])

  const handleRunAnalysis = useCallback(async () => {
    setRunning(true)
    setError(null)
    try {
      const result = await runAIAnalysis(extraContext || undefined)
      setAnalysis(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setRunning(false)
    }
  }, [extraContext])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <span>🦉</span> {t('aiDashboard.title')}
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {t('aiDashboard.subtitle')}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <a
              href="/dashboard"
              className="text-sm text-indigo-600 hover:text-indigo-500 font-medium"
            >
              {t('nav.backToDashboard')}
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Run analysis controls */}
        <div className="bg-white rounded-xl shadow p-6 space-y-4">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <span>🤖</span> {t('aiDashboard.runAnalysis.title')}
          </h2>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={extraContext}
              onChange={(e) => setExtraContext(e.target.value)}
              placeholder={t('aiDashboard.runAnalysis.contextPlaceholder')}
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <button
              onClick={handleRunAnalysis}
              disabled={running}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-500 disabled:opacity-50 transition-colors shadow"
            >
              {running ? (
                <>
                  <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  {t('aiDashboard.runAnalysis.runningButton')}
                </>
              ) : (
                t('aiDashboard.runAnalysis.runButton')
              )}
            </button>
          </div>
          <p className="text-xs text-gray-400">
            {t('aiDashboard.runAnalysis.description')}
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 rounded-xl px-5 py-4 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="bg-white rounded-xl shadow p-6 animate-pulse space-y-4">
            <div className="h-5 bg-gray-200 rounded w-48" />
            <div className="grid grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-32 bg-gray-100 rounded-xl" />
              ))}
            </div>
          </div>
        )}

        {/* KPI strip */}
        {!loading && analysis?.agent_results && analysis.agent_results.length > 0 && (
          <KPIStrip results={analysis.agent_results} />
        )}

        {/* Agent results + recommendation */}
        {!loading && analysis && <AIDecision data={analysis} />}

        {/* Alert panel */}
        <AlertPanel />
      </main>
    </div>
  )
}
