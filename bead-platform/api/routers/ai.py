"""
AI orchestration endpoints.

Routes:
  POST /ai/analyze           – run the full multi-agent analysis
  GET  /ai/decisions/latest  – return the most recent analysis result
  POST /ai/alerts/test       – send a test alert to all configured channels
  POST /ai/alerts/broadcast  – broadcast a custom alert
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from services.ai_agents import orchestrator, ai_decision
from services.alert_service import alert_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# In-memory cache for the most recent analysis (process-scoped)
_latest_result: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    context: Optional[str] = None


class BroadcastRequest(BaseModel):
    title: str
    message: str
    severity: str = "info"
    extra: Optional[Dict[str, str]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/analyze")
def analyze(request: AnalyzeRequest = Body(default=AnalyzeRequest())) -> Dict[str, Any]:
    """Run the full Planner → Risk → Compliance agent pipeline and return an
    executive recommendation.  Results are cached for the /decisions/latest
    endpoint.
    """
    global _latest_result
    try:
        result = orchestrator.run_analysis(extra_context=request.context)
        _latest_result = result

        # Auto-broadcast high-severity findings
        risk_data = next(
            (r for r in result.get("agent_results", []) if r.get("agent") == "RiskAgent"), {}
        )
        if risk_data.get("high_severity", 0) > 0:
            alert_service.broadcast(
                title="🚨 BEAD Platform: High-Severity Risks Detected",
                message=risk_data.get("summary", "High-severity risks detected in BEAD projects."),
                severity="high",
                extra={"Iterations": str(result.get("iterations", 1))},
            )

        return result
    except Exception as exc:
        logger.error("AI analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/decisions/latest")
def get_latest_decisions() -> Dict[str, Any]:
    """Return the most recent AI analysis result, or a prompt to run /analyze
    if no analysis has been performed yet.
    """
    if _latest_result is None:
        return {
            "message": "No analysis has been run yet. POST to /ai/analyze to start.",
            "agent_results": [],
            "executive_recommendation": None,
        }
    return _latest_result


@router.post("/decision")
def decision(context: str = Body(..., embed=True)) -> Dict[str, str]:
    """Generate a single executive AI decision for the supplied context string.

    This is the direct `ai_decision(context)` entry-point exposed as a REST
    endpoint.
    """
    try:
        recommendation = ai_decision(context)
        return {"recommendation": recommendation}
    except Exception as exc:
        logger.error("ai_decision error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/alerts/test")
def test_alerts() -> Dict[str, Any]:
    """Send a test notification to all configured alert channels.

    Returns a dict indicating which channels succeeded.
    """
    results = alert_service.broadcast(
        title="🦉 OwlEyes – Test Alert",
        message="This is a test notification from the BEAD Platform AI system.",
        severity="info",
        extra={"Source": "OwlEyes BEAD Platform", "Type": "Test"},
    )
    configured = {k: v for k, v in results.items()}
    return {"channels": configured, "message": "Test alerts dispatched to all configured channels."}


@router.post("/alerts/broadcast")
def broadcast_alert(request: BroadcastRequest) -> Dict[str, Any]:
    """Send a custom alert to all configured channels (Slack + Teams)."""
    try:
        results = alert_service.broadcast(
            title=request.title,
            message=request.message,
            severity=request.severity,
            extra=request.extra,
        )
        return {"channels": results}
    except Exception as exc:
        logger.error("Broadcast error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
