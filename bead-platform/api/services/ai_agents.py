"""
Multi-agent AI orchestration for BEAD platform.

Agents:
- PlannerAgent   – reviews project timelines and resource plans
- RiskAgent      – identifies schedule, cost, and technical risks
- ComplianceAgent– checks BEAD grant compliance requirements

AIOrchestrator runs them in an AutoGPT-style loop, then synthesises an
executive recommendation via an LLM (OpenAI / Azure OpenAI).  When no LLM
key is configured the system falls back to a purely rule-based analysis.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..db import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _llm_complete(prompt: str) -> str:
    """Call the configured LLM and return the text response.

    Supports OpenAI and Azure OpenAI.  Falls back gracefully when neither
    is configured.
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        return ""

    try:
        import openai  # type: ignore

        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if azure_endpoint:
            client = openai.AzureOpenAI(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            )
            model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        else:
            client = openai.OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# ai_decision – public entry-point referenced in the problem statement
# ---------------------------------------------------------------------------

def ai_decision(context: str) -> str:
    """Generate an executive recommendation for the supplied risk context.

    If an LLM is configured the prompt is sent there; otherwise a concise
    rule-based summary is returned.
    """
    prompt = f"""
You are an IT Program Director overseeing a BEAD-funded broadband
infrastructure programme.

Analyse the following project risk context and provide a concise executive
recommendation (3-5 bullet points, plain English, no jargon):

{context}

Provide executive recommendation.
"""
    llm_response = _llm_complete(prompt)
    if llm_response:
        return llm_response

    # Rule-based fallback
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    bullets = [f"• {line}" for line in lines[:5]] if lines else ["• No specific risks identified."]
    return (
        "Executive summary (rule-based – configure OPENAI_API_KEY for LLM analysis):\n"
        + "\n".join(bullets)
    )


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------

class _BaseAgent:
    name: str = "BaseAgent"

    def _fetch_project_data(self) -> List[Dict[str, Any]]:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.status,
                    p.start_date,
                    p.end_date,
                    p.budget,
                    p.spent,
                    p.completion_percentage,
                    p.project_manager,
                    p.region,
                    p.fiber_miles_planned,
                    p.fiber_miles_completed,
                    p.locations_served,
                    COALESCE(SUM(e.amount), 0) AS total_expenditure,
                    COUNT(DISTINCT fr.id) AS route_count
                FROM projects p
                LEFT JOIN expenditures e ON p.id = e.project_id
                LEFT JOIN fiber_routes fr ON p.id = fr.project_id
                GROUP BY p.id
                LIMIT 50
                """
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]
            conn.close()
            return rows
        except Exception as exc:
            logger.error("%s: failed to fetch project data: %s", self.name, exc)
            return []

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# PlannerAgent
# ---------------------------------------------------------------------------

class PlannerAgent(_BaseAgent):
    """Reviews project timelines and resource allocation."""

    name = "PlannerAgent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        projects = self._fetch_project_data()
        findings: List[str] = []
        overdue: List[str] = []
        behind_schedule: List[str] = []

        today = datetime.now(timezone.utc).date()

        for p in projects:
            name = p.get("name") or p.get("id") or "Unknown"

            # Timeline analysis
            end_date = p.get("end_date")
            if end_date:
                try:
                    if hasattr(end_date, "date"):
                        end = end_date.date()
                    else:
                        end = datetime.fromisoformat(str(end_date)).date()
                    if end < today and (p.get("completion_percentage") or 0) < 100:
                        overdue.append(name)
                except Exception:
                    pass

            # Completion vs fibre miles
            planned = p.get("fiber_miles_planned") or 0
            completed_miles = p.get("fiber_miles_completed") or 0
            completion_pct = p.get("completion_percentage") or 0
            if planned > 0 and completed_miles / planned < completion_pct / 100 * 0.7:
                behind_schedule.append(name)

        if overdue:
            findings.append(f"⏰ {len(overdue)} project(s) past end date without 100% completion: {', '.join(overdue[:3])}.")
        if behind_schedule:
            findings.append(f"📉 {len(behind_schedule)} project(s) have fibre deployment lagging behind reported completion: {', '.join(behind_schedule[:3])}.")
        if not findings:
            findings.append("✅ All projects appear to be on schedule.")

        return {
            "agent": self.name,
            "findings": findings,
            "project_count": len(projects),
            "overdue_count": len(overdue),
            "behind_schedule_count": len(behind_schedule),
        }


# ---------------------------------------------------------------------------
# RiskAgent
# ---------------------------------------------------------------------------

class RiskAgent(_BaseAgent):
    """Identifies schedule, cost, and technical risks."""

    name = "RiskAgent"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        projects = self._fetch_project_data()
        risks: List[Dict[str, Any]] = []

        for p in projects:
            name = p.get("name") or p.get("id") or "Unknown"
            budget = float(p.get("budget") or 0)
            spent = float(p.get("spent") or p.get("total_expenditure") or 0)
            completion = float(p.get("completion_percentage") or 0)

            # Cost overrun risk
            if budget > 0:
                spend_ratio = spent / budget
                if spend_ratio > 0.9 and completion < 80:
                    risks.append({
                        "project": name,
                        "type": "COST",
                        "severity": "HIGH",
                        "detail": f"Budget {spend_ratio:.0%} consumed at only {completion:.0f}% completion.",
                    })
                elif spend_ratio > 0.75 and completion < 60:
                    risks.append({
                        "project": name,
                        "type": "COST",
                        "severity": "MEDIUM",
                        "detail": f"Budget {spend_ratio:.0%} consumed at {completion:.0f}% completion.",
                    })

            # Schedule risk (low completion, active project)
            status = (p.get("status") or "").lower()
            if status == "active" and completion < 20:
                risks.append({
                    "project": name,
                    "type": "SCHEDULE",
                    "severity": "MEDIUM",
                    "detail": f"Active project at only {completion:.0f}% completion.",
                })

            # Technical risk – no fibre routes recorded
            if (p.get("fiber_miles_planned") or 0) > 0 and (p.get("route_count") or 0) == 0:
                risks.append({
                    "project": name,
                    "type": "TECHNICAL",
                    "severity": "HIGH",
                    "detail": "No fibre routes recorded despite planned deployment.",
                })

        high_count = sum(1 for r in risks if r["severity"] == "HIGH")
        return {
            "agent": self.name,
            "risks": risks,
            "total_risks": len(risks),
            "high_severity": high_count,
            "summary": (
                f"Identified {len(risks)} risk(s) across {len(projects)} project(s). "
                f"{high_count} HIGH-severity item(s) require immediate attention."
                if risks
                else "✅ No significant risks detected."
            ),
        }


# ---------------------------------------------------------------------------
# ComplianceAgent
# ---------------------------------------------------------------------------

class ComplianceAgent(_BaseAgent):
    """Checks BEAD grant compliance requirements."""

    name = "ComplianceAgent"

    # Minimum required data fields per project
    _REQUIRED_FIELDS = ["name", "region", "project_manager", "start_date", "end_date", "budget"]

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        projects = self._fetch_project_data()
        flags: List[Dict[str, Any]] = []

        for p in projects:
            name = p.get("name") or p.get("id") or "Unknown"

            # Missing metadata
            missing = [f for f in self._REQUIRED_FIELDS if not p.get(f)]
            if missing:
                flags.append({
                    "project": name,
                    "type": "MISSING_DATA",
                    "severity": "MEDIUM",
                    "detail": f"Missing required BEAD reporting fields: {', '.join(missing)}.",
                })

            # Location tracking
            if (p.get("fiber_miles_planned") or 0) > 0 and (p.get("locations_served") or 0) == 0:
                flags.append({
                    "project": name,
                    "type": "COVERAGE_REPORTING",
                    "severity": "HIGH",
                    "detail": "No service locations recorded – required for BEAD eligibility reporting.",
                })

            # Spend without routes
            if (p.get("total_expenditure") or 0) > 0 and (p.get("route_count") or 0) == 0:
                flags.append({
                    "project": name,
                    "type": "AUDIT_TRAIL",
                    "severity": "MEDIUM",
                    "detail": "Expenditure recorded but no fibre routes documented.",
                })

        return {
            "agent": self.name,
            "flags": flags,
            "total_flags": len(flags),
            "high_severity": sum(1 for f in flags if f["severity"] == "HIGH"),
            "summary": (
                f"{len(flags)} compliance flag(s) found across {len(projects)} project(s)."
                if flags
                else "✅ All projects appear compliant."
            ),
        }


# ---------------------------------------------------------------------------
# AIOrchestrator – AutoGPT-style loop
# ---------------------------------------------------------------------------

class AIOrchestrator:
    """
    Coordinates Planner → Risk → Compliance agents in an iterative loop,
    then synthesises an executive recommendation.

    The 'AutoGPT-style' loop means each agent's output enriches the shared
    context that subsequent agents receive, and the orchestrator may make
    multiple reasoning passes if high-severity issues are found.
    """

    MAX_ITERATIONS = 3

    def __init__(self) -> None:
        self.agents: List[_BaseAgent] = [
            PlannerAgent(),
            RiskAgent(),
            ComplianceAgent(),
        ]

    # ------------------------------------------------------------------
    def run_analysis(self, extra_context: Optional[str] = None) -> Dict[str, Any]:
        """Execute the full multi-agent analysis and return structured results."""
        shared_context: Dict[str, Any] = {"extra": extra_context or ""}
        agent_results: List[Dict[str, Any]] = []

        iteration = 0
        needs_deeper_analysis = True

        while needs_deeper_analysis and iteration < self.MAX_ITERATIONS:
            iteration += 1
            logger.info("AIOrchestrator: iteration %d", iteration)

            for agent in self.agents:
                try:
                    result = agent.run(shared_context)
                    agent_results.append(result)
                    # Feed this agent's output into the shared context
                    shared_context[agent.name] = result
                    logger.info("%s completed with %d finding(s).", agent.name, len(result))
                except Exception as exc:
                    logger.error("%s raised an exception: %s", agent.name, exc)
                    agent_results.append({"agent": agent.name, "error": str(exc)})

            # Decide whether a second pass is worthwhile
            high_risks = shared_context.get("RiskAgent", {}).get("high_severity", 0)
            high_flags = shared_context.get("ComplianceAgent", {}).get("high_severity", 0)
            needs_deeper_analysis = iteration < 2 and (high_risks + high_flags) > 3

        # Build the executive recommendation
        recommendation = self._synthesise(shared_context)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "iterations": iteration,
            "agent_results": agent_results,
            "executive_recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    def _synthesise(self, ctx: Dict[str, Any]) -> str:
        """Build a natural-language executive recommendation from agent outputs."""
        # Collect key signals
        planner = ctx.get("PlannerAgent", {})
        risk = ctx.get("RiskAgent", {})
        compliance = ctx.get("ComplianceAgent", {})

        context_text = (
            f"Programme overview: {planner.get('project_count', 0)} projects, "
            f"{planner.get('overdue_count', 0)} overdue, "
            f"{planner.get('behind_schedule_count', 0)} behind schedule.\n"
            f"Risk summary: {risk.get('summary', 'N/A')}\n"
            f"Compliance summary: {compliance.get('summary', 'N/A')}\n"
        )

        if ctx.get("extra"):
            context_text += f"\nAdditional context: {ctx['extra']}"

        # Highest-severity risks
        top_risks = [r for r in risk.get("risks", []) if r.get("severity") == "HIGH"][:3]
        if top_risks:
            context_text += "\nTop risks:\n" + "\n".join(
                f"  - [{r['type']}] {r['project']}: {r['detail']}" for r in top_risks
            )

        # Highest-severity compliance flags
        top_flags = [f for f in compliance.get("flags", []) if f.get("severity") == "HIGH"][:3]
        if top_flags:
            context_text += "\nTop compliance flags:\n" + "\n".join(
                f"  - [{f['type']}] {f['project']}: {f['detail']}" for f in top_flags
            )

        # Planner findings
        for finding in planner.get("findings", [])[:3]:
            context_text += f"\nPlanner: {finding}"

        return ai_decision(context_text)


# Singleton orchestrator
orchestrator = AIOrchestrator()
