param(
    [Parameter(Mandatory = $true)]
    [string]$SessionId,

    [Parameter(Mandatory = $true)]
    [string]$QueueId,

    [string]$Role = "reviewer-verifier",
    [string]$Platform = "codex",
    [string]$Adapter = "subagent",
    [string]$RequiredTier,
    [string]$ActualTier,
    [string]$ModelLabel,
    [string]$RequestId,
    [string]$AgentId,
    [string]$ResultPath,
    [switch]$CheckGate = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function New-PrepareNativeRequest {
    param(
        [string]$SessionId,
        [string]$QueueId,
        [string]$Role,
        [string]$Platform,
        [string]$Adapter,
        [string]$RequiredTier,
        [string]$ActualTier,
        [string]$ModelLabel
    )

    $args = @(
        "runner","prepare-native",
        "--role", $Role,
        "--session-id", $SessionId,
        "--queue", $QueueId,
        "--platform", $Platform,
        "--adapter", $Adapter
    )

    if ($RequiredTier) { $args += @("--required-tier", $RequiredTier) }
    if ($ActualTier) { $args += @("--actual-tier", $ActualTier) }
    if ($ModelLabel) { $args += @("--model-label", $ModelLabel) }

    $output = & harness @args
    if ($LASTEXITCODE -ne 0) {
        throw "prepare-native failed."
    }

    return ($output | ConvertFrom-Json)
}

function Add-SpawnRecord {
    param(
        [string]$SessionId,
        [string]$RequestId,
        [string]$Role,
        [string]$AgentId
    )

    & harness runner record-native-spawn `
        --session-id $SessionId `
        --request-id $RequestId `
        --role $Role `
        --agent-id $AgentId `
        --status spawned

    if ($LASTEXITCODE -ne 0) {
        throw "record-native-spawn failed."
    }
}

function Parse-ResultFile {
    param(
        [string]$Role,
        [string]$SessionId,
        [string]$RequestId,
        [string]$AgentId,
        [string]$Input
    )

    if (-not (Test-Path -LiteralPath $Input)) {
        throw "Result file not found: $Input"
    }

    & harness runner parse-result `
        --role $Role `
        --session-id $SessionId `
        --request-id $RequestId `
        --agent-id $AgentId `
        --input $Input

    if ($LASTEXITCODE -ne 0) {
        throw "parse-result failed."
    }
}

$prepare = New-PrepareNativeRequest `
    -SessionId $SessionId `
    -QueueId $QueueId `
    -Role $Role `
    -Platform $Platform `
    -Adapter $Adapter `
    -RequiredTier $RequiredTier `
    -ActualTier $ActualTier `
    -ModelLabel $ModelLabel

$RequestId = $prepare.requestId
Write-Output "native handoff prepared"
Write-Output "requestId: $RequestId"
Write-Output "requestPath: $($prepare.requestPath)"
Write-Output "promptPath: $($prepare.promptPath)"

if (-not $AgentId) {
    Write-Output "下一步：使用平台原生 spawn_agent，拿到 agent-id 后再次执行此脚本并加入 -AgentId"
    return
}

Add-SpawnRecord `
    -SessionId $SessionId `
    -RequestId $RequestId `
    -Role $Role `
    -AgentId $AgentId

if (-not $ResultPath) {
    Write-Output "下一步：平台回传结果后，用 -ResultPath 重跑，继续执行 parse-result."
    return
}

Parse-ResultFile `
    -Role $Role `
    -SessionId $SessionId `
    -RequestId $RequestId `
    -AgentId $AgentId `
    -Input $ResultPath

if ($CheckGate) {
    harness gate check verification --session-id $SessionId
    if ($LASTEXITCODE -ne 0) {
        throw "harness gate check verification failed."
    }
}

Write-Output "流程完成：native handoff -> spawn record -> parse-result -> gate check verification"
