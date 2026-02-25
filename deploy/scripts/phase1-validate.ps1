param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$Cookie = ""
)

$ErrorActionPreference = "Stop"

function Step($msg) {
  Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

function CallJson($method, $url, $body = $null, $cookie = "") {
  $headers = @{ "Content-Type" = "application/json" }
  if ($cookie) { $headers["Cookie"] = "access_token=$cookie" }
  if ($body) {
    return Invoke-RestMethod -Method $method -Uri $url -Headers $headers -Body $body
  }
  return Invoke-RestMethod -Method $method -Uri $url -Headers $headers
}

Step "Diagnostics"
$diag = CallJson "GET" "$BaseUrl/api/v1/diagnostics"
$diag | ConvertTo-Json -Depth 8

Step "Jobs summary"
$jobs = CallJson "GET" "$BaseUrl/api/v1/jobs/summary"
$jobs | ConvertTo-Json -Depth 8

if ($Cookie) {
  Step "Feature flags"
  $flags = CallJson "GET" "$BaseUrl/api/v1/admin/settings/feature-flags" $null $Cookie
  $flags | ConvertTo-Json -Depth 8

  Step "Trigger scan"
  $scan = CallJson "POST" "$BaseUrl/api/v1/admin/scan/run" "{}" $Cookie
  $scan | ConvertTo-Json -Depth 8
} else {
  Write-Warning "No access token provided. Skipping admin endpoints."
}

Step "Aggregate summary"
$summary = CallJson "GET" "$BaseUrl/api/v1/cost/summary?range=prev_month"
$summary | ConvertTo-Json -Depth 8

Step "Live usage sample (Jan 2026)"
$live = CallJson "GET" "$BaseUrl/api/v1/costs/by-resource?start_date=2026-01-01&end_date=2026-01-31"
$live | ConvertTo-Json -Depth 8

Write-Host "`nPhase 1 validation completed." -ForegroundColor Green
