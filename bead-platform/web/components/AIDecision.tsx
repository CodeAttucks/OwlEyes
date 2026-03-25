'use client'

import { AgentResult, AIAnalysisResult } from '../lib/api'

// ---------------------------------------------------------------------------
// Severity badge
// ---------------------------------------------------------------------------
function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    HIGH: 'bg-red-100 text-red-800 border-red-200',
    MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    LOW: 'bg-green-100 text-green-800 border-green-200',
  }
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${
        map[severity.toUpperCase()] ?? 'bg-gray-100 text-gray-700 border-gray-200'
      }`}
    >
      {severity}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Single agent card
// ---------------------------------------------------------------------------
function AgentCard({ result }: { result: AgentResult }) {
  const agentColour: Record<string, string> = {
    PlannerAgent: 'border-blue-400 bg-blue-50',
    RiskAgent: 'border-red-400 bg-red-50',
    ComplianceAgent: 'border-purple-400 bg-purple-50',
  }
  const agentIcon: Record<string, string> = {
    PlannerAgent: '📋',
    RiskAgent: '⚠️',
    ComplianceAgent: '🛡️',
  }
  const colour = agentColour[result.agent] ?? 'border-gray-300 bg-gray-50'
  const icon = agentIcon[result.agent] ?? '🤖'

  const items =
    result.risks ?? result.flags ?? result.findings?.map((f) => ({ detail: f })) ?? []
  const highCount = result.high_severity ?? 0

  return (
    <div className={`rounded-xl border-l-4 p-5 ${colour} flex flex-col gap-3`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-gray-900 flex items-center gap-2">
          <span>{icon}</span>
          {result.agent}
        </h3>
        {highCount > 0 && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-600 text-white text-xs font-bold">
            {highCount} HIGH
          </span>
        )}
      </div>

      {/* Error state */}
      {result.error && (
        <p className="text-sm text-red-700 bg-red-100 rounded px-3 py-2">{result.error}</p>
      )}

      {/* Summary */}
      {result.summary && (
        <p className="text-sm text-gray-700">{result.summary}</p>
      )}

      {/* Item list */}
      {items.length > 0 && (
        <ul className="space-y-2">
          {(items as Array<Record<string, string>>).slice(0, 5).map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              {'severity' in item && <SeverityBadge severity={item.severity} />}
              <span className="text-gray-700 flex-1">
                {'project' in item && (
                  <span className="font-medium text-gray-900">{item.project}: </span>
                )}
                {item.detail}
              </span>
            </li>
          ))}
        </ul>
      )}

      {/* Stats row for PlannerAgent */}
      {result.agent === 'PlannerAgent' && result.project_count !== undefined && (
        <div className="flex gap-4 text-xs text-gray-600 pt-1">
          <span>📁 {result.project_count} projects</span>
          <span>⏰ {result.overdue_count ?? 0} overdue</span>
          <span>📉 {result.behind_schedule_count ?? 0} behind</span>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Executive recommendation panel
// ---------------------------------------------------------------------------
function ExecutiveRecommendation({ text }: { text: string }) {
  const lines = text.split('\n').filter(Boolean)
  return (
    <div className="rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white p-6">
      <h3 className="text-lg font-bold text-indigo-900 mb-4 flex items-center gap-2">
        <span>🦉</span> Executive Recommendation
      </h3>
      <div className="space-y-2">
        {lines.map((line, i) => (
          <p key={i} className="text-sm text-gray-800 leading-relaxed">
            {line}
          </p>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------
interface AIDecisionProps {
  data: AIAnalysisResult
}

export default function AIDecision({ data }: AIDecisionProps) {
  const ts = data.timestamp ? new Date(data.timestamp).toLocaleString() : null
  const hasResults = data.agent_results && data.agent_results.length > 0

  return (
    <div className="space-y-6">
      {/* Meta row */}
      {ts && (
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>🕐 Analysis run at {ts}</span>
          {data.iterations !== undefined && (
            <span>• {data.iterations} orchestration iteration{data.iterations !== 1 ? 's' : ''}</span>
          )}
        </div>
      )}

      {/* "No analysis yet" */}
      {!hasResults && (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-gray-500">
          <p className="text-4xl mb-3">🤖</p>
          <p className="font-medium">No analysis has been run yet.</p>
          <p className="text-sm mt-1">Click <strong>Run Analysis</strong> to start the multi-agent pipeline.</p>
        </div>
      )}

      {/* Agent cards */}
      {hasResults && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.agent_results.map((r, i) => (
            <AgentCard key={i} result={r} />
          ))}
        </div>
      )}

      {/* Executive recommendation */}
      {data.executive_recommendation && (
        <ExecutiveRecommendation text={data.executive_recommendation} />
      )}
    </div>
  )
}
