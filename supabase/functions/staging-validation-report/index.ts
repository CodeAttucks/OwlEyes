type ValidationReportPayload = {
  repository?: string;
  pull_request_number?: string | number;
  sha?: string;
  run_id?: string;
  run_url?: string;
  report?: string;
};

declare const Deno: {
  env: {
    get(name: string): string | undefined;
  };
  serve(handler: (req: Request) => Response | Promise<Response>): void;
};

function jsonResponse(status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

function logEvent(level: "INFO" | "WARN" | "ERROR", event: string, context: Record<string, unknown>) {
  console.log(JSON.stringify({
    ts: new Date().toISOString(),
    level,
    event,
    ...context,
  }));
}

Deno.serve(async (req: Request) => {
  const requestId = crypto.randomUUID();
  const sourceIp = req.headers.get("x-forwarded-for") ?? "unknown";
  const userAgent = req.headers.get("user-agent") ?? "unknown";

  if (req.method !== "POST") {
    logEvent("WARN", "invalid_method", {
      request_id: requestId,
      method: req.method,
      source_ip: sourceIp,
    });
    return jsonResponse(405, { error: "Method not allowed", request_id: requestId });
  }

  const expectedToken = Deno.env.get("EDGE_FUNCTION_TOKEN");
  if (!expectedToken) {
    logEvent("ERROR", "misconfigured_missing_token", {
      request_id: requestId,
    });
    return jsonResponse(500, { error: "Function is not configured", request_id: requestId });
  }

  const authHeader = req.headers.get("authorization") ?? "";
  const providedToken = authHeader.startsWith("Bearer ") ? authHeader.slice(7).trim() : "";

  if (!providedToken || providedToken !== expectedToken) {
    logEvent("WARN", "auth_failed", {
      request_id: requestId,
      source_ip: sourceIp,
      user_agent: userAgent,
    });
    return jsonResponse(401, { error: "Unauthorized", request_id: requestId });
  }

  let payload: ValidationReportPayload;
  try {
    payload = await req.json();
  } catch {
    logEvent("WARN", "invalid_json", {
      request_id: requestId,
    });
    return jsonResponse(400, { error: "Invalid JSON payload", request_id: requestId });
  }

  if (!payload.report || typeof payload.report !== "string") {
    logEvent("WARN", "missing_report", {
      request_id: requestId,
      repository: payload.repository ?? null,
      run_id: payload.run_id ?? null,
    });
    return jsonResponse(400, { error: "Payload must include report string", request_id: requestId });
  }

  if (payload.report.length > 200_000) {
    logEvent("WARN", "report_too_large", {
      request_id: requestId,
      report_size: payload.report.length,
    });
    return jsonResponse(413, { error: "Report payload too large", request_id: requestId });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  if (supabaseUrl && serviceRoleKey) {
    const insertBody = {
      repository: payload.repository ?? "unknown",
      pull_request_number: payload.pull_request_number ? Number(payload.pull_request_number) : null,
      sha: payload.sha ?? null,
      run_id: payload.run_id ?? null,
      run_url: payload.run_url ?? null,
      report: payload.report,
      source_ip: sourceIp,
      user_agent: userAgent,
    };

    const insertResp = await fetch(`${supabaseUrl}/rest/v1/security_validation_reports`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: serviceRoleKey,
        Authorization: `Bearer ${serviceRoleKey}`,
        Prefer: "return=minimal",
      },
      body: JSON.stringify(insertBody),
    });

    if (!insertResp.ok) {
      const errorText = await insertResp.text();
      logEvent("ERROR", "report_insert_failed", {
        request_id: requestId,
        status: insertResp.status,
        body: errorText,
        repository: payload.repository ?? null,
        run_id: payload.run_id ?? null,
      });
      return jsonResponse(502, { error: "Failed to persist validation report", request_id: requestId });
    }
  } else {
    logEvent("WARN", "persistence_disabled", {
      request_id: requestId,
      reason: "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing",
    });
  }

  logEvent("INFO", "report_accepted", {
    request_id: requestId,
    repository: payload.repository ?? null,
    pull_request_number: payload.pull_request_number ?? null,
    run_id: payload.run_id ?? null,
    source_ip: sourceIp,
  });

  return jsonResponse(202, {
    ok: true,
    request_id: requestId,
  });
});
