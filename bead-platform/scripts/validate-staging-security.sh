#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BEAD_DIR="${ROOT_DIR}/bead-platform"

COMPOSE_FILE="${BEAD_DIR}/docker-compose.prod.yml"
NGINX_CONF="${BEAD_DIR}/nginx.conf"
API_MAIN="${BEAD_DIR}/api/main.py"
DEPLOY_DOC="${ROOT_DIR}/PROD_DEPLOYMENT.md"
GITIGNORE_FILE="${BEAD_DIR}/.gitignore"

EXPECTED_DOMAIN="${EXPECTED_DOMAIN:-bead-it.base44.app}"
LETSENCRYPT_DIR="${LETSENCRYPT_DIR:-/etc/letsencrypt}"
CERT_FULLCHAIN="${LETSENCRYPT_DIR}/live/${EXPECTED_DOMAIN}/fullchain.pem"
CERT_PRIVKEY="${LETSENCRYPT_DIR}/live/${EXPECTED_DOMAIN}/privkey.pem"
VALIDATE_DB_AUDIT="${VALIDATE_DB_AUDIT:-0}"
REQUIRE_TLS_CERT_FILES="${REQUIRE_TLS_CERT_FILES:-1}"
REPORT_FILE="${REPORT_FILE:-}"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
REPORT_LINES=()

add_line() {
  local status="$1"
  local item="$2"
  local details="$3"
  REPORT_LINES+=("| ${status} | ${item} | ${details} |")
}

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  add_line "PASS" "$1" "$2"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  add_line "FAIL" "$1" "$2"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  add_line "WARN" "$1" "$2"
}

service_has_key() {
  local file="$1"
  local service="$2"
  local key="$3"

  awk -v svc="$service" -v wanted="$key" '
    BEGIN { in_service = 0; found = 0 }
    $0 ~ "^  " svc ":$" { in_service = 1; next }
    in_service && $0 ~ "^  [a-zA-Z0-9_-]+:$" { in_service = 0 }
    in_service && $1 == wanted ":" { found = 1 }
    END { exit(found ? 0 : 1) }
  ' "$file"
}

DB_AUDIT_RESULT="skipped"

# 1) Compose tooling and config
if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    pass "Docker Compose available" "docker and docker compose detected"
  else
    fail "Docker Compose available" "docker compose command not available"
  fi
else
  fail "Docker available" "docker command not found"
fi

RENDERED_COMPOSE=""
if [ "${FAIL_COUNT}" -eq 0 ]; then
  RENDERED_COMPOSE="$(mktemp)"
  COMPOSE_ERR="$(mktemp)"
  if docker compose -f "${COMPOSE_FILE}" config >"${RENDERED_COMPOSE}" 2>"${COMPOSE_ERR}"; then
    pass "Compose config render" "${COMPOSE_FILE} rendered successfully"
  else
    fail "Compose config render" "failed to render compose config: $(tr '\n' ' ' <"${COMPOSE_ERR}")"
  fi
  rm -f "${COMPOSE_ERR}"
fi

# 2) SSL/TLS nginx config and cert presence
if grep -q "listen 443 ssl" "${NGINX_CONF}"; then
  pass "TLS listener configured" "listen 443 ssl found in nginx config"
else
  fail "TLS listener configured" "listen 443 ssl not found in ${NGINX_CONF}"
fi

if grep -q "${EXPECTED_DOMAIN}" "${NGINX_CONF}"; then
  pass "TLS domain configured" "${EXPECTED_DOMAIN} found in nginx config"
else
  fail "TLS domain configured" "${EXPECTED_DOMAIN} not found in nginx config"
fi

if [ -f "${CERT_FULLCHAIN}" ] && [ -f "${CERT_PRIVKEY}" ]; then
  pass "TLS cert files present" "found cert files under ${LETSENCRYPT_DIR}"
else
  if [ "${REQUIRE_TLS_CERT_FILES}" = "1" ]; then
    fail "TLS cert files present" "missing ${CERT_FULLCHAIN} and/or ${CERT_PRIVKEY}"
  else
    warn "TLS cert files present" "missing ${CERT_FULLCHAIN} and/or ${CERT_PRIVKEY} (allowed in this mode)"
  fi
fi

if command -v docker >/dev/null 2>&1; then
  NGINX_TEST_OUT="$(mktemp)"
  if [ -f "${CERT_FULLCHAIN}" ] && [ -f "${CERT_PRIVKEY}" ]; then
    if docker run --rm \
      --add-host api:127.0.0.1 \
      --add-host web:127.0.0.1 \
      -v "${NGINX_CONF}:/etc/nginx/nginx.conf:ro" \
      -v "${LETSENCRYPT_DIR}:/etc/letsencrypt:ro" \
      nginx:alpine nginx -t >"${NGINX_TEST_OUT}" 2>&1; then
      pass "Nginx syntax test" "nginx -t passed in container"
    else
      fail "Nginx syntax test" "nginx -t failed: $(tr '\n' ' ' <"${NGINX_TEST_OUT}")"
    fi
  else
    warn "Nginx syntax test" "skipped because cert files are not available"
  fi
  rm -f "${NGINX_TEST_OUT}"
fi

# 3) Secrets handling
if [ -f "${GITIGNORE_FILE}" ] && grep -qxF ".env" "${GITIGNORE_FILE}"; then
  pass "Secrets in env files" "${GITIGNORE_FILE} ignores .env"
else
  fail "Secrets in env files" "${GITIGNORE_FILE} missing exact .env ignore entry"
fi

if git -C "${ROOT_DIR}" ls-files | grep -Eq '(^|/)\.env$'; then
  fail "No tracked .env files" "one or more .env files are tracked in git"
else
  pass "No tracked .env files" "no .env files tracked in git index"
fi

# 4) Firewall/DB exposure and backup tooling
if [ -n "${RENDERED_COMPOSE}" ] && [ -f "${RENDERED_COMPOSE}" ]; then
  DB_PORTS="$(awk '
    BEGIN { in_db = 0; ports = 0 }
    /^  db:$/ { in_db = 1; next }
    in_db && /^  [a-zA-Z0-9_-]+:$/ { in_db = 0 }
    in_db && /^    ports:$/ { ports = 1 }
    END { print ports }
  ' "${RENDERED_COMPOSE}")"

  DB_EXPOSE="$(awk '
    BEGIN { in_db = 0; expose = 0 }
    /^  db:$/ { in_db = 1; next }
    in_db && /^  [a-zA-Z0-9_-]+:$/ { in_db = 0 }
    in_db && /^    expose:$/ { expose = 1 }
    END { print expose }
  ' "${RENDERED_COMPOSE}")"

  if [ "${DB_PORTS}" = "0" ] && [ "${DB_EXPOSE}" = "1" ]; then
    pass "DB network exposure" "db has no host ports and uses internal expose"
  else
    fail "DB network exposure" "db ports/expose policy mismatch (ports=${DB_PORTS}, expose=${DB_EXPOSE})"
  fi

  for service in db api web; do
    if service_has_key "${RENDERED_COMPOSE}" "${service}" "healthcheck"; then
      pass "Healthcheck for ${service}" "healthcheck configured"
    else
      fail "Healthcheck for ${service}" "healthcheck missing"
    fi
  done
fi

if command -v ufw >/dev/null 2>&1; then
  pass "Host firewall tooling" "ufw available"
else
  warn "Host firewall tooling" "ufw not available in this environment"
fi

if command -v pg_dump >/dev/null 2>&1; then
  pass "Backup tooling" "$(pg_dump --version)"
else
  fail "Backup tooling" "pg_dump not found"
fi

# 5) CORS domain
if grep -q "https://${EXPECTED_DOMAIN}" "${API_MAIN}"; then
  pass "CORS allowlist" "https://${EXPECTED_DOMAIN} found in ${API_MAIN}"
else
  fail "CORS allowlist" "https://${EXPECTED_DOMAIN} not found in ${API_MAIN}"
fi

# 6) DB audit logging
if [ "${VALIDATE_DB_AUDIT}" = "1" ]; then
  if [ -n "${DATABASE_URL:-}" ] && command -v psql >/dev/null 2>&1; then
    AUDIT_OUT="$(mktemp)"
    if psql "${DATABASE_URL}" -Atqc "SHOW shared_preload_libraries; SHOW pgaudit.log;" >"${AUDIT_OUT}" 2>/dev/null; then
      if grep -q "pgaudit" "${AUDIT_OUT}"; then
        pass "DB audit logging" "pgaudit detected in database settings"
        DB_AUDIT_RESULT="validated"
      else
        fail "DB audit logging" "pgaudit not present in SHOW output"
        DB_AUDIT_RESULT="failed"
      fi
    else
      fail "DB audit logging" "unable to query database with provided DATABASE_URL"
      DB_AUDIT_RESULT="failed"
    fi
    rm -f "${AUDIT_OUT}"
  else
    fail "DB audit logging" "VALIDATE_DB_AUDIT=1 requires DATABASE_URL and psql"
    DB_AUDIT_RESULT="failed"
  fi
else
  if grep -q "CREATE EXTENSION IF NOT EXISTS pgaudit;" "${DEPLOY_DOC}"; then
    warn "DB audit logging" "runtime check skipped (set VALIDATE_DB_AUDIT=1 to verify live DB)"
  else
    fail "DB audit logging" "pgaudit guidance not found in ${DEPLOY_DOC}"
  fi
fi

if [ -n "${RENDERED_COMPOSE}" ] && [ -f "${RENDERED_COMPOSE}" ]; then
  rm -f "${RENDERED_COMPOSE}"
fi

echo
echo "Staging Security Validation Report"
echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Domain: ${EXPECTED_DOMAIN}"
echo
echo "| Status | Check | Details |"
echo "| --- | --- | --- |"
for line in "${REPORT_LINES[@]}"; do
  echo "${line}"
done

echo
echo "Summary: PASS=${PASS_COUNT} FAIL=${FAIL_COUNT} WARN=${WARN_COUNT}"

if [ -n "${REPORT_FILE}" ]; then
  {
    echo "Staging Security Validation Report"
    echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Domain: ${EXPECTED_DOMAIN}"
    echo
    echo "| Status | Check | Details |"
    echo "| --- | --- | --- |"
    for line in "${REPORT_LINES[@]}"; do
      echo "${line}"
    done
    echo
    echo "Summary: PASS=${PASS_COUNT} FAIL=${FAIL_COUNT} WARN=${WARN_COUNT}"
  } >"${REPORT_FILE}"
fi

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "## Staging Security Validation"
    echo
    echo "- PASS: ${PASS_COUNT}"
    echo "- FAIL: ${FAIL_COUNT}"
    echo "- WARN: ${WARN_COUNT}"
    echo
    echo "| Status | Check | Details |"
    echo "| --- | --- | --- |"
    for line in "${REPORT_LINES[@]}"; do
      echo "${line}"
    done
  } >>"${GITHUB_STEP_SUMMARY}"
fi

if [ "${FAIL_COUNT}" -gt 0 ]; then
  exit 1
fi

exit 0
