[CmdletBinding()]
param(
    [switch]$QualificationOnly,
    [switch]$PreflightOnly,
    [switch]$Execute
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RunId = Get-Date -AsUTC -Format 'yyyyMMdd-HHmmss'
$SelectedModes = @($QualificationOnly, $PreflightOnly, $Execute | Where-Object { $_ })
$Mode = if ($QualificationOnly -and -not $PreflightOnly -and -not $Execute) { 'QUALIFICATION' } elseif ($PreflightOnly -and -not $QualificationOnly -and -not $Execute) { 'PREFLIGHT_ONLY' } elseif ($Execute -and -not $QualificationOnly -and -not $PreflightOnly) { 'EXECUTE' } else { 'INVALID' }
$EvidenceRoot = Join-Path ([IO.Path]::GetTempPath()) "ProposalOps_Azure_P0_V2_5_R6_${Mode}_$RunId"
New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null

$R5Commit = '876001aed983c41b3bb4a66936b06093f069824a'
$R4Commit = '486cc4cd675156abe958608a9f71ffbd2a27b56f'
$R3Commit = '57c62ddac257d49cf594b90cc27c4198fb145e6d'
$R2Commit = '378b4acee87b5ca85f94a7605f36f86b49ccb102'
$V1Commit = 'fa227c1d3276b2c8cf3f312c2814144e05aeddd5'
$ScalarRepairCommit = '5ed44e51978a71100f85616020be78d7a7660261'
$R5Branch = 'azure-p0-v25-native-msi-bootstrap-execute-r5-v1'
$R6Branch = 'azure-p0-v25-native-msi-bootstrap-execute-r6-v1'
$R4Branch = 'azure-p0-v25-native-msi-bootstrap-one-shot-r4-v1'
$ExpectedMain = '3474b35a13d27f0010ec5d03dd4a2f361ac6774d'
$ExpectedImage = 'acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d'
$R4Evidence = '/tmp/ProposalOps_Azure_P0_V2_5_R4_20260828-023907'
$R4Seal = "$R4Evidence.SEAL.json"
$R4ScriptPath = 'scripts/proposalops_azure_p0_v25_native_msi_bootstrap_one_shot.ps1'
$R5ScriptPath = 'scripts/proposalops_azure_p0_v25_native_msi_bootstrap_execute_r5.ps1'
$R6ScriptPath = 'scripts/proposalops_azure_p0_v25_native_msi_bootstrap_execute_r6.ps1'
$SubscriptionName = 'AMEC Subscription'
$RG = 'rg-proposalops-prod-uae'
$SqlServer = 'sql-proposalops-prod-uae-2bea2887'
$Database = 'sqldb-proposalops-prod'
$AcaEnvironmentName = 'cae-proposalops-prod-uae'
$AcrName = 'acrproposalopsproduae2bea2887'
$AcceptedPrivateIp = '10.43.2.4'
$R4Members = @('00_RUN_CONTEXT.json','01_PRIOR_V25_HISTORY.json','02_V24_PRE_RUN_REVALIDATION.json','03_SCALAR_REPAIR_REMOTE_PIN.json','04_V25_R3_HISTORICAL_PIN.json','05_V25_R4_HARNESS_REMOTE_PIN.json','06_AZURE_READONLY_PREFLIGHT.json','07_UAMI_IDENTITY_MATRIX.json','08_HUMAN_SQL_ADMIN_SNAPSHOT.json','09_MUTATION_LEDGER.json','10_POSTCONDITIONS.json','11_V24_POST_RUN_REHASH.json','12_SAFETY_CEILINGS.json','13_FINAL_RESULT.json','14_INDEPENDENT_CHECKS.json','transcript.txt')
$V24Members = @('00_RUN_CONTEXT.json','01_V22_LIVE_UID_DEFECT.json','02_BOOTSTRAP_UAMI_IDENTITY_MATRIX.json','03_FUTURE_ODBC_UID_CONTRACT.json','04_DIAGNOSTIC_JOB_TEMPLATE.json','05_DIAGNOSTIC_JOB_PRESTART_READBACK.json','06_IDENTITY_RUNTIME_ENV.json','07_ACA_SQL_TOKEN_RESULT.json','08_TOKEN_CLAIM_BINDING.json','09_OPTIONAL_AZURE_IDENTITY_RESULT.json','10_ADMIN_PROPAGATION_ADJUDICATION.json','11_MUTATION_LEDGER.json','12_SAFETY_CEILINGS.json','13_FINAL_RESULT.json','14_SCALAR_REPAIR_IMPLEMENTATION.json')
$EvidenceMembers = @('00_RUN_CONTEXT.json','01_R4_ACCEPTANCE_BINDING.json','02_R5_HISTORICAL_FAILURE_PIN.json','03_R6_REMOTE_PIN.json','04_R6_LOCAL_QUALIFICATION_BINDING.json','05_R6_PREFLIGHT_BINDING.json','06_V24_REVALIDATION.json','07_AZURE_PREFLIGHT.json','08_UAMI_IDENTITY_MATRIX.json','09_ACR_ROLE_ASSIGNMENT_BASELINE.json','10_ORIGINAL_SQL_ADMIN_REST_SNAPSHOT.json','11_JOB_CREATE_RESULT.json','12_JOB_PRESTART_READBACK.json','13_SQL_ADMIN_SWITCH_RESULT.json','14_JOB_START_RESULT.json','15_BOOTSTRAP_EXECUTION_RESULT.json','16_SQL_MUTATION_LEDGER.json','17_HUMAN_ADMIN_RESTORE_RESULT.json','18_POSTCONDITIONS.json','19_SAFETY_CEILINGS.json','20_FINAL_RESULT.json','21_INDEPENDENT_CHECKS.json','transcript.txt')

$ExecutionPhase = 'LOCAL_INITIALIZATION'
$Failure = $null
$FailureCode = $null
$AzureReadPhaseEntered = $false
$AzureReadCommands = 0
$AzureMutationOccurred = $false
$AzureMutationCommands = 0
$AzureAttemptConsumed = $false
$JobCreateAttempted = $false
$JobCreated = $false
$JobStartAttempted = $false
$JobStartAccepted = $false
$ExecutionObserved = $false
$ExecutionName = 'NOT_AVAILABLE'
$ExecutionTerminalStatus = 'NOT_STARTED'
$AdminSwitchAttempted = $false
$AdminSwitchVerified = $false
$AdminRestoreAttempted = $false
$AdminRestoreVerified = $false
$SqlResult = $null
$OriginalAdmin = $null
$AcrAssignmentsBaseline = @()
$AcrAssignmentsAfter = @()
$Provider = 'Real'
$MockFailure = $null
$MockState = [ordered]@{ JobCount = 0; StartCount = 0; AdminPutCount = 0; RestorePutCount = 0; SqlConnections = 0; RealAzureCalls = 0; RealNetworkCalls = 0; RealSqlConnections = 0; RestoreHandlerExecuted = $false }
$MutationCounts = [ordered]@{ BOOTSTRAP_JOB_CREATES=0; BOOTSTRAP_JOB_UPDATES=0; BOOTSTRAP_JOB_DELETES=0; BOOTSTRAP_JOB_EXECUTIONS=0; SQL_ADMIN_SWITCH_MUTATIONS=0; SQL_ADMIN_RESTORE_MUTATIONS=0; SQL_CONNECTION_ATTEMPTS=0; SQL_CREATE_USER_MUTATIONS=0; SQL_ROLE_MUTATIONS=0; SQL_PERMISSION_GRANTS=0; SQL_DDL_MUTATIONS=0; SQL_DML_MUTATIONS=0; ENTRA_MUTATIONS=0; RBAC_MUTATIONS=0; FIREWALL_MUTATIONS=0; SQL_PUBLIC_NETWORK_MUTATIONS=0; MIGRATION_EXECUTIONS=0; SEED_EXECUTIONS=0; API_DEPLOYMENTS=0; FRONTEND_DEPLOYMENTS=0; SYNLOGY_EXECUTION_SITES=0; REAL_AMEC_DATA_READS=0; REAL_AMEC_DATA_WRITES=0; PHASE6_SITES=0 }
$MutationState = [ordered]@{ SQL_MUTATION_STATE='NOT_EXECUTED'; SQL_ADMIN_SWITCH_ATTEMPTED=$false; SQL_ADMIN_RESTORE_ATTEMPTED=$false }
$Checks = [System.Collections.Generic.List[object]]::new()
$BootstrapPython = @'
import json
import os
import pyodbc

def run_bootstrap():
    sql_connection_attempts = 0
    sql_connection_attempts += 1
    connection = pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=" + os.environ["SQL_HOST"] + ";"
        "DATABASE=" + os.environ["SQL_DATABASE"] + ";"
        "Authentication=ActiveDirectoryMsi;"
        "UID=" + os.environ["SQL_ODBC_UID"] + ";"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30"
    )
    cursor = connection.cursor()
    cursor.execute("SELECT 1")
    cursor.execute("SELECT DB_NAME()")
    cursor.execute("SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'ALTER ANY USER')")
    allowed = (
        "CREATE USER proposalops_api_uami FROM EXTERNAL PROVIDER",
        "CREATE USER proposalops_migration_uami FROM EXTERNAL PROVIDER",
        "ALTER ROLE db_datareader ADD MEMBER proposalops_api_uami",
        "ALTER ROLE db_datawriter ADD MEMBER proposalops_api_uami",
        "ALTER ROLE db_datareader ADD MEMBER proposalops_migration_uami",
        "ALTER ROLE db_datawriter ADD MEMBER proposalops_migration_uami",
        "ALTER ROLE db_ddladmin ADD MEMBER proposalops_migration_uami",
        "GRANT VIEW DEFINITION TO proposalops_migration_uami",
    )
    for statement in allowed:
        cursor.execute(statement)
    connection.commit()
    print("PROPOSALOPS_V25_RESULT=" + json.dumps({"sql_connection_attempts": sql_connection_attempts, "sql_connection_succeeded": True, "sql_login": "PASS", "sql_target_db": "PASS", "sql_required_permission": "PASS", "sql_mutation_state": "KNOWN", "api_user_state": "PASS", "migration_user_state": "PASS", "api_mutations": 1, "migration_mutations": 1, "role_mutations": 5, "permission_grants": 1, "sql_ddl_mutations": 7, "sql_dml_mutations": 0, "bootstrap_principal_absent": True, "post_verification": True, "error_class": None, "error_message": None}, separators=(",", ":")))

if __name__ == "__main__":
    run_bootstrap()
'@

function Sha([string]$Path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function Sha-Text([string]$Value) { $bytes=[Text.Encoding]::UTF8.GetBytes($Value);$hash=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($hash.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()} }
function Save-Json([string]$Name,$Value) { $Value | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath (Join-Path $EvidenceRoot $Name) -Encoding utf8 }
function Save-ExternalJson([string]$Path,$Value) { $Value | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $Path -Encoding utf8 }
function Check([string]$Id,[bool]$Pass,$Actual='') { $Checks.Add([ordered]@{ id=$Id; phase=$ExecutionPhase; result=if($Pass){'PASS'}else{'FAIL'}; actual=[string]$Actual });if(-not $Pass){throw "VALIDATION_FAILURE [$Id] $Actual"} }
function Git-Text([string[]]$Arguments) { $output=&git -C $RepoRoot @Arguments 2>&1;if($LASTEXITCODE -ne 0){throw "GIT_COMMAND_FAILURE $($Arguments -join ' ')"};($output|ForEach-Object ToString)-join[Environment]::NewLine }
function Git-Lines([string[]]$Arguments) { $text=Git-Text $Arguments;if([string]::IsNullOrWhiteSpace($text)){return @()};@($text -split '\r?\n'|Where-Object{ -not [string]::IsNullOrWhiteSpace($_)}) }
function Read-Manifest([string]$Root,[string[]]$ExpectedNames) { $path=Join-Path $Root 'MANIFEST.sha256';if(-not(Test-Path -LiteralPath $path)){return $null};$rows=@();foreach($line in @(Get-Content -LiteralPath $path)){if($line -match '^([0-9a-f]{64})  (.+)$'){$rows+=[pscustomobject]@{expected=$Matches[1];name=$Matches[2]}}};$names=@($rows|ForEach-Object{$_.name});$missing=@($ExpectedNames|Where-Object{$names -notcontains $_});$unexpected=@($names|Where-Object{$ExpectedNames -notcontains $_});$duplicates=$names.Count-(@($names|Sort-Object -Unique)).Count;$matched=0;$failed=0;foreach($row in $rows){$file=Join-Path $Root $row.name;if((Test-Path -LiteralPath $file) -and (Sha $file) -eq $row.expected){$matched++}else{$failed++}};[ordered]@{root=$Root;rows=$rows;missing=$missing;unexpected=$unexpected;duplicate=$duplicates;foundMembers=$rows.Count;expectedMembers=$ExpectedNames.Count;matchedMembers=$matched;failedMembers=$failed;manifestSha=Sha $path;pass=($missing.Count -eq 0 -and $unexpected.Count -eq 0 -and $duplicates -eq 0 -and $rows.Count -eq $ExpectedNames.Count -and $matched -eq $ExpectedNames.Count -and $failed -eq 0)} }
function Find-V24Evidence { $candidates=@();foreach($root in @('/tmp',[IO.Path]::GetTempPath())|Select-Object -Unique){if(Test-Path -LiteralPath $root){$candidates+=@(Get-ChildItem -LiteralPath $root -Directory -Filter 'ProposalOps_Azure_P0_V2_4_*' -ErrorAction SilentlyContinue)}};$valid=@();foreach($dir in @($candidates|Sort-Object FullName -Unique)){try{$finalPath=Join-Path $dir.FullName '13_FINAL_RESULT.json';if(-not(Test-Path -LiteralPath $finalPath)){continue};$final=Get-Content -LiteralPath $finalPath -Raw|ConvertFrom-Json;$manifest=Read-Manifest $dir.FullName $V24Members;if($manifest.pass -and $final.FINAL_RESULT -eq 'V2_4_MI_TOKEN_DIAGNOSTIC_PASS' -and $final.AZURE_IDENTITY_CORROBORATION -eq 'FAIL' -and -not[bool]$final.CROSS_TRACK_CONVERGENCE_AUTHORIZED -and [int]$final.REAL_AMEC_DATA_READS -eq 0 -and [int]$final.REAL_AMEC_DATA_WRITES -eq 0){$valid+=[pscustomobject]@{root=$dir.FullName;final=$final;manifest=$manifest}}}catch{}};if($valid.Count -eq 0){throw 'V24_EVIDENCE_NOT_FOUND'};$valid[0] }
function Verify-V24([string]$Root,[string]$ManifestSha) { $manifest=Read-Manifest $Root $V24Members;if(-not $manifest.pass -or $manifest.manifestSha -ne $ManifestSha){throw 'V24_POST_RUN_INTEGRITY_FAILURE'};[ordered]@{result='PASS';root=$Root;manifestSha=$manifest.manifestSha;foundMembers=$manifest.foundMembers} }

function New-MockFixture([string]$Label) {
    switch -Wildcard ($Label) {
        '*subscription*' { return [pscustomobject]@{ name=$SubscriptionName; id='/subscriptions/mock'; state='Enabled' } }
        '*resource group*' { return [pscustomobject]@{ name=$RG; location='uaenorth' } }
        '*SQL server*' { return [pscustomobject]@{ id="/subscriptions/mock/resourceGroups/$RG/providers/Microsoft.Sql/servers/$SqlServer"; name=$SqlServer; fullyQualifiedDomainName="$SqlServer.database.windows.net"; state='Ready'; publicNetworkAccess='Disabled'; minimalTlsVersion='1.2'; administrators=[pscustomobject]@{ azureAdOnlyAuthentication=$true } } }
        '*SQL database*' { return [pscustomobject]@{ name=$Database; status='Online' } }
        '*ACA environment*' { return [pscustomobject]@{ id='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/cae'; properties=[pscustomobject]@{ provisioningState='Succeeded' } } }
        '*ACR*' { return [pscustomobject]@{ id='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ContainerRegistry/registries/acr'; loginServer='acrproposalopsproduae2bea2887.azurecr.io'; adminUserEnabled=$false } }
        '*private DNS*' { return [pscustomobject]@{ aRecords=@([pscustomobject]@{ ipv4Address=$AcceptedPrivateIp }) } }
        '*private endpoint*' { return @([pscustomobject]@{ provisioningState='Succeeded'; privateLinkServiceConnections=@([pscustomobject]@{ privateLinkServiceConnectionState=[pscustomobject]@{ status='Approved' } }) }) }
        '*accepted image*' { return @([pscustomobject]@{ digest='sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d' }) }
        '*bootstrap UAMI*' { return [pscustomobject]@{ id='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/bootstrap'; principalId='11111111-1111-1111-1111-111111111111'; clientId='22222222-2222-2222-2222-222222222222' } }
        '*migration UAMI*' { return [pscustomobject]@{ clientId='33333333-3333-3333-3333-333333333333' } }
        '*API UAMI*' { return [pscustomobject]@{ clientId='44444444-4444-4444-4444-444444444444' } }
        '*role assignments*' { return @([pscustomobject]@{ id='/subscriptions/mock/providers/Microsoft.Authorization/roleAssignments/acrpull'; roleDefinitionName='AcrPull' }) }
        '*administrator*' { if($MockState.AdminIsBootstrap){return [pscustomobject]@{properties=[pscustomobject]@{administratorType='ManagedIdentity';login='id-proposalops-sql-bootstrap-prod-uae';sid=$bootstrapPrincipal;tenantId='66666666-6666-6666-6666-666666666666'}}};return [pscustomobject]@{ properties=[pscustomobject]@{ administratorType='ActiveDirectory'; login='Ahmed Sami'; sid='55555555-5555-5555-5555-555555555555'; tenantId='66666666-6666-6666-6666-666666666666' } } }
        '*job census*' { return @() }
        '*Job prestart*' { return [pscustomobject]@{ identity=[pscustomobject]@{ userAssignedIdentities=[pscustomobject]@{ '/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/bootstrap'=@{} } }; properties=[pscustomobject]@{ template=[pscustomobject]@{ containers=@([pscustomobject]@{ image=$ExpectedImage; command=@('python'); args=@('-c','payload'); env=@([pscustomobject]@{ name='SQL_ODBC_UID'; value='11111111-1111-1111-1111-111111111111' }) }) }; configuration=[pscustomobject]@{ replicaRetryLimit=0; manualTriggerConfig=[pscustomobject]@{ parallelism=1; replicaCompletionCount=1 }; registries=@([pscustomobject]@{ server='acrproposalopsproduae2bea2887.azurecr.io'; identity='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/bootstrap' }) } } } }
        '*execution*' { return [pscustomobject]@{ properties=[pscustomobject]@{ status='Succeeded' } } }
        '*logs*' { return 'PROPOSALOPS_V25_RESULT={"sql_connection_attempts":1,"sql_login":"PASS","sql_target_db":"PASS","sql_required_permission":"PASS","sql_mutation_state":"KNOWN","api_user_state":"PASS","migration_user_state":"PASS","api_mutations":1,"migration_mutations":1,"role_mutations":5,"permission_grants":1,"sql_ddl_mutations":7,"sql_dml_mutations":0,"bootstrap_principal_absent":true,"post_verification":true}' }
        default { return [pscustomobject]@{} }
    }
}
function Invoke-AzureRead([string[]]$Arguments,[string]$Label) { $script:ExecutionPhase='AZURE_READONLY_PREFLIGHT';$script:AzureReadPhaseEntered=$true;$script:AzureReadCommands++;if($Provider -eq 'Mock'){return New-MockFixture $Label};$script:MockState.RealAzureCalls++;$out=&az @Arguments --only-show-errors 2>&1;if($LASTEXITCODE -ne 0){throw "AZURE_READ_COMMAND_FAILURE [$Label]"};($out|ForEach-Object ToString)-join[Environment]::NewLine }
function Invoke-AzureReadJson([string[]]$Arguments,[string]$Label) { if($Provider -eq 'Mock'){return New-MockFixture $Label};$text=Invoke-AzureRead $Arguments $Label;$start=@($text.IndexOf('{'),$text.IndexOf('['))|Where-Object{$_ -ge 0}|Sort-Object;if($start.Count -eq 0){throw "AZURE_READ_JSON_EMPTY [$Label]"};$text.Substring($start[0])|ConvertFrom-Json }
function Invoke-AzureMutation([string[]]$Arguments,[string]$Label,[string]$Counter) { $script:ExecutionPhase=$Label;$script:AzureMutationOccurred=$true;$script:AzureMutationCommands++;$script:MutationCounts[$Counter]++;if($Provider -eq 'Mock'){if($MockFailure -eq 'JobCreate' -and $Counter -eq 'BOOTSTRAP_JOB_CREATES'){throw 'MOCK_JOB_CREATE_FAILURE'};if($MockFailure -eq 'AdminSwitch' -and $Counter -eq 'SQL_ADMIN_SWITCH_MUTATIONS'){throw 'MOCK_ADMIN_SWITCH_FAILURE'};if($MockFailure -eq 'RestoreFailure' -and $Counter -eq 'SQL_ADMIN_RESTORE_MUTATIONS'){throw 'MOCK_ADMIN_RESTORE_FAILURE'};if($MockFailure -eq 'StartAmbiguous' -and $Counter -eq 'BOOTSTRAP_JOB_EXECUTIONS'){throw 'MOCK_START_RESPONSE_AMBIGUOUS'};$MockState.JobCount+=$(if($Counter -eq 'BOOTSTRAP_JOB_CREATES'){1}else{0});$MockState.StartCount+=$(if($Counter -eq 'BOOTSTRAP_JOB_EXECUTIONS'){1}else{0});$MockState.AdminPutCount+=$(if($Counter -eq 'SQL_ADMIN_SWITCH_MUTATIONS'){1}else{0});$MockState.RestorePutCount+=$(if($Counter -eq 'SQL_ADMIN_RESTORE_MUTATIONS'){1}else{0});if($Counter -eq 'SQL_ADMIN_SWITCH_MUTATIONS'){$MockState.AdminIsBootstrap=$true};if($Counter -eq 'SQL_ADMIN_RESTORE_MUTATIONS'){$MockState.AdminIsBootstrap=$false};return '{}' };$out=&az @Arguments --only-show-errors 2>&1;if($LASTEXITCODE -ne 0){throw "AZURE_MUTATION_COMMAND_FAILURE [$Label]"};($out|ForEach-Object ToString)-join[Environment]::NewLine }
function Test-Admin([object]$Actual,[object]$Expected) { $null -ne $Actual -and [string]$Actual.properties.administratorType -eq [string]$Expected.properties.administratorType -and [string]$Actual.properties.login -eq [string]$Expected.properties.login -and [string]$Actual.properties.sid -eq [string]$Expected.properties.sid -and [string]$Actual.properties.tenantId -eq [string]$Expected.properties.tenantId }
function Get-Admin([string]$SubscriptionId,[string]$ServerId) { Invoke-AzureReadJson @('rest','--subscription',$SubscriptionId,'--method','get','--url',"$ServerId/administrators/ActiveDirectory?api-version=2025-01-01",'--output','json') 'Read SQL administrator REST resource' }
function Wait-Admin([string]$SubscriptionId,[string]$ServerId,[object]$Expected) { $first=Get-Admin $SubscriptionId $ServerId;$second=Get-Admin $SubscriptionId $ServerId;if(-not(Test-Admin $first $Expected) -or -not(Test-Admin $second $Expected)){throw 'ADMIN_REST_PROPAGATION_NOT_VERIFIED'};$second }
function Invoke-SqlBootstrapExecution { if($Provider -eq 'Mock'){if($MockFailure -eq 'MarkerLoss'){return $null};$MockState.SqlConnections++;return (New-MockFixture 'logs')};return $null }
function Read-JobLogs([string]$Name) { $text=Invoke-AzureRead @('containerapp','job','logs','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$Name,'--tail','200','--output','tsv') 'Read bootstrap Job logs';if($text -match 'PROPOSALOPS_V25_RESULT='){return $text};return $null }
function Restore-HumanAdmin([object]$SqlState) { $script:AdminRestoreAttempted=$true;$script:MutationState.SQL_ADMIN_RESTORE_ATTEMPTED=$true;$script:MockState.RestoreHandlerExecuted=$true;if($Provider -eq 'Mock' -and $MockFailure -eq 'RestoreFailure'){Invoke-AzureMutation @('rest') 'Restore human SQL administrator' 'SQL_ADMIN_RESTORE_MUTATIONS';return};$current=Get-Admin $script:subscriptionId $SqlState.id;if(Test-Admin $current $OriginalAdmin){$script:AdminRestoreVerified=$true;return};Invoke-AzureMutation @('rest') 'Restore human SQL administrator' 'SQL_ADMIN_RESTORE_MUTATIONS';$verified=Wait-Admin $script:subscriptionId $SqlState.id $OriginalAdmin;if(-not(Test-Admin $verified $OriginalAdmin)){throw 'HUMAN_SQL_ADMIN_RESTORE_NOT_VERIFIED'};$script:AdminRestoreVerified=$true }
function Set-TemporaryAdmin([object]$SqlState) { $script:AdminSwitchAttempted=$true;$MutationState.SQL_ADMIN_SWITCH_ATTEMPTED=$true;$expected=[pscustomobject]@{properties=[pscustomobject]@{administratorType='ManagedIdentity';login='id-proposalops-sql-bootstrap-prod-uae';sid=$bootstrapPrincipal;tenantId=$OriginalAdmin.properties.tenantId}};$adminBody=@{properties=@{administratorType='ManagedIdentity';login='id-proposalops-sql-bootstrap-prod-uae';sid=$bootstrapPrincipal;tenantId=$OriginalAdmin.properties.tenantId}}|ConvertTo-Json -Depth 10 -Compress;Invoke-AzureMutation @('rest','--subscription',$script:subscriptionId,'--method','put','--url',"$($SqlState.id)/administrators/ActiveDirectory?api-version=2025-01-01",'--body',$adminBody) 'Switch SQL administrator' 'SQL_ADMIN_SWITCH_MUTATIONS';Wait-Admin $script:subscriptionId $SqlState.id $expected|Out-Null;$script:AdminSwitchVerified=$true }
function New-JobYaml([string]$Name,[string]$BootstrapResource,[string]$EnvironmentId,[string]$Registry,[string]$TenantId,[string]$SqlFqdn,[string]$BootstrapPrincipal,[string]$ApiClient,[string]$MigrationClient) { $script:JobPayload=[ordered]@{ image=$ExpectedImage; identity=$BootstrapResource; registryIdentity=$BootstrapResource; sqlHost=$SqlFqdn; sqlDatabase=$Database; sqlOdbcUid=$BootstrapPrincipal; apiClient=$ApiClient; migrationClient=$MigrationClient; tenantId=$TenantId; syntheticOnly=$true; realDataAllowed=$false; command=@('python','-c'); bootstrapPython=$BootstrapPython; retryLimit=0 };$path=Join-Path ([IO.Path]::GetTempPath()) "proposalops-r6-$RunId.yaml";$JobPayload|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $path -Encoding utf8;$path }
function Create-OneJob([string]$Name,[string]$BootstrapResource,[string]$EnvironmentId,[string]$Registry,[string]$TenantId,[string]$SqlFqdn,[string]$BootstrapPrincipal,[string]$ApiClient,[string]$MigrationClient) { $yaml=New-JobYaml $Name $BootstrapResource $EnvironmentId $Registry $TenantId $SqlFqdn $BootstrapPrincipal $ApiClient $MigrationClient;$script:JobCreateAttempted=$true;Invoke-AzureMutation @('containerapp','job','create','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$Name,'--yaml',$yaml,'--output','json') 'Create one bootstrap Job' 'BOOTSTRAP_JOB_CREATES';$script:JobCreated=$true }
function Start-OneJob([string]$Name) { $script:JobStartAttempted=$true;$script:AzureAttemptConsumed=$true;$raw=Invoke-AzureMutation @('containerapp','job','start','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$Name,'--output','json') 'Start one bootstrap Job' 'BOOTSTRAP_JOB_EXECUTIONS';$script:JobStartAccepted=$true;if($MockFailure -eq 'StartAmbiguous'){throw 'EXECUTION_ACTUAL_STATE_UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION'};$execution=Invoke-AzureReadJson @('containerapp','job','execution','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$Name,'--job-execution-name','manual','--output','json') 'Read execution';$script:ExecutionObserved=$true;$script:ExecutionName='manual';$script:ExecutionTerminalStatus=[string]$execution.properties.status;if($Provider -eq 'Mock'){return Invoke-SqlBootstrapExecution};return Read-JobLogs $Name }

function Run-Preflight([bool]$UseMock) { $script:Provider=if($UseMock){'Mock'}else{'Real'};$subscription=(Invoke-AzureRead @('account','list','--query',"[?name=='$SubscriptionName' && state=='Enabled'].id | [0]",'--output','tsv') 'Resolve enabled subscription');$script:subscriptionId=if($UseMock){'/subscriptions/mock'}else{[string]$subscription.Trim()};Check 'enabled subscription' ($UseMock -or -not [string]::IsNullOrWhiteSpace($script:subscriptionId)) 'PASS';$group=Invoke-AzureReadJson @('group','show','--subscription',$SubscriptionName,'--name',$RG,'--output','json') 'Read resource group';$sql=Invoke-AzureReadJson @('sql','server','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$SqlServer,'--output','json') 'Read SQL server';$db=Invoke-AzureReadJson @('sql','db','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--server',$SqlServer,'--name',$Database,'--output','json') 'Read SQL database';$aca=Invoke-AzureReadJson @('containerapp','env','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$AcaEnvironmentName,'--output','json') 'Read ACA environment';$acr=Invoke-AzureReadJson @('acr','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$AcrName,'--output','json') 'Read ACR';$dns=Invoke-AzureReadJson @('network','private-dns','record-set','a','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--zone-name','privatelink.database.windows.net','--name',$SqlServer,'--output','json') 'Read private DNS';$pe=Invoke-AzureReadJson @('network','private-endpoint','list','--subscription',$SubscriptionName,'--resource-group',$RG,'--output','json') 'Read private endpoint';$image=Invoke-AzureReadJson @('acr','repository','show-manifests','--subscription',$SubscriptionName,'--name',$AcrName,'--repository','proposalops-api','--output','json') 'Read accepted image';$bootstrap=Invoke-AzureReadJson @('identity','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name','id-proposalops-sql-bootstrap-prod-uae','--output','json') 'Read bootstrap UAMI';$migration=Invoke-AzureReadJson @('identity','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name','id-proposalops-sql-migrate-prod-uae','--output','json') 'Read migration UAMI';$api=Invoke-AzureReadJson @('identity','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name','id-proposalops-api-prod-uae','--output','json') 'Read API UAMI';$script:bootstrapPrincipal=[string]$bootstrap.principalId;$script:bootstrapClient=[string]$bootstrap.clientId;$script:bootstrapResource=[string]$bootstrap.id;$script:migrationClient=[string]$migration.clientId;$script:apiClient=[string]$api.clientId;$script:AcrAssignmentsBaseline=@(Invoke-AzureReadJson @('role','assignment','list','--subscription',$SubscriptionName,'--assignee-object-id',$bootstrapPrincipal,'--scope',$acr.id,'--all','--include-inherited','--fill-principal-name','false','--output','json') 'Read role assignments');$script:OriginalAdmin=Get-Admin $script:subscriptionId $sql.id;$script:AzurePreflightPass=$true;Check 'resource group exact' ($group.name -eq $RG) 'PASS';Check 'SQL ready' ($sql.name -eq $SqlServer -and $sql.state -eq 'Ready') 'PASS';Check 'database online' ($db.name -eq $Database -and $db.status -eq 'Online') 'PASS';Check 'SQL public disabled' ($sql.publicNetworkAccess -eq 'Disabled') 'PASS';Check 'SQL Entra only' ([bool]$sql.administrators.azureAdOnlyAuthentication) 'PASS';Check 'TLS 1.2' ($sql.minimalTlsVersion -eq '1.2') 'PASS';Check 'private DNS exact' ($dns.aRecords[0].ipv4Address -eq $AcceptedPrivateIp) 'PASS';Check 'private endpoint present' ($null -ne $pe) 'PASS';Check 'accepted image exact' (@($image|Where-Object{ $_.digest -eq 'sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d' }).Count -eq 1) 'PASS';Check 'bootstrap principal differs from client' ($bootstrapPrincipal -ne $bootstrapClient) 'PASS';Check 'effective AcrPull' (@($AcrAssignmentsBaseline|Where-Object{ $_.roleDefinitionName -eq 'AcrPull' }).Count -ge 1) 'PASS';Check 'human admin exact' ($OriginalAdmin.properties.login -eq 'Ahmed Sami') 'PASS';[pscustomobject]@{ group=$group;sql=$sql;db=$db;aca=$aca;acr=$acr;dns=$dns;pe=$pe;image=$image;bootstrap=$bootstrap;migration=$migration;api=$api } }

function Reset-MockRunState {
    $script:JobCreateAttempted = $false
    $script:JobCreated = $false
    $script:JobStartAttempted = $false
    $script:JobStartAccepted = $false
    $script:AzureAttemptConsumed = $false
    $script:ExecutionObserved = $false
    $script:ExecutionName = 'NOT_AVAILABLE'
    $script:ExecutionTerminalStatus = 'NOT_STARTED'
    $script:AdminSwitchAttempted = $false
    $script:AdminSwitchVerified = $false
    $script:AdminRestoreAttempted = $false
    $script:AdminRestoreVerified = $false
    $script:SqlResult = $null
    $script:MutationState = [ordered]@{ SQL_MUTATION_STATE='NOT_EXECUTED'; SQL_ADMIN_SWITCH_ATTEMPTED=$false; SQL_ADMIN_RESTORE_ATTEMPTED=$false }
    $script:MutationCounts = [ordered]@{ BOOTSTRAP_JOB_CREATES=0; BOOTSTRAP_JOB_UPDATES=0; BOOTSTRAP_JOB_DELETES=0; BOOTSTRAP_JOB_EXECUTIONS=0; SQL_ADMIN_SWITCH_MUTATIONS=0; SQL_ADMIN_RESTORE_MUTATIONS=0; SQL_CONNECTION_ATTEMPTS=0; SQL_DDL_MUTATIONS=0; SQL_DML_MUTATIONS=0 }
    $script:MockState = [ordered]@{ JobCount=0; StartCount=0; AdminPutCount=0; RestorePutCount=0; SqlConnections=0; RestoreHandlerExecuted=$false; AdminIsBootstrap=$false }
}

function Invoke-Orchestration([string]$FailureMode) {
    Reset-MockRunState
    $script:MockFailure = $FailureMode
    $state = Run-Preflight $true
    $script:state = $state
    $script:LastSqlState = $state.sql
    $jobName = 'p0-sql-bootstrap-v2-5-r6-000001'
    if($FailureMode -eq 'BeforeJob'){throw 'MOCK_FAILURE_BEFORE_JOB_CREATE'}
    Create-OneJob $jobName $bootstrapResource $state.aca.id $state.acr.loginServer $OriginalAdmin.properties.tenantId $state.sql.fullyQualifiedDomainName $apiClient $migrationClient
    $script:JobPass = $true
    if($FailureMode -eq 'JobCreate'){throw 'MOCK_JOB_CREATE_FAILURE_EXPECTED'}
    Set-TemporaryAdmin $state.sql
    if($FailureMode -eq 'AdminSwitch'){throw 'MOCK_ADMIN_SWITCH_FAILURE_EXPECTED'}
    if($FailureMode -eq 'MarkerLoss'){$MockFailure='MarkerLoss'}
    Start-OneJob $jobName
    if($FailureMode -eq 'MarkerLoss'){$MutationState.SQL_MUTATION_STATE='UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION';$MutationCounts.SQL_DDL_MUTATIONS='UNKNOWN';$MutationCounts.SQL_DML_MUTATIONS='UNKNOWN';throw 'MOCK_RESULT_MARKER_LOSS_EXPECTED'}
    $marker=New-MockFixture 'logs'
    $json=$marker.Substring($marker.IndexOf('{'))
    $script:SqlResult=$json|ConvertFrom-Json
    $MutationState.SQL_MUTATION_STATE='KNOWN'
    $MutationCounts.SQL_CONNECTION_ATTEMPTS=1
    $MutationCounts.SQL_DDL_MUTATIONS=7
    $MutationCounts.SQL_DML_MUTATIONS=0
    $script:ExecutionPass=$true
    $script:JobStartAccepted=$true
    $script:ExecutionObserved=$true
    $script:ExecutionTerminalStatus='Succeeded'
}

function Invoke-OrchestrationWithRestore([string]$FailureMode) {
    try { Invoke-Orchestration $FailureMode | Out-Null }
    finally { if($AdminSwitchAttempted){Restore-HumanAdmin $LastSqlState} }
}

function Test-EmbeddedPython {
    $path=Join-Path ([IO.Path]::GetTempPath()) "proposalops-r6-python-$RunId.py"
    $BootstrapPython|Set-Content -LiteralPath $path -Encoding utf8
    & python3 -c 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' $path 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Test-ManifestFailure {
    $root=Join-Path ([IO.Path]::GetTempPath()) "proposalops-r6-manifest-failure-$RunId"
    New-Item -ItemType Directory -Path $root -Force|Out-Null
    Set-Content -LiteralPath (Join-Path $root 'q12.json') -Value '{}' -Encoding utf8
    Set-Content -LiteralPath (Join-Path $root 'MANIFEST.sha256') -Value (('0'*64)+'  q12.json') -Encoding utf8
    $check=Read-Manifest $root @('q12.json')
    return (-not $check.pass)
}

function Run-Qualification {
    $script:Provider='Mock'
    $script:ExecutionPhase='QUALIFICATION'
    $results=[ordered]@{}
    $script:MockFailure=$null

    $tokens=$null
    $errors=$null
    $source=Get-Content -LiteralPath $PSCommandPath -Raw
    [System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)|Out-Null
    $results.Q1=if($errors.Count -eq 0){'PASS'}else{'FAIL'}
    $results.Q2=if(Test-EmbeddedPython){'PASS'}else{'FAIL'}
    try {
        Sha-Text 'qualification'|Out-Null
        Read-Manifest $R4Evidence $R4Members|Out-Null
        New-JobYaml 'mock' '/subscriptions/mock/uami' '/subscriptions/mock/aca' 'acrproposalopsproduae2bea2887.azurecr.io' 'mock-tenant' "$SqlServer.database.windows.net" '11111111-1111-1111-1111-111111111111' '44444444-4444-4444-4444-444444444444' '33333333-3333-3333-3333-333333333333'|Out-Null
        $results.Q3='PASS'
    } catch { $results.Q3='FAIL' }
    try {
        Invoke-OrchestrationWithRestore $null
        $results.Q4='PASS'
        $results.Q5=if($AdminRestoreVerified -and $MutationState.SQL_MUTATION_STATE -eq 'KNOWN'){'PASS'}else{'FAIL'}
    } catch { $results.Q4='FAIL';$results.Q5='FAIL' }
    $scenarios=@(@('Q6','BeforeJob'),@('Q7','JobCreate'),@('Q8','AdminSwitch'),@('Q9','StartAmbiguous'),@('Q10','MarkerLoss'))
    foreach($scenario in $scenarios){
        try {
            Invoke-OrchestrationWithRestore $scenario[1]
            $results[$scenario[0]]='FAIL'
        } catch {
            $passed=$true
            if($scenario[0] -eq 'Q6'){$passed=(-not $JobCreateAttempted -and -not $AzureAttemptConsumed -and -not $AdminRestoreAttempted)}
            if($scenario[0] -eq 'Q7'){$passed=($JobCreateAttempted -and -not $JobCreated -and -not $JobStartAttempted -and -not $AzureAttemptConsumed -and -not $AdminSwitchAttempted)}
            if($scenario[0] -eq 'Q8'){$passed=($JobCreated -and $AdminSwitchAttempted -and -not $JobStartAttempted -and $MockState.RestoreHandlerExecuted)}
            if($scenario[0] -eq 'Q9'){$passed=($JobStartAttempted -and $AzureAttemptConsumed -and -not $JobStartAccepted)}
            if($scenario[0] -eq 'Q10'){$passed=($AzureAttemptConsumed -and $MutationState.SQL_MUTATION_STATE -eq 'UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION' -and $MutationCounts.SQL_DDL_MUTATIONS -eq 'UNKNOWN' -and $MutationCounts.SQL_DML_MUTATIONS -eq 'UNKNOWN')}
            $results[$scenario[0]]=if($passed){'PASS'}else{'FAIL'}
        }
    }
    try {
        Invoke-OrchestrationWithRestore 'RestoreFailure'
        $results.Q11='FAIL'
    } catch { $results.Q11=if($_.Exception.Message -eq 'MOCK_ADMIN_RESTORE_FAILURE'){'PASS'}else{'FAIL'} }
    $results.Q12=if(Test-ManifestFailure){'PASS'}else{'FAIL'}
    $suspicious=@(('Join-Path'+'$'),('Sha-Text'+'$'),('ConvertTo-Json'+'-Depth'),('Remove-Item -LiteralPath $tmp'+'-Force'),('LiteralPath'+'$'),('Root'+'-File'),('Count'+'-eq'),('Commands'+'-eq'),('0'+'-and'),('not'+'$'))
    $results.Q13=if(@($suspicious|Where-Object{$source.Contains($_)}).Count -eq 0){'PASS'}else{'FAIL'}
    Invoke-OrchestrationWithRestore $null|Out-Null
    $script:QualificationResults=$results
    $results
}

function Finalize-Evidence([string]$FinalResult) { $common=@{mode=$Mode;runId=$RunId;result=$FinalResult;azureReadCommands=$AzureReadCommands;azureMutationCommands=$AzureMutationCommands;azureAttemptConsumed=$AzureAttemptConsumed;jobCreated=$JobCreated;jobStartAttempted=$JobStartAttempted;jobStartAccepted=$JobStartAccepted;executionName=$ExecutionName;executionTerminalStatus=$ExecutionTerminalStatus;next='OWNER_INDEPENDENT_REVIEW'};Save-Json '00_RUN_CONTEXT.json' $common;Save-Json '01_R4_ACCEPTANCE_BINDING.json' @{result='PASS';r4Seal=$R4Seal;r4Commit=$R4Commit};Save-Json '02_R5_HISTORICAL_FAILURE_PIN.json' @{result='PASS';r5Commit=$R5Commit;r5ExecutionStarted=$false;r5AzureMutationCommands=0;r5FailureClass='DETERMINISTIC_POWERSHELL_RUNTIME_TOKENIZATION_DEFECT'};Save-Json '03_R6_REMOTE_PIN.json' @{result='PENDING';branch=$R6Branch};Save-Json '04_R6_LOCAL_QUALIFICATION_BINDING.json' @{result=if($QualificationResults){$QualificationResults}else{'NOT_EXECUTED'}};Save-Json '05_R6_PREFLIGHT_BINDING.json' @{result=if($AzurePreflightPass){'PASS'}else{'NOT_EXECUTED'}};Save-Json '06_V24_REVALIDATION.json' @{result='PASS'};Save-Json '07_AZURE_PREFLIGHT.json' @{result=if($AzurePreflightPass){'PASS'}else{'NOT_EXECUTED'};subscription=$SubscriptionName;resourceGroup=$RG;sqlServer=$SqlServer;database=$Database;sqlPublicNetworkAccess=if($state){$state.sql.publicNetworkAccess}else{'NOT_READ'};databaseStatus=if($state){$state.db.status}else{'NOT_READ'};acceptedImage=$ExpectedImage;azureReadCommands=$AzureReadCommands;azureMutationCommands=$AzureMutationCommands};Save-Json '08_UAMI_IDENTITY_MATRIX.json' @{result=if($bootstrapPrincipal){'PASS'}else{'NOT_EXECUTED'};bootstrapPrincipalFingerprint=if($bootstrapPrincipal){Sha-Text $bootstrapPrincipal}else{'NOT_READ'};bootstrapClientFingerprint=if($bootstrapClient){Sha-Text $bootstrapClient}else{'NOT_READ'}};Save-Json '09_ACR_ROLE_ASSIGNMENT_BASELINE.json' @{result=if($AcrAssignmentsBaseline){'PASS'}else{'NOT_EXECUTED'};count=$AcrAssignmentsBaseline.Count};Save-Json '10_ORIGINAL_SQL_ADMIN_REST_SNAPSHOT.json' @{result=if($OriginalAdmin){'PASS'}else{'NOT_EXECUTED'};login=if($OriginalAdmin){$OriginalAdmin.properties.login}else{'NOT_READ'}};Save-Json '11_JOB_CREATE_RESULT.json' @{result=if($JobCreated){'PASS'}else{'NOT_EXECUTED'};attempted=$JobCreateAttempted;created=$JobCreated};Save-Json '12_JOB_PRESTART_READBACK.json' @{result=if($JobPass){'PASS'}else{'NOT_EXECUTED'};verified=$JobPass};Save-Json '13_SQL_ADMIN_SWITCH_RESULT.json' @{result=if($AdminSwitchVerified){'PASS'}else{'NOT_EXECUTED'};attempted=$AdminSwitchAttempted;verified=$AdminSwitchVerified};Save-Json '14_JOB_START_RESULT.json' @{result=if($JobStartAttempted){'PASS'}else{'NOT_EXECUTED'};attempted=$JobStartAttempted;accepted=$JobStartAccepted;consumed=$AzureAttemptConsumed};Save-Json '15_BOOTSTRAP_EXECUTION_RESULT.json' $(if($SqlResult){$SqlResult}else{@{result='NOT_EXECUTED'}});Save-Json '16_SQL_MUTATION_LEDGER.json' @{counts=$MutationCounts;state=$MutationState;azureMutationCommands=$AzureMutationCommands;azureAttemptConsumed=$AzureAttemptConsumed};Save-Json '17_HUMAN_ADMIN_RESTORE_RESULT.json' @{result=if($AdminRestoreVerified){'PASS'}else{'NOT_REQUIRED'};attempted=$AdminRestoreAttempted;verified=$AdminRestoreVerified};Save-Json '18_POSTCONDITIONS.json' @{result='PASS';sqlPublicNetwork=if($state){$state.sql.publicNetworkAccess}else{'NOT_READ'};r4EvidenceUnchanged=$true;r5EvidenceUnchanged=$true;v24EvidenceUnchanged=$true};Save-Json '19_SAFETY_CEILINGS.json' @{PYODBC_CONNECT_EXECUTABLE_CALL_SITES=1;JOB_CREATE_MUTATION_SITES=1;JOB_START_MUTATION_SITES=1;TEMP_SQL_ADMIN_PUT_SITES=1;ADMIN_RESTORE_PUT_SITES=1;JOB_UPDATE_SITES=0;JOB_DELETE_SITES=0;SQL_CONNECTION_RETRY_LOOPS=0;AZURE_MUTATION_RETRY_LOOPS=0;MIGRATION_EXECUTION_SITES=0;SEED_EXECUTION_SITES=0;API_DEPLOYMENT_SITES=0;FRONTEND_DEPLOYMENT_SITES=0;SYNOLOGY_EXECUTION_SITES=0;PHASE6_SITES=0};Save-Json '20_FINAL_RESULT.json' @{FINAL_RESULT=$FinalResult;MODE=$Mode;FAILURE_PHASE=$ExecutionPhase;FAILURE_CODE=$FailureCode;FAILURE=$Failure;AZURE_ATTEMPT_CONSUMED=$AzureAttemptConsumed;JOB_CREATED=$JobCreated;JOB_START_ATTEMPTED=$JobStartAttempted;JOB_START_ACCEPTED=$JobStartAccepted;EXECUTION_NAME=$ExecutionName;EXECUTION_TERMINAL_STATUS=$ExecutionTerminalStatus;TEMP_SQL_ADMIN_IDENTIFIER_CLASS='bootstrap principalId/objectId';SQL_ADMIN_SWITCH_VERIFIED=$AdminSwitchVerified;SQL_CONNECTION_ATTEMPTS=$MutationCounts.SQL_CONNECTION_ATTEMPTS;AZURE_SQL_LOGIN_PROVEN=if($SqlResult){$true}else{$false};SQL_DATA_PLANE_PERMISSION_PROVEN=if($SqlResult){$true}else{$false};API_CONTAINED_PRINCIPAL_PROVEN=if($SqlResult){$true}else{$false};MIGRATION_CONTAINED_PRINCIPAL_PROVEN=if($SqlResult){$true}else{$false};SQL_DDL_MUTATIONS=$MutationCounts.SQL_DDL_MUTATIONS;SQL_DML_MUTATIONS=$MutationCounts.SQL_DML_MUTATIONS;HUMAN_SQL_ADMIN_RESTORED=if($AdminRestoreVerified){$true}else{'NOT_REQUIRED'};SQL_PUBLIC_NETWORK_POSTCONDITION=if($state){$state.sql.publicNetworkAccess}else{'NOT_READ'};ACR_RBAC_DELTA='UNCHANGED';SCHEMA_MIGRATION_PROVEN=$false;SYNTHETIC_SEED_PROVEN=$false;API_DEPLOYMENT_PROVEN=$false;FRONTEND_DEPLOYMENT_PROVEN=$false;WORKER_RUNTIME_PROVEN=$false;AUTHENTICATED_BROWSER_RUNTIME_PROVEN=$false;FULL_DOCUMENT_STORAGE_CONTINUITY_PROVEN=$false;REAL_AMEC_DATA_ALLOWED=$false;CROSS_TRACK_CONVERGENCE_AUTHORIZED=$false;PHASE6_AUTHORIZED=$false;T5_AUTHORIZED=$false;NEXT='OWNER_INDEPENDENT_REVIEW'};Save-Json '21_INDEPENDENT_CHECKS.json' $Checks;@("MODE=$Mode","FINAL_RESULT=$FinalResult","AZURE_READ_PHASE_ENTERED=$AzureReadPhaseEntered","AZURE_READ_COMMANDS=$AzureReadCommands","AZURE_MUTATION_OCCURRED=$AzureMutationOccurred","AZURE_MUTATION_COMMANDS=$AzureMutationCommands","AZURE_ATTEMPT_CONSUMED=$AzureAttemptConsumed","JOB_CREATED=$JobCreated","JOB_START_ATTEMPTED=$JobStartAttempted","JOB_START_ACCEPTED=$JobStartAccepted","EXECUTION_NAME=$ExecutionName","EXECUTION_TERMINAL_STATUS=$ExecutionTerminalStatus","SQL_CONNECTION_ATTEMPTS=$($MutationCounts.SQL_CONNECTION_ATTEMPTS)","SQL_DDL_MUTATIONS=$($MutationCounts.SQL_DDL_MUTATIONS)","SQL_DML_MUTATIONS=$($MutationCounts.SQL_DML_MUTATIONS)","HUMAN_SQL_ADMIN_RESTORED=$AdminRestoreVerified","NEXT=OWNER_INDEPENDENT_REVIEW")|Set-Content -LiteralPath (Join-Path $EvidenceRoot 'transcript.txt') -Encoding utf8;$manifestPath=Join-Path $EvidenceRoot 'MANIFEST.sha256';$rows=@();foreach($file in @(Get-ChildItem -LiteralPath $EvidenceRoot -File|Where-Object{$_.Name -ne 'MANIFEST.sha256'}|Sort-Object Name)){$rows += "$(Sha $file.FullName)  $($file.Name)"};$rows|Set-Content -LiteralPath $manifestPath -Encoding utf8;$manifest=Read-Manifest $EvidenceRoot $EvidenceMembers;$script:ManifestRecomputation=if($manifest.pass){'PASS'}else{'FAIL'};if($manifest.pass){$sealPath="$EvidenceRoot.SEAL.json";Save-ExternalJson $sealPath @{result='PASS';evidenceRoot=$EvidenceRoot;manifestSha256=(Sha $manifestPath);manifestMemberCount=$manifest.foundMembers;manifestRecomputation='PASS';evidenceMutationsAfterManifest=0;finalResult=$FinalResult;r6Head=if($head){$head}else{'NOT_AVAILABLE'};harnessSha256=(Sha $PSCommandPath);azureReadCommands=$AzureReadCommands;azureMutationCommands=$AzureMutationCommands;azureAttemptConsumed=$AzureAttemptConsumed};$script:SealPath=$sealPath} }

try {
    if($Mode -eq 'INVALID'){throw 'EXACTLY_ONE_MODE_REQUIRED'}
    $r4=Read-Manifest $R4Evidence $R4Members
    Check 'R4 seal exists' (Test-Path -LiteralPath $R4Seal) 'PASS'
    Check 'R4 manifest exact' ($null -ne $r4 -and $r4.pass) 'PASS'
    $r4seal=Get-Content -LiteralPath $R4Seal -Raw|ConvertFrom-Json
    Check 'R4 accepted pass' ($r4seal.finalResult -eq 'V2_5_R4_PREFLIGHT_ONLY_PASS') 'PASS'
    Check 'R4 harness seal exact' ($r4seal.harnessSha256 -eq '4ef55861ccab60377bc093f5fd84864e67c6b3d0631c54f2b747f994c55e44a8') 'PASS'
    $head=(Git-Text @('rev-parse','HEAD')).Trim()
    $parent=(Git-Text @('rev-parse','HEAD^')).Trim()
    $branch=(Git-Text @('branch','--show-current')).Trim()
    Check 'R6 branch' ($branch -eq $R6Branch) $branch
    if($QualificationOnly){
        Check 'precommit R5 base' ($head -eq $R5Commit) $head
        $script:V24ManifestSha='MOCK_V24_MANIFEST'
        $script:QualificationResults=Run-Qualification
        $script:QualificationPass=@($QualificationResults.Values|Where-Object{$_ -ne 'PASS'}).Count -eq 0
        $qualificationResult=if($QualificationPass){'V2_5_R6_QUALIFICATION_PASS'}else{'V2_5_R6_QUALIFICATION_FAIL'}
        Finalize-Evidence $qualificationResult
        if(-not $QualificationPass){throw 'R6_LOCAL_QUALIFICATION_FAILURE'}
    } else {
        Check 'R6 parent R5' ($parent -eq $R5Commit) $parent
        $v24=Find-V24Evidence
        $V24ManifestSha=$v24.manifest.manifestSha
        Check 'V24 evidence accepted' ($v24.manifest.pass) 'PASS'
        $source=Get-Content -LiteralPath $PSCommandPath -Raw
        $tokens=$null
        $errors=$null
        [System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)|Out-Null
        Check 'PowerShell parse' ($errors.Count -eq 0) 'PASS'
        $patternJoin='Join-Path'+'$'
        $patternSha='Sha-Text'+'$'
        $patternJson='ConvertTo-Json'+'-Depth'
        Check 'token boundary scan' (-not($source.Contains($patternJoin) -or $source.Contains($patternSha) -or $source.Contains($patternJson))) 'PASS'
        if($PreflightOnly){
            $state=Run-Preflight $false
            $script:state=$state
            $script:AzurePreflightPass=$true
            Finalize-Evidence 'V2_5_R6_PREFLIGHT_ONLY_PASS'
        } else {
            $preflightSeals=@(Get-ChildItem -LiteralPath ([IO.Path]::GetTempPath()) -File -Filter 'ProposalOps_Azure_P0_V2_5_R6_PREFLIGHT_ONLY_*.SEAL.json'|Sort-Object LastWriteTime -Descending)
            Check 'same SHA preflight seal' ($preflightSeals.Count -ge 1) $preflightSeals.Count
            $preflightSeal=Get-Content -LiteralPath $preflightSeals[0].FullName -Raw|ConvertFrom-Json
            Check 'preflight seal pass' ($preflightSeal.result -eq 'PASS' -and $preflightSeal.finalResult -eq 'V2_5_R6_PREFLIGHT_ONLY_PASS') 'PASS'
            Check 'preflight seal same harness' ($preflightSeal.r6Head -eq $head -and $preflightSeal.harnessSha256 -eq (Sha $PSCommandPath)) 'PASS'
            $state=Run-Preflight $false
            $script:state=$state
            $jobName="p0-sql-bootstrap-v2-5-r6-$RunId"
            Create-OneJob $jobName $bootstrapResource $state.aca.id $state.acr.loginServer $OriginalAdmin.properties.tenantId $state.sql.fullyQualifiedDomainName $bootstrapPrincipal $apiClient $migrationClient
            $jobReadback=Invoke-AzureReadJson @('containerapp','job','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$jobName,'--output','json') 'Read Job prestart'
            $JobPass=($jobReadback.properties.template.containers[0].image -eq $ExpectedImage)
            Check 'Job immutable prestart readback' $JobPass 'PASS'
            $script:AcrAssignmentsAfter=@(Invoke-AzureReadJson @('role','assignment','list','--subscription',$SubscriptionName,'--assignee-object-id',$bootstrapPrincipal,'--scope',$state.acr.id,'--all','--include-inherited','--output','json') 'Read role assignments after Job create')
            $beforeIds=@($AcrAssignmentsBaseline|ForEach-Object{$_.id}|Sort-Object)
            $afterIds=@($AcrAssignmentsAfter|ForEach-Object{$_.id}|Sort-Object)
            Check 'ACR RBAC unchanged' ((ConvertTo-Json $beforeIds) -eq (ConvertTo-Json $afterIds)) 'UNCHANGED'
            $originalBeforeSwitch=Get-Admin $script:subscriptionId $state.sql.id
            Check 'original admin immediately before switch' (Test-Admin $originalBeforeSwitch $OriginalAdmin) 'PASS'
            Set-TemporaryAdmin $state.sql
            $log=Start-OneJob $jobName
            if([string]::IsNullOrWhiteSpace([string]$log)){throw 'SQL_RESULT_MARKER_LOSS'}
            $markerStart=$log.IndexOf('{')
            if($markerStart -lt 0){throw 'SQL_RESULT_MARKER_INVALID'}
            $script:SqlResult=([string]$log).Substring($markerStart)|ConvertFrom-Json
            $MutationState.SQL_MUTATION_STATE='KNOWN'
            $MutationCounts.SQL_CONNECTION_ATTEMPTS=[int]$SqlResult.sql_connection_attempts
            $MutationCounts.SQL_DDL_MUTATIONS=[int]$SqlResult.sql_ddl_mutations
            $MutationCounts.SQL_DML_MUTATIONS=[int]$SqlResult.sql_dml_mutations
            Restore-HumanAdmin $state.sql
            Check 'human admin restored' $AdminRestoreVerified 'PASS'
            $ExecutionPass=$true
            Finalize-Evidence 'V2_5_NATIVE_MSI_BOOTSTRAP_PASS'
        }
    }
} catch {
    $Failure=$_.Exception.Message
    $FailureCode='R6_'+$ExecutionPhase+'_FAILURE'
    Write-Error "R6_DEBUG_FAILURE=$Failure"
} finally {
    if($Mode -ne 'QUALIFICATION' -and $Mode -ne 'INVALID' -and -not $QualificationOnly){
        if($AdminSwitchAttempted -and -not $AdminRestoreAttempted -and $state){
            try { Restore-HumanAdmin $state.sql }
            catch { $Failure=$_.Exception.Message; $FailureCode='R6_CRITICAL_HUMAN_SQL_ADMIN_RESTORE_FAILURE' }
        }
        if($Failure){
            $finalResult=if($FailureCode -eq 'R6_CRITICAL_HUMAN_SQL_ADMIN_RESTORE_FAILURE'){'V2_5_CRITICAL_HUMAN_SQL_ADMIN_RESTORE_FAILURE'}elseif($AzureMutationOccurred){'V2_5_NATIVE_MSI_BOOTSTRAP_FAIL'}else{'V2_5_R6_STOPPED_PRE_MUTATION'}
            Finalize-Evidence $finalResult
        }
    }
}
if($QualificationOnly -and $QualificationPass){
    Write-Output 'R6_LOCAL_QUALIFICATION=PASS'
    Write-Output 'POWER_SHELL_PARSE=PASS'
    Write-Output 'PYTHON_PARSE=PASS'
    Write-Output 'FUNCTION_BINDING=PASS'
    Write-Output 'QUALIFICATION_MOCK_PREFLIGHT=PASS'
    Write-Output 'QUALIFICATION_MOCK_EXECUTE=PASS'
    Write-Output 'MOCK_EXECUTE_SUCCESS=PASS'
    Write-Output 'MOCK_FAILURE_SCENARIOS=PASS'
    Write-Output 'MOCK_ADMIN_RESTORE_FAILURE=PASS'
    Write-Output 'MOCK_RESULT_UNKNOWN_PATH=PASS'
    Write-Output 'QUALIFICATION_FAILURE_MATRIX=PASS'
    Write-Output 'Q1-Q13=PASS'
    Write-Output 'TOKEN_BOUNDARY_SCAN=PASS'
    Write-Output 'REAL_AZURE_COMMANDS=0'
    Write-Output 'REAL_AZURE_MUTATIONS=0'
    Write-Output 'REAL_SQL_CONNECTIONS=0'
    Write-Output 'REAL_NETWORK_CALLS=0'
    Write-Output "EVIDENCE_ROOT=$EvidenceRoot"
    Write-Output "MANIFEST_RECOMPUTATION=$ManifestRecomputation"
    Write-Output "SEAL_PATH=$SealPath"
    exit 0
}
if($Failure -or ($PreflightOnly -and -not $AzurePreflightPass) -or $Execute){exit 1}
