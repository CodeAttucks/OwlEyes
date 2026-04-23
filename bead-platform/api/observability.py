from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_llmobs_configured = False


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def configure_llm_observability() -> None:
    """Enable Datadog LLM Observability when configured.

    This is intentionally optional. If `ddtrace` is not installed or the
    required Datadog environment variables are missing, the API continues to
    run without telemetry.
    """
    global _llmobs_configured

    if _llmobs_configured:
        return

    if not _as_bool(os.getenv("DD_LLMOBS_ENABLED"), default=False):
        return

    api_key = os.getenv("DD_API_KEY")
    if not api_key:
        logger.warning("Datadog LLM Observability requested, but DD_API_KEY is not set.")
        return

    try:
        from ddtrace import patch
        from ddtrace.llmobs import LLMObs
    except ImportError:
        logger.warning("Datadog LLM Observability requested, but ddtrace is not installed.")
        return

    site = os.getenv("DD_SITE", "datadoghq.com")
    env = os.getenv("DD_ENV") or os.getenv("ENVIRONMENT") or "development"
    service = os.getenv("DD_SERVICE", "owleyes-api")
    ml_app = os.getenv("DD_LLMOBS_ML_APP", "owleyes-ai")
    project_name = os.getenv("DD_LLMOBS_PROJECT_NAME") or None
    app_key = os.getenv("DD_APP_KEY") or None
    agentless_enabled = _as_bool(os.getenv("DD_LLMOBS_AGENTLESS_ENABLED"), default=True)

    patch(openai=True)
    LLMObs.enable(
        ml_app=ml_app,
        integrations_enabled=True,
        agentless_enabled=agentless_enabled,
        site=site,
        api_key=api_key,
        app_key=app_key,
        project_name=project_name,
        env=env,
        service=service,
    )
    _llmobs_configured = True
    logger.info(
        "Datadog LLM Observability enabled for ml_app=%s service=%s env=%s",
        ml_app,
        service,
        env,
    )