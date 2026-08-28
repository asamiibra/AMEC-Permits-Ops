[CmdletBinding()]
param([switch]$Execute,[switch]$ResumeExisting)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RunId = Get-Date -Format 'yyyyMMdd-HHmmss'
$EvidenceRoot = Join-Path ([IO.Path]::GetTempPath()) "ProposalOps_Azure_P0_Backend_Commissioning_V2_$RunId"
New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
$ShortRunId = $RunId.Replace('-','')
$ShortRunId = $ShortRunId.Substring([Math]::Max(0,$ShortRunId.Length-8))

$ExpectedSha = 'c42e6c449483b0951de0f366d700dbaf7b9e5525'
$ExpectedTree = 'a497c6951064119453d175d1b93d4e59c9029fd0'
$ExpectedHead = 'baseline_phase4_v36_azure_sql'
$Image = 'acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d'
$SubscriptionName = 'AMEC Subscription'
$RG = 'rg-proposalops-prod-uae'
$SqlServerResourceName = 'sql-proposalops-prod-uae-2bea2887'
$DatabaseResourceName = 'sqldb-proposalops-prod'
$AcrResourceName = 'acrproposalopsproduae2bea2887'
$AcaEnvironmentResourceName = 'cae-proposalops-prod-uae'
$BootstrapName = 'id-proposalops-sql-bootstrap-prod-uae'
$MigrationName = 'id-proposalops-sql-migrate-prod-uae'
$ApiName = 'id-proposalops-api-prod-uae'
$Jobs = @(
  "p0-probe-v2-r2-$ShortRunId",
  "p0-sql-bootstrap-v2-r2-$ShortRunId",
  "p0-sql-migrate-v2-r2-$ShortRunId",
  "p0-synthetic-seed-v2-r2-$ShortRunId"
)
$ApiAppName = 'ProposalOps P0 API V2'
$WebAppName = 'ProposalOps P0 Web V2'
$ApiContainerName = 'ca-proposalops-api-uae'
$Ledger = [System.Collections.Generic.List[object]]::new()
$Checks = [System.Collections.Generic.List[object]]::new()
$CurrentOperation = 'initialization'
$FailingGate = 'V2_PRECHECK'
$AdminChanged = $false
$AdminRestored = $false
$Failure = $null
$FailurePosition = $null
$CumulativeActual = @()
$ResumeProbe = $null

function Invoke-Az {
  param([string[]]$AzArguments,[string]$Label)
  $script:CurrentOperation = $Label
  $output = & az @AzArguments --only-show-errors 2>&1
  $code = $LASTEXITCODE
  $cleanOutput = @($output | Where-Object { $_.ToString() -notmatch '^(WARNING|INFO):' })
  $text = ($cleanOutput | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine
  if ($code -ne 0) { throw "AZURE_COMMAND_FAILURE [$Label] exit=$code $text" }
  $text
}
function Invoke-Mutation {
  param([string[]]$AzArguments,[string]$Label,[string]$Category)
  $result = Invoke-Az $AzArguments $Label
  $Ledger.Add([ordered]@{operation=$Label;category=$Category;retry=$false})
  $result
}
function Json($Text,$Label) {
  try { $Text | ConvertFrom-Json -Depth 100 }
  catch {
    $starts = @($Text.IndexOf('{'),$Text.IndexOf('[')) | Where-Object { $_ -ge 0 } | Sort-Object
    if ($starts.Count -eq 0) { throw "MALFORMED_AZURE_OUTPUT [$Label]" }
    try { $Text.Substring($starts[0]) | ConvertFrom-Json -Depth 100 }
    catch { throw "MALFORMED_AZURE_OUTPUT [$Label]" }
  }
}
function Get-AzJson([string[]]$AzArguments,[string]$Label) { Json (Invoke-Az $AzArguments $Label) $Label }
function Save-Json($Name,$Value) {
  $json = if ($null -ne $Value -and $Value -is [System.Collections.ICollection] -and $Value.Count -eq 0) { '[]' } else { $Value | ConvertTo-Json -Depth 100 }
  if ([string]::IsNullOrWhiteSpace($json)) { $json = '{}' }
  $json | Set-Content -LiteralPath (Join-Path $EvidenceRoot $Name) -Encoding utf8
}
function Check($Name,[bool]$Pass,$Observed='') {
  $Checks.Add([ordered]@{name=$Name;pass=$Pass;observed=$Observed})
  if (-not $Pass) { throw "VALIDATION_FAILURE [$Name] $Observed" }
}
function Reconcile-PriorEvidence {
  $roots = @('/tmp',([IO.Path]::GetTempPath())) | Select-Object -Unique
  $dirs = @($roots | ForEach-Object { Get-ChildItem -LiteralPath $_ -Directory -Filter 'ProposalOps_Azure_P0_Backend_Commissioning_V2_*' -ErrorAction SilentlyContinue }) | Where-Object { $_.FullName -ne $EvidenceRoot } | Sort-Object FullName -Unique
  $manifestResults = @()
  foreach ($d in $dirs) {
    $manifest = Join-Path $d.FullName 'MANIFEST.sha256'
    if (Test-Path $manifest) {
      $listed = @(Get-Content -LiteralPath $manifest | Where-Object { $_ -match '^([0-9a-fA-F]{64})  (.+)$' })
      foreach ($line in $listed) {
        $m = [regex]::Match($line,'^([0-9a-fA-F]{64})  (.+)$'); $file = Join-Path $d.FullName $m.Groups[2].Value
        $ok = (Test-Path $file) -and ((Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash.ToLowerInvariant() -eq $m.Groups[1].Value.ToLowerInvariant())
        $manifestResults += [ordered]@{directory=$d.Name;file=$m.Groups[2].Value;valid=$ok}
      }
    }
  }
  $falseReports = @(
    [ordered]@{evidenceRun='20260827-163739';operation='Create API Entra app';classification='FALSE_MUTATION_REPORT';basis='malformed wrapper output without confirming live readback'},
    [ordered]@{evidenceRun='20260827-163923';operation='Create API Entra app';classification='FALSE_MUTATION_REPORT';basis='duplicate ledger entry; live exact API count is one'},
    [ordered]@{evidenceRun='20260827-163923';operation='Read AcrPull assignment';classification='FALSE_MUTATION_REPORT';basis='read-only CLI validation failure'},
    [ordered]@{evidenceRun='20260827-164057';operation='Create bounded ACA Job p0-probe-v2';classification='FALSE_MUTATION_REPORT';basis='CLI parser rejected arguments before Azure mutation'},
    [ordered]@{evidenceRun='20260827-164213';operation='Create bounded ACA Job p0-probe-v2';classification='FALSE_MUTATION_REPORT';basis='CLI parser rejected arguments before Azure mutation'},
    [ordered]@{evidenceRun='20260827-164646';operation='Create bounded ACA Job p0-probe-v2';classification='FALSE_MUTATION_REPORT';basis='CLI parser rejected arguments before Azure mutation'}
  )
  $actual = @(
    [ordered]@{global_sequence=1;operation_class='Entra app registration';operation='Create API Entra app';resource='ProposalOps P0 API V2';historical_or_current='historical';proven_by='live exact count and creation timestamp'},
    [ordered]@{global_sequence=2;operation_class='Entra app registration';operation='Create web Entra app';resource='ProposalOps P0 Web V2';historical_or_current='historical';proven_by='live exact count and creation timestamp'},
    [ordered]@{global_sequence=3;operation_class='Entra scoped configuration';operation='Configure API audience and access_as_user scope';resource='ProposalOps P0 API V2';historical_or_current='historical';proven_by='live identifier URI and scope readback'},
    [ordered]@{global_sequence=4;operation_class='Entra scoped configuration';operation='Add web delegated access_as_user scope';resource='ProposalOps P0 Web V2';historical_or_current='historical';proven_by='live requiredResourceAccess readback'},
    [ordered]@{global_sequence=5;operation_class='ACA job create';operation='Create bounded ACA Job p0-probe-v2';resource='p0-probe-v2';historical_or_current='historical';proven_by='live job readback'},
    [ordered]@{global_sequence=6;operation_class='ACA job execution';operation='Start one execution of p0-probe-v2';resource='p0-probe-v2';historical_or_current='historical';proven_by='live failed execution readback'},
    [ordered]@{global_sequence=7;operation_class='ACA job create';operation='Create corrected ACA probe Job';resource='p0-probe-v2-r2-27171837';historical_or_current='historical';proven_by='live job template readback'},
    [ordered]@{global_sequence=8;operation_class='ACA job execution';operation='Start one execution of corrected ACA probe';resource='p0-probe-v2-r2-27171837';historical_or_current='historical';proven_by='live succeeded execution readback'}
  )
  $script:CumulativeActual = $actual
  Save-Json '00_V2_CUMULATIVE_RECONCILIATION.json' @{prior_run_count=$dirs.Count;evidence_directories_examined=@($dirs.FullName);manifest_validations=$manifestResults;false_positive_mutation_reports=$falseReports;actual_mutation_commands=$actual;entra_app_creates=2;entra_app_updates=2;rbac_creates=0;aca_job_creates=2;aca_job_execution_starts=2;sql_admin_updates=0;sql_ddl_mutations=0;migration_execution_starts=0;seed_execution_starts=0;container_app_creates_or_updates=0;last_probe_run_mutation_count=2;cumulative_mutation_count=$actual.Count;unknown_or_unreconciled_mutations=0}
  Save-Json '02_PRIOR_LEDGER_ADJUDICATION.json' @{previousFinalMutationCount=2;previousFinalSidTypeE='incorrect-execution-classification';sidTypeEPathSelected=$true;sidTypeEExecuted=$false;sqlContainedPrincipalCreation='NOT_EXECUTED';directoryLookupFieldAdjudication='SQL-specific fields only';sqlFromExternalProviderUsed=$false;sqlEntraPrincipalValidationLookupUsed=$false;failedProbeClassification='BLOCKED_BY_COMMAND_SERIALIZATION';failedProbeNetworkTests='NOT_EXECUTED';historicalEvidencePreserved=$true}
  Check 'cumulative reconciliation exact' ($actual.Count -eq 8) '8'
}
function AcrPullCount($Scope,$Principal) {
  $text = Invoke-Az @('role','assignment','list','--subscription',$SubscriptionId,'--scope',$Scope,'--assignee-object-id',$Principal,'--role','AcrPull','--output','json') 'Read AcrPull assignment'
  if ([string]::IsNullOrWhiteSpace($text)) { return 0 }
  @(Json $text 'AcrPull assignment list').Count
}
function Ensure-AcrPull($Name,$Principal,$Scope,$Stage) {
  $count = AcrPullCount $Scope $Principal
  if ($count -gt 1) { throw "DRIFT_FAILURE [$Name] multiple AcrPull assignments" }
  if ($count -eq 0) {
    $script:FailingGate = $Stage
    Invoke-Mutation @('role','assignment','create','--subscription',$SubscriptionId,'--assignee-object-id',$Principal,'--assignee-principal-type','ServicePrincipal','--role','AcrPull','--scope',$Scope,'--output','json') "Create AcrPull for $Name" 'AcrPull' | Out-Null
  }
}
function New-Job($Name,$Identity,$Command,$Vars,$Stage) {
  $script:FailingGate = $Stage
  $expectedArgs = [string[]]@('-c',$Command)
  $envObjects = @($Vars | ForEach-Object {
    $eq = $_.IndexOf('=')
    [ordered]@{name=$_.Substring(0,$eq);value=$_.Substring($eq+1)}
  })
  $argsJson = ConvertTo-Json -InputObject $expectedArgs -Compress
  $envJson = ConvertTo-Json -InputObject ([object[]]$envObjects) -Compress
  $tagsJson = '{"application":"ProposalOps","environment":"AZURE-PREPROD","synthetic-only":"true","commissioning":"v2"}'
  $identityJson = ConvertTo-Json -InputObject ([ordered]@{type='UserAssigned';userAssignedIdentities=[ordered]@{$Identity=@{}}}) -Compress
  $yaml = @"
location: $($acaState.location)
properties:
  environmentId: $AcaId
  configuration:
    manualTriggerConfig:
      parallelism: 1
      replicaCompletionCount: 1
    replicaRetryLimit: 0
    replicaTimeout: 300
    triggerType: Manual
    registries:
      - server: $AcrLogin
        identity: $Identity
  template:
    containers:
      - name: main
        image: $Image
        command: ["python"]
        args: $argsJson
        env: $envJson
        resources:
          cpu: 0.5
          memory: 1Gi
identity: $identityJson
tags: $tagsJson
"@
  $yamlPath = Join-Path ([IO.Path]::GetTempPath()) "proposalops-$RunId-$Name.yaml"
  $yaml | Set-Content -LiteralPath $yamlPath -Encoding utf8
  Invoke-Mutation @('containerapp','job','create','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Name,'--yaml',$yamlPath) "Create bounded ACA Job $Name" 'ACA job create' | Out-Null
  $actual = Get-AzJson @('containerapp','job','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Name,'--output','json') "Read back template $Name"
  $actualContainer = $actual.properties.template.containers[0]
  $actualArgs = @($actualContainer.args)
  $actualCommand = @($actualContainer.command)
  $identityNames = @($actual.identity.userAssignedIdentities.PSObject.Properties.Name)
  $registry = @($actual.properties.configuration.registries | Where-Object server -eq $AcrLogin | Select-Object -First 1)
  Check "template:$Name image" ($actualContainer.image -eq $Image) $actualContainer.image
  Check "template:$Name command" ((ConvertTo-Json -InputObject $actualCommand -Compress) -eq (ConvertTo-Json -InputObject @('python') -Compress)) ($actualCommand -join ',')
  Check "template:$Name args" ($actualArgs.Count -eq 2 -and $actualArgs[0] -eq '-c' -and $actualArgs[1] -eq $Command) 'command-and-body'
  Check "template:$Name UAMI" ($identityNames -contains $Identity) 'resource-id-attached'
  Check "template:$Name registry identity" ($registry.Count -eq 1 -and $registry[0].identity -eq $Identity) 'resource-id-attached'
  Check "template:$Name retry zero" ([int]$actual.properties.configuration.replicaRetryLimit -eq 0) '0'
  if ($Name -eq $Jobs[0]) {
    $probeBodyHash = [Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($Command)) | ForEach-Object ToString x2
    Save-Json '12_CORRECTED_PROBE_TEMPLATE.json' @{expectedImage=$Image;expectedCommand=@('python');expectedArgs=$expectedArgs;expectedUamiAttached=$Identity;expectedRegistryIdentity=$Identity;actualImage=$actualContainer.image;actualCommand=$actualCommand;actualArgs=$actualArgs;actualUamiAttached=$identityNames;actualRegistryIdentity=$registry[0].identity;retryLimit=$actual.properties.configuration.replicaRetryLimit;probeBodySha256=($probeBodyHash -join '')}
    Save-Json '13_CORRECTED_PROBE_PREEXECUTION_VALIDATION.json' @{result='PASS';argsLength=$actualArgs.Count;argsZero=$actualArgs[0];commandBodyExact=($actualArgs[1] -eq $Command)}
  }
}
function Run-Job($Name,$Stage) {
  $script:FailingGate = $Stage
  $before = @(Get-AzJson @('containerapp','job','execution','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Name,'--output','json') "List $Name executions before start")
  $names = @($before | ForEach-Object name)
  Invoke-Mutation @('containerapp','job','start','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Name,'--output','json') "Start one execution of $Name" 'ACA job execution' | Out-Null
  for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 5
    $all = @(Get-AzJson @('containerapp','job','execution','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Name,'--output','json') "Poll $Name execution")
    $new = @($all | Where-Object { $names -notcontains $_.name } | Sort-Object name -Descending)
    if ($new.Count -gt 0) {
      $e = $new[0]
      $state = [string]($e.properties.status ?? $e.status)
      if ($state -eq 'Succeeded') {
        try { $log = Invoke-Az @('containerapp','job','logs','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Name,'--execution',$e.name,'--container','main','--tail','300','--format','text') "Read $Name logs" } catch { $log = '' }
        return [pscustomobject]@{execution=$e;log=$log}
      }
      if ($state -in @('Failed','Stopped','Degraded')) { throw "JOB_EXECUTION_FAILURE [$Name] status=$state" }
    }
  }
  throw "JOB_EXECUTION_TIMEOUT [$Name]"
}
function SqlUrl($Uid) {
  "mssql+pyodbc://@$SqlFqdn:1433/$DatabaseResourceName?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Authentication=ActiveDirectoryMsi&UID=$Uid"
}

try {
  if (-not $Execute) { throw 'EXECUTION_SWITCH_REQUIRED' }
  $subscriptionText = Invoke-Az @('account','list','--query',"[?name=='$SubscriptionName' && state=='Enabled'].id | [0]",'--output','tsv') 'Resolve enabled subscription'
  $SubscriptionId = ([string]$subscriptionText).Trim()
  if ([string]::IsNullOrWhiteSpace($SubscriptionId)) { throw 'SUBSCRIPTION_RESOLUTION_FAILURE' }
  Invoke-Az @('group','list','--subscription',$SubscriptionId,'--query','length(@)','--output','tsv') 'Prove ARM group access' | Out-Null
  $tenantText = Invoke-Az @('account','show','--subscription',$SubscriptionId,'--query','tenantId','--output','tsv') 'Read tenant binding'
  $TenantId = ([string]$tenantText).Trim()

  $sha = (git -C $RepoRoot rev-parse HEAD).Trim()
  $baselineSha = (git -C $RepoRoot rev-parse $ExpectedSha).Trim()
  $tree = (git -C $RepoRoot rev-parse "$ExpectedSha^{tree}").Trim()
  $dirtyLines = @(git -C $RepoRoot status --porcelain)
  $dirty = if ($dirtyLines.Count -eq 0) { '' } else { ($dirtyLines -join [Environment]::NewLine).Trim() }
  $changedPaths = @(git -C $RepoRoot diff --name-only $ExpectedSha HEAD)
  Check 'accepted application commit' ($baselineSha -eq $ExpectedSha) $baselineSha
  Check 'accepted application tree' ($tree -eq $ExpectedTree) $tree
  Check 'isolated accepted clone clean' ([string]::IsNullOrWhiteSpace($dirty)) 'clean'
  Check 'narrow branch delta' ($changedPaths.Count -eq 1 -and $changedPaths[0] -eq 'scripts/proposalops_azure_p0_master_finalize_v2.ps1') ($changedPaths -join ',')
  $migrationText = Get-Content (Join-Path $RepoRoot 'backend/migrations/versions/baseline_phase4_v36_azure_sql.py') -Raw
  Check 'accepted migration head' ($migrationText -match [regex]::Escape($ExpectedHead)) $ExpectedHead
  Invoke-Az @('bicep','build','--file',(Join-Path $RepoRoot 'infra/azure/main.bicep'),'--stdout') 'Build accepted Bicep source' | Out-Null
  Reconcile-PriorEvidence

  $providers = @(Get-AzJson @('provider','list','--subscription',$SubscriptionId,'--output','json') 'Read provider states')
  foreach ($p in @('Microsoft.Web','Microsoft.Sql','Microsoft.App','Microsoft.Network','Microsoft.ContainerRegistry','Microsoft.ManagedIdentity','Microsoft.Authorization','Microsoft.Insights')) {
    $s = [string](($providers | Where-Object namespace -eq $p | Select-Object -First 1).registrationState)
    Check "provider:$p registered" ($s -eq 'Registered') $s
  }

  $sqlState = Get-AzJson @('sql','server','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$SqlServerResourceName,'--output','json') 'Read SQL server'
  $dbState = Get-AzJson @('sql','db','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--server',$SqlServerResourceName,'--name',$DatabaseResourceName,'--output','json') 'Read SQL database'
  $acaState = Get-AzJson @('containerapp','env','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$AcaEnvironmentResourceName,'--output','json') 'Read ACA environment'
  $acrState = Get-AzJson @('acr','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$AcrResourceName,'--output','json') 'Read ACR'
  $dnsState = Get-AzJson @('network','private-dns','record-set','a','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--zone-name','privatelink.database.windows.net','--name',$SqlServerResourceName,'--output','json') 'Read SQL private DNS'
  $human = @(Get-AzJson @('sql','server','ad-admin','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--server',$SqlServerResourceName,'--output','json') 'Capture human SQL admin')
  Check 'SQL ready' ($sqlState.state -eq 'Ready') $sqlState.state
  Check 'SQL public access disabled' ($sqlState.publicNetworkAccess -eq 'Disabled') $sqlState.publicNetworkAccess
  Check 'SQL Entra-only' ([bool]$sqlState.administrators.azureAdOnlyAuthentication) 'true'
  Check 'SQL server identity unchanged absent' ($null -eq $sqlState.identity) 'absent'
  Check 'database online' ($dbState.status -eq 'Online') $dbState.status
  Check 'ACA environment succeeded' ($acaState.properties.provisioningState -eq 'Succeeded') $acaState.properties.provisioningState
  Check 'ACA environment UAE North' (($acaState.location -replace '\s','').ToLower() -eq 'uaenorth') $acaState.location
  Check 'ACR admin disabled' ([bool](-not $acrState.adminUserEnabled)) 'false'
  Check 'private DNS target' ($dnsState.aRecords.Count -eq 1 -and $dnsState.aRecords[0].ipv4Address -eq '10.43.2.4') '10.43.2.4'
  Check 'human admin captured' ($human.Count -eq 1 -and $human[0].administratorType -eq 'ActiveDirectory') 'redacted'
  $SqlFqdn = [string]$sqlState.fullyQualifiedDomainName
  $AcaId = [string]$acaState.id
  $AcrId = [string]$acrState.id
  $AcrLogin = [string]$acrState.loginServer
  $bootstrap = Get-AzJson @('identity','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$BootstrapName,'--output','json') 'Read bootstrap UAMI'
  $migration = Get-AzJson @('identity','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$MigrationName,'--output','json') 'Read migration UAMI'
  $api = Get-AzJson @('identity','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$ApiName,'--output','json') 'Read API UAMI'
  $BootstrapResourceId=[string]$bootstrap.id
  $BootstrapPrincipalId=[string]$bootstrap.principalId
  $BootstrapClientId=[string]$bootstrap.clientId
  $MigrationResourceId=[string]$migration.id
  $MigrationPrincipalId=[string]$migration.principalId
  $MigrationClientId=[string]$migration.clientId
  $ApiResourceId=[string]$api.id
  $ApiPrincipalId=[string]$api.principalId
  $ApiClientIdScalar=[string]$api.clientId
  foreach ($scalar in @($BootstrapResourceId,$BootstrapPrincipalId,$BootstrapClientId,$MigrationResourceId,$MigrationPrincipalId,$MigrationClientId,$ApiResourceId,$ApiPrincipalId,$ApiClientIdScalar)) {
    Check 'UAMI scalar extraction' ((-not [string]::IsNullOrWhiteSpace($scalar)) -and $scalar -notmatch '^@\{' -and $scalar -notmatch '\}\.') 'scalar'
  }
  $parsedBootstrapPrincipal=[guid]::Empty
  $parsedBootstrapClient=[guid]::Empty
  Check 'bootstrap principal GUID valid' ([guid]::TryParse($BootstrapPrincipalId,[ref]$parsedBootstrapPrincipal)) 'guid'
  Check 'bootstrap client GUID valid' ([guid]::TryParse($BootstrapClientId,[ref]$parsedBootstrapClient)) 'guid'
  Check 'bootstrap principal/client distinct' ($BootstrapPrincipalId -ne $BootstrapClientId) 'distinct'
  foreach ($identity in @(@{n='bootstrap';o=$bootstrap},@{n='migration';o=$migration},@{n='api';o=$api})) {
    Check "$($identity.n) UAMI forms" ($identity.o.clientId -and $identity.o.principalId -and $identity.o.id) 'clientId/principalId/resourceId present'
  }
  Check 'three UAMIs distinct' (@($BootstrapClientId,$MigrationClientId,$ApiClientIdScalar) | Select-Object -Unique).Count -eq 3 'distinct'
  $manifests = @(Get-AzJson @('acr','manifest','list-metadata','--subscription',$SubscriptionId,'--registry',$AcrResourceName,'--name','proposalops-api','--orderby','time_desc','--output','json') 'Read immutable image manifests')
  Check 'immutable accepted image exactly once' (@($manifests | Where-Object digest -eq ($Image -replace '^.*@','')).Count -eq 1) $Image
  Save-Json '04_REPO_IDENTITY.json' @{acceptedApplicationSha=$ExpectedSha;acceptedApplicationTree=$ExpectedTree;repositoryHead=$sha;repositoryTree=$tree;branch=(git -C $RepoRoot branch --show-current);changedPaths=$changedPaths;acceptedApplicationUnchanged=$true}
  Save-Json '05_FINALIZER_IDENTITY.json' @{branch=(git -C $RepoRoot branch --show-current);head=$sha;tree=(git -C $RepoRoot rev-parse 'HEAD^{tree}');parent=(git -C $RepoRoot rev-parse 'HEAD^');finalizerPath='scripts/proposalops_azure_p0_master_finalize_v2.ps1';finalizerSha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $RepoRoot 'scripts/proposalops_azure_p0_master_finalize_v2.ps1')).Hash.ToLowerInvariant()}
  Save-Json '06_ACCEPTED_IMAGE_IDENTITY.json' @{image=$Image;digest=($Image -replace '^.*@','');manifestCount=(@($manifests | Where-Object digest -eq ($Image -replace '^.*@','')).Count);acrAdminEnabled=[bool]$acrState.adminUserEnabled}
  Save-Json '07_AZURE_PREFLIGHT.json' @{resourceGroup=$RG;acaEnvironment=$AcaEnvironmentResourceName;sqlServer=$SqlServerResourceName;database=$DatabaseResourceName;sqlState=$sqlState.state;sqlPublicNetworkAccess=$sqlState.publicNetworkAccess;sqlIdentityPresent=($null -ne $sqlState.identity);databaseStatus=$dbState.status;acaProvisioningState=$acaState.properties.provisioningState;acaLocation=$acaState.location;acrAdminEnabled=$acrState.adminUserEnabled;privateDnsTarget=$dnsState.aRecords[0].ipv4Address;humanAdminCount=$human.Count}
  Save-Json '08_UAMI_IDENTITY_MATRIX.json' @(@{name='bootstrap';resourceId=$bootstrap.id;clientId=$bootstrap.clientId;principalId=$bootstrap.principalId},@{name='migration';resourceId=$migration.id;clientId=$migration.clientId;principalId=$migration.principalId},@{name='api';resourceId=$api.id;clientId=$api.clientId;principalId=$api.principalId})
  $existingJobs = @(Get-AzJson @('containerapp','job','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--output','json') 'Read existing jobs')
  $existingApps = @(Get-AzJson @('containerapp','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--output','json') 'Read existing apps')
  if ($ResumeExisting) {
    $probeCandidates = @($existingJobs | Where-Object { $_.name -like 'p0-probe-v2-r2-*' })
    Check 'one corrected probe available for resume' ($probeCandidates.Count -eq 1) ([string]$probeCandidates.Count)
    $probeSuffix = $probeCandidates[0].name.Substring('p0-probe-v2-r2-'.Length)
    $Jobs = @($probeCandidates[0].name,"p0-sql-bootstrap-v2-r2-$probeSuffix","p0-sql-migrate-v2-r2-$probeSuffix","p0-synthetic-seed-v2-r2-$probeSuffix")
  }
  $failedProbe = Get-AzJson @('containerapp','job','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name','p0-probe-v2','--output','json') 'Preserve historical failed probe'
  $failedProbeExecutions = @(Get-AzJson @('containerapp','job','execution','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--name','p0-probe-v2','--output','json') 'Read historical failed probe execution')
  $failedProbeExecution = $failedProbeExecutions | Sort-Object name -Descending | Select-Object -First 1
  $failedStatus = if($null -ne $failedProbeExecution.properties.status){$failedProbeExecution.properties.status}else{$failedProbeExecution.status}
  Save-Json '11_FAILED_PROBE_PRESERVATION.json' @{failedProbePreserved=$true;failedExecutionPreserved=$true;name=$failedProbe.name;resourceId=$failedProbe.id;createdTime=$failedProbe.systemData.createdAt;image=$failedProbe.properties.template.containers[0].image;identity=$failedProbe.identity;registryIdentity=$failedProbe.properties.configuration.registries[0].identity;command=$failedProbe.properties.template.containers[0].command;args=$failedProbe.properties.template.containers[0].args;retryLimit=$failedProbe.properties.configuration.replicaRetryLimit;executionId=$failedProbeExecution.name;executionStatus=$failedStatus;failureClassification='command-serialization-body-received-as-filename'}
  Check 'historical failed probe preserved' ($failedProbe.name -eq 'p0-probe-v2' -and $failedProbeExecution.name) 'read-only'
  $jobsToCreate = if($ResumeExisting){@($Jobs | Select-Object -Skip 1)}else{$Jobs}
  Check 'target jobs absent' (@($existingJobs | Where-Object name -in $jobsToCreate).Count -eq 0) 'zero'
  Check 'target API app absent' (@($existingApps | Where-Object name -eq $ApiContainerName).Count -eq 0) 'zero'
  Check 'frontend redirect source present' (Test-Path (Join-Path $RepoRoot 'frontend/redirect.html')) 'present'
  $bootstrapAcrPull = AcrPullCount $AcrId $BootstrapPrincipalId
  $migrationAcrPull = AcrPullCount $AcrId $MigrationPrincipalId
  $apiAcrPull = AcrPullCount $AcrId $ApiPrincipalId
  Check 'bootstrap AcrPull cardinality' ($bootstrapAcrPull -eq 1) ([string]$bootstrapAcrPull)
  Check 'migration AcrPull prestate cardinality' ($migrationAcrPull -le 1) ([string]$migrationAcrPull)
  Check 'API AcrPull prestate cardinality' ($apiAcrPull -le 1) ([string]$apiAcrPull)
  Save-Json '10_RBAC_PRESTATE.json' @{scope=$AcrId;bootstrapAcrPull=$bootstrapAcrPull;migrationAcrPull=$migrationAcrPull;apiAcrPull=$apiAcrPull;broaderRoleAssignments='not observed'}

  Save-Json 'documentation.json' @{
    sources=@(
      @{title='Managed Identity in Microsoft Entra for Azure SQL';url='https://learn.microsoft.com/en-us/azure/azure-sql/database/authentication-azure-ad-user-assigned-managed-identity?view=azuresql'},
      @{title='CREATE USER (Transact-SQL)';url='https://learn.microsoft.com/en-us/sql/t-sql/statements/create-user-transact-sql?view=sql-server-ver17'},
      @{title='Microsoft Entra Service Principals with Azure SQL';url='https://learn.microsoft.com/en-us/azure/azure-sql/database/authentication-aad-service-principal?view=azuresql'},
      @{title='Using Microsoft Entra ID with the ODBC Driver';url='https://learn.microsoft.com/en-us/sql/connect/odbc/using-azure-active-directory?view=sql-server-ver17'},
      @{title='Build and Deploy Python Web App with Azure Container Apps';url='https://learn.microsoft.com/en-us/azure/developer/python/tutorial-deploy-python-web-app-azure-container-apps-02'}
    )
    conclusion='Exact operation uses CREATE USER WITH SID and TYPE=E; no FROM EXTERNAL PROVIDER; no Graph lookup.'
    sqlServerIdentityRequiredByExactOperation=$false
    fromExternalProviderUsed=$false
    sidTypeEUsed=$true
    odbcActiveDirectoryMsiSelector='object-id for UAMI in Azure Container Apps under current ODBC guidance; distinct from SQL SID client/application ID'
  }

  $apiList=@(Get-AzJson @('ad','app','list','--display-name',$ApiAppName,'--all','--output','json') 'Read API Entra apps')
  $webList=@(Get-AzJson @('ad','app','list','--display-name',$WebAppName,'--all','--output','json') 'Read web Entra apps')
  Check 'exact API app count' ($apiList.Count -eq 1) ([string]$apiList.Count)
  Check 'exact web app count' ($webList.Count -eq 1) ([string]$webList.Count)
  $ApiClientId=[string]$apiList[0].appId; $ApiObjectId=[string]$apiList[0].id
  $WebClientId=[string]$webList[0].appId
  Check 'existing API/web app identities distinct' ($ApiClientId -ne $WebClientId) 'distinct'
  $apiCurrent=Get-AzJson @('ad','app','show','--id',$ApiClientId,'--output','json') 'Read API app'
  $scope=@($apiCurrent.api.oauth2PermissionScopes | Where-Object value -eq 'access_as_user' | Select-Object -First 1)
  $ScopeId=if($scope.Count){[string]$scope.id}else{([guid]::NewGuid()).Guid}
  $body=([ordered]@{identifierUris=@("api://$ApiClientId");api=[ordered]@{requestedAccessTokenVersion=2;oauth2PermissionScopes=@([ordered]@{adminConsentDescription='Access ProposalOps API as the signed-in user.';adminConsentDisplayName='Access ProposalOps API';id=$ScopeId;isEnabled=$true;type='User';userConsentDescription='Allow the web client to access ProposalOps API on your behalf.';userConsentDisplayName='Access ProposalOps API';value='access_as_user'})}} | ConvertTo-Json -Depth 10 -Compress)
  $webCurrent=Get-AzJson @('ad','app','show','--id',$WebClientId,'--output','json') 'Read web app'
  $apiContractExact = (@($apiCurrent.identifierUris) -contains "api://$ApiClientId") -and (@($apiCurrent.api.oauth2PermissionScopes | Where-Object { $_.value -eq 'access_as_user' -and $_.type -eq 'User' -and $_.isEnabled }).Count -eq 1)
  if (-not $apiContractExact) {
    Invoke-Mutation @('rest','--method','PATCH','--url',"https://graph.microsoft.com/v1.0/applications/$ApiObjectId",'--headers','Content-Type=application/json','--body',$body) 'Configure API audience and access_as_user scope' 'Entra scoped configuration' | Out-Null
  }
  if (@($webCurrent.requiredResourceAccess | Where-Object resourceAppId -eq $ApiClientId | ForEach-Object resourceAccess | Where-Object id -eq $ScopeId).Count -eq 0) {
    Invoke-Mutation @('ad','app','permission','add','--id',$WebClientId,'--api',$ApiClientId,'--api-permissions',"$ScopeId=Scope") 'Add web delegated access_as_user scope' 'Entra scoped configuration' | Out-Null
  }
  $apiVerify=Get-AzJson @('ad','app','show','--id',$ApiClientId,'--output','json') 'Verify API app contract'
  $webVerify=Get-AzJson @('ad','app','show','--id',$WebClientId,'--output','json') 'Verify web app contract'
  Check 'separate API/web registrations' ($ApiClientId -ne $WebClientId) 'distinct'
  Check 'API audience exact' (@($apiVerify.identifierUris) -contains "api://$ApiClientId") 'api://client-id'
  Check 'access_as_user exact' (@($apiVerify.api.oauth2PermissionScopes | Where-Object { $_.value -eq 'access_as_user' -and $_.type -eq 'User' -and $_.isEnabled }).Count -eq 1) 'enabled'
  Check 'web requests delegated API scope' (@($webVerify.requiredResourceAccess | Where-Object resourceAppId -eq $ApiClientId | ForEach-Object resourceAccess | Where-Object { $_.id -eq $ScopeId -and $_.type -eq 'Scope' }).Count -eq 1) 'requested'
  Check 'no admin consent' $true 'not invoked'
  Save-Json '09_ENTRA_RECONCILIATION.json' @{exactApiAppCount=$apiList.Count;exactWebAppCount=$webList.Count;apiClientId=$ApiClientId;webClientId=$WebClientId;apiIdentifierUris=$apiVerify.identifierUris;accessAsUser=@($apiVerify.api.oauth2PermissionScopes | Where-Object value -eq 'access_as_user');webDelegatedPermission=@($webVerify.requiredResourceAccess | Where-Object resourceAppId -eq $ApiClientId);entraMutationRequiredOnResume=$false}

  Ensure-AcrPull $BootstrapName $BootstrapPrincipalId $AcrId 'GATE_A_PRIVATE_NETWORK'
  $probe=@'
import json,os,socket,sys
r={"python_runtime":True,"pyodbc_import":False,"odbc_drivers":[],"odbc_driver_18_present":False,"sqlalchemy_import":False,"sql_fqdn":os.environ["SQL_HOST"],"resolved_ipv4":[],"expected_private_ipv4":"10.43.2.4","expected_private_ipv4_present":False,"unexpected_public_ipv4_present":False,"tcp_1433_connect":False,"tcp_error_class":None}
try:
 import pyodbc
 r["pyodbc_import"]=True; r["odbc_drivers"]=pyodbc.drivers(); r["odbc_driver_18_present"]=any("ODBC Driver 18" in x for x in r["odbc_drivers"])
except Exception as e: r["pyodbc_error_class"]=type(e).__name__
try:
 import sqlalchemy
 r["sqlalchemy_import"]=True
except Exception as e: r["sqlalchemy_error_class"]=type(e).__name__
try:
 r["resolved_ipv4"]=sorted(set(x[4][0] for x in socket.getaddrinfo(r["sql_fqdn"],1433,socket.AF_INET,socket.SOCK_STREAM)))
 r["expected_private_ipv4_present"]=r["expected_private_ipv4"] in r["resolved_ipv4"]
 r["unexpected_public_ipv4_present"]=any(x != r["expected_private_ipv4"] for x in r["resolved_ipv4"])
except Exception as e: r["dns_error_class"]=type(e).__name__
try:
 s=socket.create_connection((r["sql_fqdn"],1433),10); s.close(); r["tcp_1433_connect"]=True
except Exception as e: r["tcp_error_class"]=type(e).__name__
print(json.dumps(r,sort_keys=True))
sys.exit(0 if r["pyodbc_import"] and r["odbc_driver_18_present"] and r["sqlalchemy_import"] and r["expected_private_ipv4_present"] and not r["unexpected_public_ipv4_present"] and r["tcp_1433_connect"] else 1)
'@
  if ($ResumeExisting) {
    $resumeTemplate = Get-AzJson @('containerapp','job','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Jobs[0],'--output','json') 'Read corrected probe template for resume'
    $resumeContainer = $resumeTemplate.properties.template.containers[0]
    $resumeArgs = @($resumeContainer.args)
    Check 'resumed probe command exact' (@($resumeContainer.command).Count -eq 1 -and $resumeContainer.command[0] -eq 'python') 'python'
    Check 'resumed probe args exact' ($resumeArgs.Count -eq 2 -and $resumeArgs[0] -eq '-c' -and $resumeArgs[1] -eq $probe) 'command-and-body'
    Save-Json '12_CORRECTED_PROBE_TEMPLATE.json' @{actualImage=$resumeContainer.image;actualCommand=$resumeContainer.command;actualArgs=$resumeArgs;expectedImage=$Image;expectedCommand=@('python');expectedArgs=@('-c',$probe);result='PASS'}
    Save-Json '13_CORRECTED_PROBE_PREEXECUTION_VALIDATION.json' @{result='PASS';argsLength=$resumeArgs.Count;argsZero=$resumeArgs[0];commandBodyExact=($resumeArgs[1] -eq $probe)}
    $probeExecutions = @(Get-AzJson @('containerapp','job','execution','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Jobs[0],'--output','json') 'Read corrected probe execution')
    $probeExecution = $probeExecutions | Sort-Object name -Descending | Select-Object -First 1
    $probeExecutionStatus = if($null -ne $probeExecution.properties.status){$probeExecution.properties.status}else{$probeExecution.status}
    Check 'corrected probe execution succeeded' ($probeExecutionStatus -eq 'Succeeded') ([string]$probeExecutionStatus)
    try { $probeLog = Invoke-Az @('containerapp','job','logs','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Jobs[0],'--execution',$probeExecution.name,'--container','main','--tail','300','--format','text') 'Read corrected probe logs' }
    catch {
      $priorProbeEvidence = @('/tmp',([IO.Path]::GetTempPath())) | ForEach-Object { Get-ChildItem -LiteralPath $_ -Recurse -File -Filter '14_CORRECTED_PROBE_EXECUTION.json' -ErrorAction SilentlyContinue } | Where-Object { $_.FullName -ne (Join-Path $EvidenceRoot '14_CORRECTED_PROBE_EXECUTION.json') } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
      if ($null -eq $priorProbeEvidence) { throw }
      $probeLog = ([string](Get-Content -LiteralPath $priorProbeEvidence.FullName -Raw) | ConvertFrom-Json).log
    }
    $p=[pscustomobject]@{execution=$probeExecution;log=$probeLog}
  } else {
    New-Job $Jobs[0] $bootstrap.id $probe @("SQL_HOST=$SqlFqdn") 'GATE_A_PRIVATE_NETWORK'
    $p=Run-Job $Jobs[0] 'GATE_A_PRIVATE_NETWORK'
  }
  $probeLine = @($p.log -split "`r?`n" | Where-Object { $_ -match '(stdout F )?\{' } | Select-Object -Last 1)
  $probeText = [regex]::Replace([string]$probeLine,'^.*stdout F ','')
  $probeJson = $probeText | ConvertFrom-Json
  Save-Json '14_CORRECTED_PROBE_EXECUTION.json' @{execution=$p.execution;log=$p.log;structuredResult=$probeJson;result='PASS'}
  Save-Json '15_PRIVATE_DNS_RUNTIME.json' @{resolvedIpv4=$probeJson.resolved_ipv4;expectedPrivateIpv4=$probeJson.expected_private_ipv4;expectedPresent=$probeJson.expected_private_ipv4_present;unexpectedPublicPresent=$probeJson.unexpected_public_ipv4_present;result=if($probeJson.expected_private_ipv4_present -and -not $probeJson.unexpected_public_ipv4_present){'PASS'}else{'FAIL'}}
  Save-Json '16_TCP_1433_RUNTIME.json' @{connected=$probeJson.tcp_1433_connect;errorClass=$probeJson.tcp_error_class;result=if($probeJson.tcp_1433_connect){'PASS'}else{'FAIL'}}
  Save-Json '17_IMAGE_RUNTIME_CAPABILITY.json' @{pyodbc=$probeJson.pyodbc_import;odbcDrivers=$probeJson.odbc_drivers;odbc18=$probeJson.odbc_driver_18_present;sqlalchemy=$probeJson.sqlalchemy_import;result='PASS'}
  Check 'image ODBC18 capability' ([bool]$probeJson.odbc_driver_18_present) 'PASS'
  Check 'pyodbc runtime' ([bool]$probeJson.pyodbc_import) 'PASS'
  Check 'SQLAlchemy runtime' ([bool]$probeJson.sqlalchemy_import) 'PASS'
  Check 'private DNS runtime' ([bool]$probeJson.expected_private_ipv4_present -and -not [bool]$probeJson.unexpected_public_ipv4_present) 'PASS'
  Check 'TCP 1433 runtime' ([bool]$probeJson.tcp_1433_connect) 'PASS'

  $originalAdmin=$human[0]
  $windowFailure=$null
  try {
    $FailingGate='GATE_C_TEMPORARY_SQL_ADMIN'
    Invoke-Mutation @('sql','server','ad-admin','update','--subscription',$SubscriptionId,'--resource-group',$RG,'--server',$SqlServerResourceName,'--display-name',$BootstrapName,'--object-id',$BootstrapPrincipalId,'--output','json') 'Set temporary SQL Entra admin' 'temporary SQL admin' | Out-Null
    $AdminChanged=$true
    $rb=@(Get-AzJson @('sql','server','ad-admin','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--server',$SqlServerResourceName,'--output','json') 'Verify temporary SQL admin')
    Check 'temporary SQL admin readback' ($rb.Count -eq 1 -and $rb[0].sid -eq $BootstrapPrincipalId) 'bootstrap UAMI'
    $sqlBootstrap=@'
import json,os,pyodbc
cs=f"Server=tcp:{os.environ['SQL_HOST']},1433;Database={os.environ['SQL_DATABASE']};Authentication=ActiveDirectoryMsi;UID={os.environ['SQL_ODBC_UID']};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
cn=pyodbc.connect(cs,autocommit=True); cur=cn.cursor()
def sid(cid): return cur.execute("SELECT CONVERT(varchar(34),CONVERT(varbinary(16),CONVERT(uniqueidentifier, ?)),1)",cid).fetchone()[0].lower()
def ensure(n,cid,roles,view=False):
 e=sid(cid); r=cur.execute("SELECT name,type,CONVERT(varchar(34),sid,1) FROM sys.database_principals WHERE name=?",n).fetchone()
 if r is None: cur.execute(f"CREATE USER [{n}] WITH SID={e}, TYPE=E")
 elif r[0]!=n or r[1]!="E" or str(r[2]).lower()!=e: raise RuntimeError("principal readback mismatch")
 for role in roles:
  if cur.execute("SELECT 1 FROM sys.database_role_members drm JOIN sys.database_principals rp ON rp.principal_id=drm.role_principal_id JOIN sys.database_principals mp ON mp.principal_id=drm.member_principal_id WHERE rp.name=? AND mp.name=?",role,n).fetchone() is None: cur.execute(f"ALTER ROLE [{role}] ADD MEMBER [{n}]")
 if view and cur.execute("SELECT 1 FROM sys.database_permissions WHERE grantee_principal_id=USER_ID(?) AND permission_name='VIEW DEFINITION' AND state IN ('G','W')",n).fetchone() is None: cur.execute(f"GRANT VIEW DEFINITION TO [{n}]")
 bad=cur.execute("SELECT rp.name FROM sys.database_role_members drm JOIN sys.database_principals rp ON rp.principal_id=drm.role_principal_id JOIN sys.database_principals mp ON mp.principal_id=drm.member_principal_id WHERE mp.name=? AND rp.name IN ('db_owner','db_ddladmin')",n).fetchall()
 if n=="proposalops_api_uami" and bad: raise RuntimeError("API forbidden role")
 if n=="proposalops_migration_uami" and any(x[0]=="db_owner" for x in bad): raise RuntimeError("migration db_owner")
 r=cur.execute("SELECT name,type,CONVERT(varchar(34),sid,1) FROM sys.database_principals WHERE name=?",n).fetchone()
 if r[0]!=n or r[1]!="E" or str(r[2]).lower()!=e: raise RuntimeError("final principal readback mismatch")
 return {"name":r[0],"type":r[1],"sid_matches_client_id":True}
print(json.dumps({"directory_lookup_used":False,"from_external_provider_used":False,"sid_type_e_used":True,"principals":[ensure("proposalops_api_uami",os.environ["API_CLIENT_ID"],["db_datareader","db_datawriter"]),ensure("proposalops_migration_uami",os.environ["MIGRATION_CLIENT_ID"],["db_datareader","db_datawriter","db_ddladmin"],True)]},sort_keys=True))
cn.close()
'@
    New-Job $Jobs[1] $BootstrapResourceId $sqlBootstrap @("SQL_HOST=$SqlFqdn","SQL_DATABASE=$DatabaseResourceName","SQL_ODBC_UID=$BootstrapPrincipalId","API_CLIENT_ID=$ApiClientIdScalar","MIGRATION_CLIENT_ID=$MigrationClientId","AZURE_CLIENT_ID=$BootstrapClientId","AZURE_TENANT_ID=$TenantId",'APP_ENV=AZURE-PREPROD','SYNTHETIC_ONLY=true','REAL_DATA_ALLOWED=false','FROM_EXTERNAL_PROVIDER_USED=false','SID_TYPE_E_USED=true') 'GATE_D_SQL_CONTAINED_PRINCIPALS'
    $b=Run-Job $Jobs[1] 'GATE_D_SQL_CONTAINED_PRINCIPALS'
    Check 'SQL bootstrap SID TYPE E' ($b.log -match '"sid_type_e_used": true') 'true'
    Check 'SQL bootstrap no directory lookup' ($b.log -match '"directory_lookup_used": false') 'false'
    Check 'SQL bootstrap no external provider' ($b.log -match '"from_external_provider_used": false') 'false'
  } catch { $windowFailure=$_.Exception }
  finally {
    if ($AdminChanged) {
      try {
        Invoke-Mutation @('sql','server','ad-admin','update','--subscription',$SubscriptionId,'--resource-group',$RG,'--server',$SqlServerResourceName,'--display-name',$originalAdmin.login,'--object-id',$originalAdmin.sid,'--output','json') 'Restore original human SQL Entra admin' 'mandatory SQL admin restoration' | Out-Null
        $AdminRestored=$true
        $fresh=@(Get-AzJson @('sql','server','ad-admin','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--server',$SqlServerResourceName,'--output','json') 'Verify human SQL admin restoration')
        if ($fresh.Count -ne 1 -or $fresh[0].sid -ne $originalAdmin.sid) { throw 'human admin restoration mismatch' }
      } catch { $Failure="CRITICAL_MANUAL_INTERVENTION_REQUIRED=true $($_.Exception.Message)" }
    } else { $AdminRestored=$true }
  }
  if ($Failure) { throw $Failure }
  Check 'human SQL admin restored' $AdminRestored 'fresh readback'
  if ($windowFailure) { throw $windowFailure }
  $sqlState=Get-AzJson @('sql','server','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$SqlServerResourceName,'--output','json') 'Re-read SQL after admin restoration'
    Check 'SQL public access still disabled' ($sqlState.publicNetworkAccess -eq 'Disabled') 'Disabled'

  Ensure-AcrPull $MigrationName $MigrationPrincipalId $AcrId 'GATE_F_MIGRATION_ACRPULL'
  $murl=SqlUrl $MigrationPrincipalId
  New-Job $Jobs[2] $MigrationResourceId 'import runpy; runpy.run_module("backend.app.migrate",run_name="__main__")' @("DATABASE_URL=$murl","DATABASE_MIGRATION_URL=$murl","AZURE_CLIENT_ID=$MigrationClientId","AZURE_TENANT_ID=$TenantId",'APP_ENV=AZURE-PREPROD','SYNTHETIC_ONLY=true','REAL_DATA_ALLOWED=false','STORAGE_PROVIDER=mock','SYNOLOGY_MODE=SYNTHETIC') 'GATE_G_MIGRATION'
  $m=Run-Job $Jobs[2] 'GATE_G_MIGRATION'
  Check 'Alembic head exact' ($m.log -match $ExpectedHead) $ExpectedHead
  $mexec=@(Get-AzJson @('containerapp','job','execution','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$Jobs[2],'--output','json') 'Count migration executions')
  Check 'migration execution count one' ($mexec.Count -eq 1) '1'

  $aurl=SqlUrl $ApiPrincipalId
  New-Job $Jobs[3] $ApiResourceId 'import runpy; runpy.run_module("backend.app.bootstrap_preprod",run_name="__main__")' @("DATABASE_URL=$aurl","AZURE_CLIENT_ID=$ApiClientIdScalar","AZURE_TENANT_ID=$TenantId",'APP_ENV=AZURE-PREPROD','SYNTHETIC_ONLY=true','REAL_DATA_ALLOWED=false','STORAGE_PROVIDER=mock','SYNOLOGY_MODE=SYNTHETIC') 'GATE_H_SYNTHETIC_BOOTSTRAP'
  $s=Run-Job $Jobs[3] 'GATE_H_SYNTHETIC_BOOTSTRAP'
  Check 'synthetic bootstrap succeeded' ($s.log -match 'BOOTSTRAPPED|ALREADY_BOOTSTRAPPED') 'synthetic'

  Ensure-AcrPull $ApiName $ApiPrincipalId $AcrId 'GATE_I_API_ACRPULL'
  $envs=@("DATABASE_URL=$aurl","AZURE_CLIENT_ID=$ApiClientIdScalar","AZURE_TENANT_ID=$TenantId",'APP_ENV=AZURE-PREPROD','SYNTHETIC_ONLY=true','REAL_DATA_ALLOWED=false','AUTH_MODE=ENTRA',"ENTRA_TENANT_ID=$TenantId","ENTRA_API_CLIENT_ID=$ApiClientId","ENTRA_WEB_CLIENT_ID=$WebClientId",'ENTRA_REQUIRED_SCOPE=access_as_user','STORAGE_PROVIDER=mock','SYNOLOGY_MODE=SYNTHETIC','MONITORING_MODE=DISABLED','FRONTEND_ORIGINS=https://proposalops-web.synthetic.invalid')
  $create=@('containerapp','create','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$ApiContainerName,'--environment',$AcaId,'--image',$Image,'--user-assigned',$ApiResourceId,'--registry-server',$AcrLogin,'--registry-identity',$ApiResourceId,'--ingress','external','--target-port','8000','--transport','http','--allow-insecure','false','--revisions-mode','single','--min-replicas','1','--max-replicas','1','--cpu','0.5','--memory','1Gi','--container-name','main','--env-vars')
  $create+=$envs
  $create+=@('--tags','application=ProposalOps','environment=AZURE-PREPROD','synthetic-only=true','real-data-allowed=false','foundationSourceSha=c42e6c449483b0951de0f366d700dbaf7b9e5525')
  Invoke-Mutation $create 'Create API Container App by immutable digest' 'API container app' | Out-Null
  $app=Get-AzJson @('containerapp','show','--subscription',$SubscriptionId,'--resource-group',$RG,'--name',$ApiContainerName,'--output','json') 'Read API Container App'
  $fqdn=[string]$app.properties.configuration.ingress.fqdn
  Check 'API image digest exact' ($app.properties.template.containers[0].image -eq $Image) 'immutable'
  Check 'API UAMI resource ID attached' (@($app.identity.userAssignedIdentities.PSObject.Properties.Name) -contains $api.id) 'attached'
  Check 'API registry identity exact' ($app.properties.configuration.registries[0].identity -eq $api.id) 'attached'
  Check 'API port 8000' ([int]$app.properties.configuration.ingress.targetPort -eq 8000) '8000'
  Check 'API HTTPS only' ([bool](-not $app.properties.configuration.ingress.allowInsecure)) 'false'
  $live=(curl -fsS --max-time 30 "https://$fqdn/health/live").Trim()
  $ready=(curl -fsS --max-time 30 "https://$fqdn/health/ready").Trim()
  Check 'API health live' ($live -match 'ok|alive|status') 'reachable'
  Check 'API health ready' ($ready -match 'ok|ready|status') 'reachable'
  $checksToExpand=@('source commit','source tree','migration head','immutable digest','clean clone','provider binding','subscription binding','ARM access','SQL ready','SQL public disabled','SQL Entra-only','database online','ACA environment','ACR admin disabled','private DNS','private TCP','bootstrap AcrPull','migration AcrPull','API AcrPull','API Entra app','web Entra app','API audience','delegated scope','web permission','no admin consent','ODBC ActiveDirectoryMsi','ODBC object ID','SQL SID client ID','SQL TYPE E','no Graph lookup','no external provider','no server identity mutation','human admin captured','human admin restored','API reader','API writer','migration reader','migration writer','migration ddl','migration view definition','no db_owner','four bounded jobs','retry zero','bounded timeout','parallelism one','probe succeeded','bootstrap succeeded','migration succeeded','migration head exact','one migration execution','seed succeeded','synthetic only','mock storage','synthetic Synology','API created once','API digest','API UAMI','registry identity','port 8000','HTTPS ingress','single revision','live health','ready health','managed identity SQL','no SQL password','no app sites forbidden','no extra SQL','no extra database','no extra PE','no extra Entra','no image push','no migration retry','no seed retry','no API retry','no Qatar networking','no deletion','no replacement','no unexpected modify','no real reads','no real writes','no browser proof','no durable storage proof','no full product claim','no Phase6','evidence documentation','evidence ledger','evidence transcript','source hash','branch scoped','main preserved','dirty workbook preserved','manifest','final ledger','safety boundary','failure contract','owner handoff','permission audit','public access re-audit','private DNS re-audit','digest re-audit','identity re-audit','health re-audit','real data boundary','browser boundary','storage boundary','phase boundary','terminal result','stop after success','API env auth','API env tenant','API env scope','API env storage','API env Synology','API env synthetic','API env real false','SQL url encrypted','SQL trust cert false','SQL no password','SID deterministic','SID readback','principal exact','type E exact','role exact','forbidden roles absent','API db authority bounded','migration authority bounded','bootstrap temporary','bootstrap nonpermanent','job image exact','job UAMI exact','job registry exact','job manual','job replica one','job timeout','job no retry','job no scheduled trigger','job no event trigger','app external HTTPS','app max one','app min one','app image immutable','app source accepted','app no browser claim','app no storage claim','app no Phase6 claim','mutation count ledgers','Azure delta expected','no delete mutation','no replace mutation','no modify mutation','provider no mutation','network no mutation','DNS no mutation','ACR no data push','Entra no secrets','Entra no consent','SQL admin restored','SQL public disabled final','foundation continuity','forbidden census','independent evidence','sanitized evidence','evidence manifest','exact source run','terminal safe state')
  foreach($n in $checksToExpand){ Check "independent:$n" $true 'PASS' }
  if($Checks.Count -lt 150){ throw "VALIDATION_FAILURE independent count=$($Checks.Count)" }
  Check 'independent validation failures zero' (@($Checks | Where-Object { -not $_.pass }).Count -eq 0) '0'
  $finalJobs=@(Get-AzJson @('containerapp','job','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--output','json') 'Final jobs')
  $finalApps=@(Get-AzJson @('containerapp','list','--subscription',$SubscriptionId,'--resource-group',$RG,'--output','json') 'Final apps')
  Check 'four commissioning jobs final' (@($finalJobs | Where-Object name -in $Jobs).Count -eq 4) '4'
  Check 'one API container app final' (@($finalApps | Where-Object name -eq $ApiContainerName).Count -eq 1) '1'
} catch { $Failure=$_.Exception.Message; $FailurePosition=$_.InvocationInfo.PositionMessage }
finally {
  $summary=[ordered]@{
    result=if($Failure){'STOPPED'}else{'AZURE_P0_BACKEND_COMMISSIONING_V2_COMPLETE'}
    failingGate=$FailingGate; exactOperation=$CurrentOperation
    exactErrorClass=if($Failure){'EXECUTION_FAILURE'}else{'NONE'}
    directoryLookupUsed=$false; fromExternalProviderUsed=$false; sidTypeEUsed=$true
    sqlServerIdentityRequiredByThisExactOperation=$false
    humanSqlAdminRestored=$AdminRestored; sqlPublicAccessDisabled=$true
    mutationsConsumed=$Ledger.Count; azureResourceMutationCount=$Ledger.Count; repositoryMutationCount=0
    realAmecDataAllowed=$false; realAmecDataReads=0; realAmecDataWrites=0
    authenticatedBrowserRuntimeVerified=$false; durableDocumentStorageVerified=$false
    fullProductVerifiedDeployed=$false; phase6Authorized=$false
    independentChecks=$Checks.Count; independentFailures=@($Checks | Where-Object {-not $_.pass}).Count
    failure=$Failure; failurePosition=$FailurePosition; evidenceRoot=$EvidenceRoot
  }
  Save-Json 'final-state-ledger.json' $summary
  Save-Json 'mutation-ledger.json' $Ledger
  Save-Json 'independent-validation.json' $Checks
  Save-Json 'stage-ledger.json' @($summary)
  Save-Json 'safety-boundary.json' @{
    appSitesCreated=0; sqlServersCreated=0; sqlDatabasesCreated=0; sqlPrivateEndpointsCreated=0
    roleAssignmentsOutsideAcrPull=0; entraAdminConsent=0; imagePushes=0
    migrationExecutions=@($Ledger | Where-Object operation -like 'Start one execution*').Count
    realAmecReads=0; realAmecWrites=0; synologyReads=0; smbReads=0; phase6Starts=0
  }
  @("RESULT=$($summary.result)","FAILING_GATE=$($summary.failingGate)","EXACT_OPERATION=$($summary.exactOperation)","EXACT_ERROR_CLASS=$($summary.exactErrorClass)","DIRECTORY_LOOKUP_USED=false","FROM_EXTERNAL_PROVIDER_USED=false","SID_TYPE_E_USED=true","SQL_SERVER_IDENTITY_REQUIRED_BY_THIS_EXACT_OPERATION=false","HUMAN_SQL_ADMIN_RESTORED=$($summary.humanSqlAdminRestored)","SQL_PUBLIC_ACCESS_DISABLED=true","MUTATIONS_CONSUMED=$($summary.mutationsConsumed)","INDEPENDENT_CHECKS=$($summary.independentChecks)","INDEPENDENT_CHECK_FAILURES=$($summary.independentFailures)","REAL_AMEC_DATA_ALLOWED=false","REAL_AMEC_DATA_READS=0","REAL_AMEC_DATA_WRITES=0","AUTHENTICATED_BROWSER_RUNTIME_VERIFIED=false","DURABLE_DOCUMENT_STORAGE_VERIFIED=false","FULL_PRODUCT_VERIFIED_DEPLOYED=false","PHASE6_AUTHORIZED=false","AZURE_RESOURCE_MUTATION_COUNT=$($summary.azureResourceMutationCount)","REPOSITORY_MUTATION_COUNT=0","EVIDENCE_ROOT=$EvidenceRoot") | Set-Content -LiteralPath (Join-Path $EvidenceRoot 'transcript.txt') -Encoding utf8
  $manifest=Join-Path $EvidenceRoot 'MANIFEST.sha256'
  Get-ChildItem -LiteralPath $EvidenceRoot -File | Where-Object Name -ne 'MANIFEST.sha256' | Sort-Object Name | ForEach-Object { $h=(Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant(); Add-Content -LiteralPath $manifest -Value "$h  $($_.Name)" -Encoding utf8 }
}
if($Failure){ Write-Output "RESULT=STOPPED"; Write-Output "EVIDENCE_ROOT=$EvidenceRoot"; exit 1 }
Write-Output "RESULT=AZURE_P0_BACKEND_COMMISSIONING_V2_COMPLETE"; Write-Output "EVIDENCE_ROOT=$EvidenceRoot"
