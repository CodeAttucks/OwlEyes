# Datadog GitHub Actions Setup

This repository now emits lightweight custom metrics from key GitHub Actions workflows directly to Datadog using the Datadog Metrics API.

Integrated workflows:

- `.github/workflows/app-ci.yml`
- `.github/workflows/staging-security-validation.yml`
- `.github/workflows/deploy-edge-function.yml`

The integration is intentionally non-blocking. If Datadog ingestion fails, the workflow logs a warning and continues.

## GitHub Configuration

### Required Repository Secret

Add this under **Repository Settings -> Secrets and variables -> Actions -> Secrets**:

| Name | Required | Example | Purpose |
|------|----------|---------|---------|
| `DD_API_KEY` | Yes | `********************************` | Datadog API key used to submit custom metrics |

### Recommended Repository Variables

Add these under **Repository Settings -> Secrets and variables -> Actions -> Variables**:

| Name | Required | Recommended Value | Purpose |
|------|----------|-------------------|---------|
| `DD_SITE` | Yes | `datadoghq.com` | Datadog site. Use `datadoghq.eu`, `us3.datadoghq.com`, `us5.datadoghq.com`, etc. if your org is hosted there |
| `DD_ENV` | Yes | `ci` | Environment tag added to all workflow metrics |
| `DD_SERVICE` | Yes | `owleyes-github-actions` | Service tag for grouping GitHub Actions telemetry |
| `DD_EXTRA_TAGS` | No | `team:platform,app:owleyes` | Extra comma-separated tags appended to every emitted metric |

If the variables are omitted, the workflows fall back to:

- `DD_SITE=datadoghq.com`
- `DD_ENV=ci`
- `DD_SERVICE=owleyes-github-actions`

## Datadog Configuration

### 1. Create the API Key

In Datadog:

1. Go to **Organization Settings -> API Keys**
2. Create a new key named `github-actions-owleyes`
3. Copy the value into the GitHub secret `DD_API_KEY`

No Datadog application key is required for this integration because the workflows only send metrics.

### 2. Optional GitHub Integration

For richer repository metadata in Datadog, install the Datadog GitHub integration in addition to the custom metrics above. The custom metrics drive the dashboard design below; the GitHub integration is additive, not required.

### 2a. Claude MCP Onboarding

If you manage Datadog onboarding through the Claude CLI on your local machine, add the Datadog US3 MCP server with:

```bash
claude mcp add --transport http datadog-onboarding-us3 "https://mcp.us3.datadoghq.com/api/unstable/mcp-server/mcp?toolsets=onboarding"
claude /mcp
```

That command could not be executed in this workspace because the `claude` CLI is not installed in the container.

### 3. Metric Names Emitted

The workflows submit these metrics:

| Metric | Type | Meaning |
|--------|------|---------|
| `owleyes.github_actions.job.completed` | Count | One point per job execution |
| `owleyes.github_actions.job.duration_seconds` | Gauge | Wall-clock duration of the GitHub Actions job |

### 4. Tags Emitted on Every Metric

Each metric includes these tags:

- `repo:CodeAttucks/OwlEyes`
- `workflow:<workflow name>`
- `job:<job id>`
- `branch:<branch name>`
- `event:<github event name>`
- `status:<success|failure|cancelled>`
- `env:<DD_ENV>`
- `service:<DD_SERVICE>`
- `pipeline_type:<ci|deploy>`
- `provider:github`
- `runner:github-actions`
- any tags from `DD_EXTRA_TAGS`

## Dashboard Layout

Create a dashboard named `OwlEyes GitHub Actions` with the widgets below.

### Row 1: Pipeline Health

#### Widget 1: CI job volume (query value)

```text
sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,pipeline_type:ci}.as_count()
```

Time window: `Last 24 hours`

#### Widget 2: Deploy job volume (query value)

```text
sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,pipeline_type:deploy}.as_count()
```

Time window: `Last 7 days`

#### Widget 3: Failed CI jobs (query value)

```text
sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,pipeline_type:ci,status:failure}.as_count()
```

Time window: `Last 24 hours`

#### Widget 4: Failed deploy jobs (query value)

```text
sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,pipeline_type:deploy,status:failure}.as_count()
```

Time window: `Last 7 days`

### Row 2: Trends

#### Widget 5: CI success vs failure over time (timeseries)

```text
sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,pipeline_type:ci} by {status}.as_count()
```

Display: Stacked bars or lines

#### Widget 6: Deploy success vs failure over time (timeseries)

```text
sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,pipeline_type:deploy} by {status}.as_count()
```

Display: Stacked bars or lines

#### Widget 7: Average job duration by workflow (timeseries)

```text
avg:owleyes.github_actions.job.duration_seconds{repo:CodeAttucks/OwlEyes} by {workflow}
```

Display: Lines

### Row 3: Breakdown

#### Widget 8: Slowest jobs (top list)

```text
top(avg:owleyes.github_actions.job.duration_seconds{repo:CodeAttucks/OwlEyes} by {workflow,job}, 10, 'mean', 'desc')
```

#### Widget 9: Job runs by workflow (top list)

```text
top(sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes} by {workflow}, 10, 'sum', 'desc')
```

#### Widget 10: Failures by branch (top list)

```text
top(sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,status:failure} by {branch}, 10, 'sum', 'desc')
```

### Row 4: Focus Views

#### Widget 11: App CI job duration (timeseries)

```text
avg:owleyes.github_actions.job.duration_seconds{repo:CodeAttucks/OwlEyes,workflow:App CI} by {job}
```

#### Widget 12: Staging security validation failures (query value)

```text
sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,workflow:Staging Security Validation,status:failure}.as_count()
```

#### Widget 13: Deploy pipeline runs by status (sunburst or top list)

```text
sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,workflow:Deploy Edge Function} by {status,job}
```

## Suggested Dashboard Template Variables

Add these template variables so the dashboard can be filtered quickly:

- `repo`
- `workflow`
- `job`
- `branch`
- `status`
- `pipeline_type`
- `env`

## Recommended Alerts

Create monitors for these conditions:

1. CI failures in the last hour

```text
sum(last_1h):sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,pipeline_type:ci,status:failure}.as_count() >= 1
```

2. Deploy failures in the last 24 hours

```text
sum(last_24h):sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes,pipeline_type:deploy,status:failure}.as_count() >= 1
```

3. App CI mean duration regression

```text
avg(last_1d):avg:owleyes.github_actions.job.duration_seconds{repo:CodeAttucks/OwlEyes,workflow:App CI} > 900
```

## Verification

After the GitHub secret and variables are configured:

1. Run `App CI` manually from the Actions tab
2. In Datadog Metrics Explorer, query:

```text
sum:owleyes.github_actions.job.completed{repo:CodeAttucks/OwlEyes} by {workflow,status}
```

3. Confirm data points appear within a few minutes
4. Build the dashboard from the widget queries above