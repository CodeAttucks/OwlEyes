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

// ---------------------------------------------------------------------------
// KPI summary strip
// ---------------------------------------------------------------------------
function KPIStrip({ results }: { results: AgentResult[] }) {
  const risk = results.find((r) => r.agent === 'RiskAgent')
  const compliance = results.find((r) => r.agent === 'ComplianceAgent')
  const planner = results.find((r) => r.agent === 'PlannerAgent')

  const tiles = [
    {
      label: 'Total Projects',
      value: planner?.project_count ?? '—',
      colour: 'from-blue-500 to-blue-600',
    },
    {
      label: 'Overdue Projects',
      value: planner?.overdue_count ?? '—',
      colour: 'from-orange-500 to-orange-600',
    },
    {
      label: 'Risk Items',
      value: risk?.total_risks ?? '—',
      colour: 'from-red-500 to-red-600',
    },
    {
      label: 'High-Severity Risks',
      value: risk?.high_severity ?? '—',
      colour: 'from-rose-600 to-rose-700',
    },
    {
      label: 'Compliance Flags',
      value: compliance?.total_flags ?? '—',
      colour: 'from-purple-500 to-purple-600',
    },
    {
      label: 'Critical Flags',
      value: compliance?.high_severity ?? '—',
      colour: 'from-violet-600 to-violet-700',
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {tiles.map((t) => (
        <div
          key={t.label}
          className={`bg-gradient-to-br ${t.colour} rounded-xl p-4 text-white shadow`}
        >
          <p className="text-xs font-medium opacity-80 uppercase tracking-wide">{t.label}</p>
          <p className="text-3xl font-bold mt-1">{t.value}</p>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Alert control panel
// ---------------------------------------------------------------------------
function AlertPanel() {
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
      setMessage('Test alert failed — check API connectivity.')
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
      setMessage('Alert broadcast sent.')
      setBroadcastMsg('')
    } catch {
      setMessage('Broadcast failed — check webhook configuration.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow p-6 space-y-4">
      <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
        <span>🔔</span> Alert Integrations
      </h2>

      {/* Channel status */}
      <div className="flex gap-4">
        {[
          { key: 'slack', label: 'Slack', icon: '💬' },
          { key: 'teams', label: 'Teams', icon: '🟦' },
        ].map(({ key, label, icon }) => {
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
              {label}
              {status !== null && (
                <span>{ok ? '✓' : '⚠ not configured'}</span>
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
        {sending ? '⏳ Sending…' : '📡 Send Test Alert'}
      </button>

      {/* Broadcast */}
      <div className="border-t pt-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-700">Broadcast Custom Alert</h3>
        <textarea
          value={broadcastMsg}
          onChange={(e) => setBroadcastMsg(e.target.value)}
          rows={2}
          placeholder="Enter alert message…"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
        />
        <div className="flex items-center gap-3">
          <select
            value={broadcastSeverity}
            onChange={(e) => setBroadcastSeverity(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="info">Info</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
          <button
            onClick={handleBroadcast}
            disabled={sending || !broadcastMsg.trim()}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 disabled:opacity-50 transition-colors"
          >
            {sending ? '⏳ Sending…' : '📣 Broadcast'}
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
              <span>🦉</span> AI Executive Dashboard
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Multi-agent analysis · Planner · Risk · Compliance
            </p>
          </div>
          <a
            href="/dashboard"
            className="text-sm text-indigo-600 hover:text-indigo-500 font-medium"
          >
            ← Back to Dashboard
          </a>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Run analysis controls */}
        <div className="bg-white rounded-xl shadow p-6 space-y-4">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <span>🤖</span> Run Multi-Agent Analysis
          </h2>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={extraContext}
              onChange={(e) => setExtraContext(e.target.value)}
              placeholder="Optional: add extra context for the AI (e.g. 'Q3 budget freeze')"
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
                  Running agents…
                </>
              ) : (
                '▶ Run Analysis'
              )}
            </button>
          </div>
          <p className="text-xs text-gray-400">
            Executes Planner → Risk → Compliance agents in sequence, then synthesises an
            executive recommendation. High-severity findings are automatically broadcast to
            configured Slack / Teams channels.
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
