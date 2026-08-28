[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string] $EvidenceRoot,
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string] $BootstrapUamiResourceId,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')][string] $BootstrapPrincipalId,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')][string] $BootstrapClientId,
    [switch] $AuthorizeV25A,
    [switch] $AuthorizeV25B
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# V2.5 is a local pre-authorization harness. It intentionally contains no
# Azure CLI invocation. Future mutation modes remain unavailable in this run.
$script:AcceptedApplicationSha = 'c42e6c449483b0951de0f366d700dbaf7b9e5525'
$script:AcceptedApplicationTree = 'a497c6951064119453d175d1b93d4e59c9029fd0'
$script:AcceptedImage = 'acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d'
$script:SqlFqdn = 'sql-proposalops-prod-uae-2bea2887.database.windows.net'
$script:SqlDatabase = 'sqldb-proposalops-prod'
$script:ExpectedPrivateIp = '10.43.2.4'
$script:ReplicaTimeout = 300

function Get-Sha256([string] $Value) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
    return (([Security.Cryptography.SHA256]::Create().ComputeHash($bytes) | ForEach-Object ToString x2) -join '').ToLowerInvariant()
}

function Assert-CanonicalGuid([string] $Name, [string] $Value) {
    $parsed = [guid]::Empty
    if (-not [guid]::TryParse($Value, [ref]$parsed) -or $Value -ne $parsed.ToString()) { throw "STOP_UAMI_SCALAR_CONTRACT_FAILED:$Name" }
    if ($Value -match '[\r\n]|^\s|\s$|@\{|\}\.principalId|\}\.clientId|\$\(') { throw "STOP_UAMI_SCALAR_CONTRACT_FAILED:$Name" }
}

function Assert-ScalarIdentity {
    param([string] $ResourceId, [string] $PrincipalId, [string] $ClientId)
    if ([string]::IsNullOrWhiteSpace($ResourceId) -or $ResourceId -notmatch '(?i)^/subscriptions/[0-9a-f-]{36}/resourcegroups/[^/]+/providers/Microsoft.ManagedIdentity/userassignedidentities/[^/]+$') { throw 'STOP_UAMI_SCALAR_CONTRACT_FAILED:resourceId' }
    Assert-CanonicalGuid 'principalId' $PrincipalId
    Assert-CanonicalGuid 'clientId' $ClientId
    if ($PrincipalId.ToLowerInvariant() -eq $ClientId.ToLowerInvariant()) { throw 'STOP_UAMI_SCALAR_CONTRACT_FAILED:principal_client_collision' }
}

function New-ConnectionContract {
    param([ValidateSet('V25A','V25B')][string] $Lane)
    Assert-ScalarIdentity $BootstrapUamiResourceId $BootstrapPrincipalId $BootstrapClientId
    $base = [ordered]@{
        driver = 'ODBC Driver 18 for SQL Server'; server = $script:SqlFqdn; port = 1433
        database = $script:SqlDatabase; encrypt = 'yes'; trust_server_certificate = 'no'
        authentication = 'ActiveDirectoryMsi'; uid = $BootstrapPrincipalId
        uid_identifier_class = 'principalId/objectId'; password_present = $false
        client_secret_present = $false; dsn_dependency = $false
    }
    if ($Lane -eq 'V25A') { $base.sql_login_executed = $false; $base.sql_statements_executed = $false }
    else { $base.sql_login_executed = $true; $base.sql_statements_executed = $false }
    return $base
}

function New-StructuredJobPayload {
    param([string] $Name, [ValidateSet('V25A','V25B')][string] $Lane, [string] $Body, [hashtable] $Environment)
    if ($Name -notmatch '^p025-[a-z0-9-]+$') { throw 'STOP_V25A_TEMPLATE_VALIDATION_FAILED:job_name' }
    if ($Body -match '(?i)access_token|identity_header|password|client.secret|bearer|CREATE\s+USER|ALTER\s+ROLE|INSERT\s+INTO|UPDATE\s+') { throw 'STOP_SECRET_OR_SQL_STATEMENT_IN_TEMPLATE' }
    $env = [ordered]@{}; foreach ($key in ($Environment.Keys | Sort-Object)) { $env[$key] = [string]$Environment[$key] }
    return [ordered]@{
        name = $Name; lane = $Lane; image = $script:AcceptedImage; environment = 'cae-proposalops-prod-uae'
        triggerType = 'Manual'; command = @('python'); args = @('-c', $Body)
        env = $env; identity = @($BootstrapUamiResourceId); registryIdentity = $BootstrapUamiResourceId
        replicaRetryLimit = 0; parallelism = 1; replicaCompletionCount = 1; replicaTimeout = $script:ReplicaTimeout
        bodySha256 = Get-Sha256 $Body; commandArraySha256 = Get-Sha256 (@('python') | ConvertTo-Json -Compress)
        argsArraySha256 = Get-Sha256 (@('-c',$Body) | ConvertTo-Json -Compress)
        envContractSha256 = Get-Sha256 ($env | ConvertTo-Json -Compress)
    }
}

function Test-StructuredJobPayload {
    param([hashtable] $Payload, [string] $ExpectedBody, [ValidateSet('V25A','V25B')][string] $Lane)
    if ($Payload.image -ne $script:AcceptedImage -or $Payload.environment -ne 'cae-proposalops-prod-uae') { throw "STOP_${Lane}_TEMPLATE_VALIDATION_FAILED:image_or_environment" }
    if (@($Payload.command).Count -ne 1 -or $Payload.command[0] -ne 'python') { throw "STOP_${Lane}_TEMPLATE_VALIDATION_FAILED:command" }
    if (@($Payload.args).Count -ne 2 -or $Payload.args[0] -ne '-c' -or $Payload.args[1] -ne $ExpectedBody) { throw "STOP_${Lane}_TEMPLATE_VALIDATION_FAILED:args" }
    if ($Payload.bodySha256 -ne (Get-Sha256 $ExpectedBody) -or $Payload.replicaRetryLimit -ne 0 -or $Payload.parallelism -ne 1 -or $Payload.replicaCompletionCount -ne 1) { throw "STOP_${Lane}_TEMPLATE_VALIDATION_FAILED:hash_or_limits" }
    if (@($Payload.identity).Count -ne 1 -or $Payload.identity[0] -ne $BootstrapUamiResourceId -or $Payload.registryIdentity -ne $BootstrapUamiResourceId) { throw "STOP_${Lane}_TEMPLATE_VALIDATION_FAILED:identity" }
    return $true
}

function Get-FourStateResult([string] $State, [string] $Reason) {
    if ($State -notin @('PASS','FAIL','NOT_EXECUTED','NOT_PROVEN')) { throw 'STOP_FOUR_STATE_SEMANTICS_VALIDATION_FAILED' }
    return [ordered]@{ state = $State; reason = $Reason }
}

function Write-PreauthorizationPlan {
    New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
    if ($AuthorizeV25A -or $AuthorizeV25B) { throw 'STOP_AUTHORIZATION_NOT_AVAILABLE_IN_PREAUTHORIZATION_RUN' }
    $aBody = 'import json,os,socket; print(json.dumps({"dns":"executed_inside_aca","sql_token":"executed_inside_aca","sql_login_executed":False,"sql_statements_executed":False}))'
    $bBody = 'import os,pyodbc; pyodbc.connect("DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:"+os.environ["SQL_FQDN"]+",1433;DATABASE="+os.environ["SQL_DATABASE"]+";Encrypt=yes;TrustServerCertificate=no;Authentication=ActiveDirectoryMsi;UID="+os.environ["ODBC_MSI_UID"],timeout=30).close()'
    $env = @{ SQL_FQDN=$script:SqlFqdn; SQL_DATABASE=$script:SqlDatabase; ODBC_MSI_UID=$BootstrapPrincipalId; SYNTHETIC_ONLY='true'; REAL_DATA_ALLOWED='false' }
    $a = New-StructuredJobPayload 'p025-v25a-network-token' 'V25A' $aBody $env
    $b = New-StructuredJobPayload 'p025-v25b-native-login' 'V25B' $bBody $env
    Test-StructuredJobPayload $a $aBody 'V25A' | Out-Null; Test-StructuredJobPayload $b $bBody 'V25B' | Out-Null
    $plan = [ordered]@{ schema='proposalops.azure.p0.v2.5.preauthorization'; mode='PREAUTH_READ_ONLY'; accepted_application_sha=$script:AcceptedApplicationSha; accepted_application_tree=$script:AcceptedApplicationTree; accepted_image=$script:AcceptedImage; mission_cumulative_mutations_derived=19; azure_mutations_current_run=0; sql_connection_attempts=0; v25a_authorized=$false; v25b_authorized=$false; migration_authorized=$false; api_deployment_authorized=$false; phase6_authorized=$false; cross_track_convergence_authorized=$false; real_amec_data_allowed=$false; aca_runtime_private_dns=(Get-FourStateResult 'NOT_EXECUTED' 'No future Job execution authorized'); aca_runtime_tcp_1433=(Get-FourStateResult 'NOT_EXECUTED' 'No future Job execution authorized'); native_odbc_msi_sql_login=(Get-FourStateResult 'NOT_EXECUTED' 'No future Job execution authorized'); v25a_template=$a; v25b_template=$b; sql_admin_propagation='NOT_PROVEN'; restoration_design='UNCONDITIONAL_OUTER_CLEANUP_REQUIRED' }
    $plan | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $EvidenceRoot 'V25_PREAUTHORIZATION_PLAN.json') -Encoding utf8NoBOM
    return $plan
}

Write-PreauthorizationPlan | ConvertTo-Json -Depth 30
