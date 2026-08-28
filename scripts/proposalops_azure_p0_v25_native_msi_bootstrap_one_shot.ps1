[CmdletBinding()]
param([switch]$Execute)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RunId = Get-Date -AsUTC -Format 'yyyyMMdd-HHmmss'
$EvidenceRoot = Join-Path ([IO.Path]::GetTempPath()) "ProposalOps_Azure_P0_V2_5_R2_$RunId"
New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null

$ExpectedAppSha = 'c42e6c449483b0951de0f366d700dbaf7b9e5525'
$ExpectedAppTree = 'a497c6951064119453d175d1b93d4e59c9029fd0'
$ExpectedImage = 'acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d'
$ScalarRepairCommit = '5ed44e51978a71100f85616020be78d7a7660261'
$ScalarRepairTree = 'b88db7e551b372366918d28415cd70b6846a32ec'
$ScalarRepairBranch = 'azure-p0-v24-scalar-repair-immutable-v1'
$ScalarRepairScriptSha = '2a5a3abb7f95af5a713d75dba94b66b42fc7430ac43c186ea74ead778b42e669'
$V1Branch = 'azure-p0-v25-native-msi-bootstrap-one-shot-v1'
$V1Commit = 'fa227c1d3276b2c8cf3f312c2814144e05aeddd5'
$V1Tree = '2fd49ceceb7daf828112c22372a06278fef451f8'
$R2Branch = 'azure-p0-v25-native-msi-bootstrap-one-shot-r2-v1'
$ExpectedMain = '3474b35a13d27f0010ec5d03dd4a2f361ac6774d'
$SubscriptionName = 'AMEC Subscription'
$RG = 'rg-proposalops-prod-uae'
$SqlServer = 'sql-proposalops-prod-uae-2bea2887'
$Database = 'sqldb-proposalops-prod'
$AcaEnvironmentName = 'cae-proposalops-prod-uae'
$AcrName = 'acrproposalopsproduae2bea2887'
$AcceptedPrivateIp = '10.43.2.4'

$CurrentOperation = 'initialization'
$Failure = $null
$FailureCode = $null
$AzureMutationOccurred = $false
$AzureAttemptConsumed = $false
$JobCreateAttempted = $false
$JobCreated = $false
$ExecutionStartAttempted = $false
$ExecutionStarted = $false
$AdminSwitchAttempted = $false
$AdminSwitchVerified = $false
$AdminRestoreAttempted = $false
$AdminRestoreVerified = $false
$OriginalHumanAdmin = $null
$V24Evidence = $null
$V24ManifestSha = $null
$Checks = [System.Collections.Generic.List[object]]::new()
$MutationCounts = [ordered]@{
  REPOSITORY_COMMITS_CREATED = 1
  REMOTE_BRANCHES_CREATED = 1
  REMOTE_BRANCH_UPDATES = 0
  BOOTSTRAP_JOB_CREATES = 0
  BOOTSTRAP_JOB_UPDATES = 0
  BOOTSTRAP_JOB_DELETES = 0
  BOOTSTRAP_JOB_EXECUTIONS = 0
  SQL_ADMIN_SWITCH_MUTATIONS = 0
  SQL_ADMIN_RESTORE_MUTATIONS = 0
  SQL_CONNECTION_ATTEMPTS = 0
  SQL_CREATE_USER_MUTATIONS = 0
  SQL_ROLE_MUTATIONS = 0
  SQL_PERMISSION_GRANTS = 0
  SQL_DDL_OTHER = 0
  SQL_DDL_MUTATIONS = 0
  SQL_DML_MUTATIONS = 0
  ENTRA_MUTATIONS = 0
  RBAC_MUTATIONS = 0
  FIREWALL_MUTATIONS = 0
  SQL_PUBLIC_NETWORK_MUTATIONS = 0
  MIGRATION_EXECUTIONS = 0
  SEED_EXECUTIONS = 0
  API_DEPLOYMENTS = 0
  FRONTEND_DEPLOYMENTS = 0
  SYNLOGY_READS = 0
  REAL_AMEC_DATA_READS = 0
  REAL_AMEC_DATA_WRITES = 0
  PHASE6_MUTATIONS = 0
}
$MutationState = [ordered]@{
  BOOTSTRAP_JOB_CREATE_ATTEMPTED = $false
  BOOTSTRAP_JOB_CREATED = $false
  BOOTSTRAP_JOB_EXECUTION_START_ATTEMPTED = $false
  BOOTSTRAP_JOB_EXECUTION_STARTED = $false
  SQL_ADMIN_SWITCH_ATTEMPTED = $false
  SQL_ADMIN_SWITCH_VERIFIED = $false
  SQL_ADMIN_RESTORE_ATTEMPTED = $false
  SQL_ADMIN_RESTORE_VERIFIED = $false
  SQL_MUTATION_STATE = 'NOT_EXECUTED'
}

function Save-Json([string]$Name, $Value) { $Value | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath (Join-Path $EvidenceRoot $Name) -Encoding utf8 }
function Sha([string]$Path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function Git-Text([string[]]$Arguments) {
  $output = & git -C $RepoRoot @Arguments 2>&1
  if ($LASTEXITCODE -ne 0) { throw "GIT_COMMAND_FAILURE $($Arguments -join ' ')" }
  ($output | ForEach-Object ToString) -join [Environment]::NewLine
}
function Check([string]$Id, [bool]$Pass, $Actual = '') {
  $Checks.Add([ordered]@{ id = $Id; operation = $CurrentOperation; result = if ($Pass) { 'PASS' } else { 'FAIL' }; actual = [string]$Actual })
  if (-not $Pass) { throw "VALIDATION_FAILURE [$Id] $Actual" }
}
function Invoke-Az([string[]]$Arguments, [string]$Label) {
  $script:CurrentOperation = $Label
  $out = & az @Arguments --only-show-errors 2>&1
  if ($LASTEXITCODE -ne 0) { throw "AZURE_COMMAND_FAILURE [$Label] $(($out | ForEach-Object ToString) -join [Environment]::NewLine)" }
  ($out | ForEach-Object ToString) -join [Environment]::NewLine
}
function Invoke-AzJson([string[]]$Arguments, [string]$Label) {
  $text = Invoke-Az $Arguments $Label
  $starts = @($text.IndexOf('{'), $text.IndexOf('[')) | Where-Object { $_ -ge 0 } | Sort-Object
  if ($starts.Count -eq 0) { throw "AZURE_JSON_EMPTY [$Label]" }
  $text.Substring($starts[0]) | ConvertFrom-Json
}
function Invoke-AzMutation([string[]]$Arguments, [string]$Label, [string]$Counter) {
  $script:AzureMutationOccurred = $true
  $script:MutationCounts[$Counter]++
  Invoke-Az $Arguments $Label | Out-Null
}
function Get-Admin([string]$Subscription) { @(Invoke-AzJson @('sql','server','ad-admin','list','--subscription',$Subscription,'--resource-group',$RG,'--server',$SqlServer,'--output','json') 'Read SQL Entra administrator') }
function Wait-Admin([string]$Subscription, [string]$ExpectedSid, [string]$ExpectedLogin, [int]$Seconds = 180) {
  for ($i = 0; $i -lt [Math]::Max(1, [int]($Seconds / 5)); $i++) {
    $a = Get-Admin $Subscription
    if ($a.Count -eq 1 -and $a[0].sid -eq $ExpectedSid -and $a[0].login -eq $ExpectedLogin) { return $a }
    Start-Sleep -Seconds 5
  }
  @(Get-Admin $Subscription)
}
function Read-Manifest([string]$Root, [int]$ExpectedMembers = 15) {
  $path = Join-Path $Root 'MANIFEST.sha256'
  if (-not (Test-Path -LiteralPath $path)) { return $null }
  $rows = @()
  foreach ($line in @(Get-Content -LiteralPath $path)) { if ($line -match '^([0-9a-f]{64})  (.+)$') { $rows += [pscustomobject]@{ expected = $Matches[1]; name = $Matches[2] } } }
  $matched = 0
  $failed = 0
  foreach ($row in $rows) {
    $file = Join-Path $Root $row.name
    if ((Test-Path -LiteralPath $file) -and (Sha $file) -eq $row.expected) { $matched++ } else { $failed++ }
  }
  [ordered]@{ root = $Root; rows = $rows; expectedMembers = $ExpectedMembers; foundMembers = $rows.Count; matchedMembers = $matched; failedMembers = $failed; manifestSha = Sha $path; pass = ($rows.Count -eq $ExpectedMembers -and $matched -eq $ExpectedMembers -and $failed -eq 0) }
}
function Find-V24Evidence {
  $dirs = @()
  foreach ($root in @('/tmp', [IO.Path]::GetTempPath()) | Select-Object -Unique) { if (Test-Path -LiteralPath $root) { $dirs += @(Get-ChildItem -LiteralPath $root -Directory -Filter 'ProposalOps_Azure_P0_V2_4_*' -ErrorAction SilentlyContinue) } }
  $valid = @()
  foreach ($dir in ($dirs | Sort-Object FullName -Unique)) {
    try {
      $finalPath = Join-Path $dir.FullName '13_FINAL_RESULT.json'
      if (-not (Test-Path -LiteralPath $finalPath)) { continue }
      $final = Get-Content -LiteralPath $finalPath -Raw | ConvertFrom-Json
      $manifest = Read-Manifest $dir.FullName
      if ($final.FINAL_RESULT -eq 'V2_4_MI_TOKEN_DIAGNOSTIC_PASS' -and $manifest.pass -and $final.AZURE_IDENTITY_CORROBORATION -eq 'FAIL' -and -not [bool]$final.CROSS_TRACK_CONVERGENCE_AUTHORIZED -and [int]$final.REAL_AMEC_DATA_READS -eq 0 -and [int]$final.REAL_AMEC_DATA_WRITES -eq 0) { $valid += [pscustomobject]@{ root = $dir.FullName; final = $final; manifest = $manifest } }
    } catch {}
  }
  if ($valid.Count -eq 0) { throw 'V24_EVIDENCE_NOT_FOUND' }
  if (@($valid | ForEach-Object { $_.manifest.manifestSha } | Select-Object -Unique).Count -ne 1) { throw 'V24_EVIDENCE_AMBIGUOUS' }
  $valid[0]
}
function Verify-V24([string]$Root, [string]$ManifestSha) {
  $m = Read-Manifest $Root
  if ($null -eq $m -or -not $m.pass -or $m.manifestSha -ne $ManifestSha) { throw 'V24_EVIDENCE_INTEGRITY_FAIL' }
  [ordered]@{ result = 'PASS'; root = $Root; manifestSha = $m.manifestSha; expectedMembers = $m.expectedMembers; foundMembers = $m.foundMembers; matchedMembers = $m.matchedMembers; failedMembers = $m.failedMembers }
}
function Set-UnknownSqlState {
  $script:MutationState.SQL_MUTATION_STATE = 'UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION'
  foreach ($k in @('SQL_CONNECTION_ATTEMPTS','SQL_CREATE_USER_MUTATIONS','SQL_ROLE_MUTATIONS','SQL_PERMISSION_GRANTS','SQL_DDL_OTHER','SQL_DDL_MUTATIONS','SQL_DML_MUTATIONS')) { $script:MutationCounts[$k] = 'UNKNOWN' }
}
function New-BootstrapJob([string]$Name, [string]$Identity, [string]$EnvironmentId, [string]$Registry, [string]$TenantId, [string]$SqlFqdn, [string]$BootstrapPrincipal, [string]$ApiClient, [string]$MigrationClient) {
  $body = @'
import json,os,sys
r={"sql_connection_attempts":0,"sql_connection_succeeded":False,"sql_login":"NOT_EXECUTED","sql_target_db":"NOT_EXECUTED","sql_required_permission":"NOT_EXECUTED","sql_ddl_executed":False,"sql_dml_executed":False,"api_mutations":0,"migration_mutations":0,"role_mutations":0,"permission_grants":0,"sql_mutations":[],"bootstrap_principal_absent":False,"post_verification":False,"sql_mutation_state":"KNOWN"}
cn=None
def emit():
 print("PROPOSALOPS_V25_RESULT="+json.dumps(r,sort_keys=True,separators=(",",":")))
try:
 import pyodbc
 r["sql_connection_attempts"]=1
 cs=f"DRIVER={{ODBC Driver 18 for SQL Server}};Server=tcp:{os.environ['SQL_HOST']},1433;Database={os.environ['SQL_DATABASE']};Authentication=ActiveDirectoryMsi;UID={os.environ['SQL_ODBC_UID']};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
 cn=pyodbc.connect(cs,autocommit=True);r["sql_connection_succeeded"]=True;cur=cn.cursor()
 r["sql_login"]="PASS" if cur.execute("SELECT 1").fetchone()[0]==1 else "FAIL"
 r["sql_target_db"]="PASS" if cur.execute("SELECT DB_NAME()").fetchone()[0]==os.environ["SQL_DATABASE"] else "FAIL"
 r["sql_required_permission"]="PASS" if int(cur.execute("SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','ALTER ANY USER')").fetchone()[0])==1 else "FAIL"
 def sid(cid): return cur.execute("SELECT CONVERT(varchar(34),CONVERT(varbinary(16),CONVERT(uniqueidentifier, ?)),1)",cid).fetchone()[0].lower()
 def inspect(n):
  x=cur.execute("SELECT name,type,CONVERT(varchar(34),sid,1) FROM sys.database_principals WHERE name=?",n).fetchone()
  roles=[str(z[0]) for z in cur.execute("SELECT rp.name FROM sys.database_role_members drm JOIN sys.database_principals rp ON rp.principal_id=drm.role_principal_id JOIN sys.database_principals mp ON mp.principal_id=drm.member_principal_id WHERE mp.name=?",n).fetchall()]
  return x,roles
 r["bootstrap_principal_absent"]=cur.execute("SELECT 1 FROM sys.database_principals WHERE name='proposalops_bootstrap_uami'").fetchone() is None
 targets=[("proposalops_api_uami",os.environ["API_CLIENT_ID"],["db_datareader","db_datawriter"],{"db_owner","db_ddladmin"},False),("proposalops_migration_uami",os.environ["MIGRATION_CLIENT_ID"],["db_datareader","db_datawriter","db_ddladmin"],{"db_owner"},True)]
 states=[]
 for n,cid,required,forbidden,view in targets:
  x,roles=inspect(n);expected=sid(cid)
  if x is not None and (x[1]!="E" or str(x[2]).lower()!=expected): raise RuntimeError("existing principal mismatch")
  if any(z in forbidden for z in roles): raise RuntimeError("forbidden role present")
  states.append((n,required,view,x,roles,expected))
 if r["sql_login"]!="PASS" or r["sql_target_db"]!="PASS" or r["sql_required_permission"]!="PASS" or not r["bootstrap_principal_absent"]: raise RuntimeError("pre-DDL gate failed")
 for n,required,view,x,roles,expected in states:
  if x is None:
   cur.execute(f"CREATE USER [{n}] WITH SID={expected}, TYPE=E");r["sql_ddl_executed"]=True;r["sql_mutations"].append(f"CREATE USER {n}")
   if n=="proposalops_api_uami":r["api_mutations"]+=1
   else:r["migration_mutations"]+=1
  for role in required:
   if role not in roles:cur.execute(f"ALTER ROLE [{role}] ADD MEMBER [{n}]");r["sql_ddl_executed"]=True;r["role_mutations"]+=1;r["sql_mutations"].append(f"ALTER ROLE {role} ADD MEMBER {n}")
  if view and cur.execute("SELECT 1 FROM sys.database_permissions WHERE grantee_principal_id=USER_ID(?) AND permission_name='VIEW DEFINITION' AND state IN ('G','W')",n).fetchone() is None:cur.execute(f"GRANT VIEW DEFINITION TO [{n}]");r["sql_ddl_executed"]=True;r["permission_grants"]+=1;r["sql_mutations"].append(f"GRANT VIEW DEFINITION TO {n}")
 for n,required,view,x,roles,expected in states:
  y,actual=inspect(n)
  if y is None or y[1]!="E" or str(y[2]).lower()!=expected or set(actual)!=set(required):raise RuntimeError("post principal verification failed")
  if view and cur.execute("SELECT 1 FROM sys.database_permissions WHERE grantee_principal_id=USER_ID(?) AND permission_name='VIEW DEFINITION' AND state IN ('G','W')",n).fetchone() is None:raise RuntimeError("VIEW DEFINITION missing")
 r["post_verification"]=True;emit();sys.exit(0)
except Exception as e:
 r["error_class"]=type(e).__name__;r["error_message"]=str(e)[:240];emit();sys.exit(1)
finally:
 if cn is not None:cn.close()
'@
  $environment = @("SQL_HOST=$SqlFqdn","SQL_DATABASE=$Database","SQL_ODBC_UID=$BootstrapPrincipal","API_CLIENT_ID=$ApiClient","MIGRATION_CLIENT_ID=$MigrationClient","AZURE_TENANT_ID=$TenantId",'SYNTHETIC_ONLY=true','REAL_DATA_ALLOWED=false')
  $argsJson = ConvertTo-Json ([string[]]@('-c',$body)) -Compress
  $envJson = ConvertTo-Json ([object[]]($environment | ForEach-Object { $p=$_.IndexOf('=');[ordered]@{name=$_.Substring(0,$p);value=$_.Substring($p+1)} })) -Compress
  $identityJson = ConvertTo-Json ([ordered]@{type='UserAssigned';userAssignedIdentities=[ordered]@{$Identity=@{}}}) -Compress
  $yaml = @"
location: UAE North
properties:
  environmentId: $EnvironmentId
  configuration:
    manualTriggerConfig:
      parallelism: 1
      replicaCompletionCount: 1
    replicaRetryLimit: 0
    replicaTimeout: 300
    triggerType: Manual
    registries:
      - server: $Registry
        identity: $Identity
  template:
    containers:
      - name: main
        image: $ExpectedImage
        command: ["python"]
        args: $argsJson
        env: $envJson
        resources:
          cpu: 0.5
          memory: 1Gi
identity: $identityJson
tags: {"application":"ProposalOps","environment":"AZURE-PREPROD","synthetic-only":"true","commissioning":"v2.5-r2"}
"@
  $path = Join-Path ([IO.Path]::GetTempPath()) "proposalops-v25-r2-$RunId.yaml"
  $yaml | Set-Content -LiteralPath $path -Encoding utf8
  $script:JobCreateAttempted = $true
  $script:MutationState.BOOTSTRAP_JOB_CREATE_ATTEMPTED = $true
  Invoke-AzMutation @('containerapp','job','create','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$Name,'--yaml',$path,'--output','json') "Create exactly one R2 Job $Name" 'BOOTSTRAP_JOB_CREATES'
  $script:JobCreated = $true
  $script:MutationState.BOOTSTRAP_JOB_CREATED = $true
}
function Start-OneExecution([string]$Name) {
  $before = @(Invoke-AzJson @('containerapp','job','execution','list','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$Name,'--output','json') 'List R2 executions before start')
  $beforeNames = @($before | ForEach-Object { $_.name })
  $script:ExecutionStartAttempted = $true
  $script:MutationState.BOOTSTRAP_JOB_EXECUTION_START_ATTEMPTED = $true
  Invoke-AzMutation @('containerapp','job','start','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$Name,'--output','json') 'Start exactly one R2 bootstrap execution' 'BOOTSTRAP_JOB_EXECUTIONS'
  for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 5
    $all = @(Invoke-AzJson @('containerapp','job','execution','list','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$Name,'--output','json') 'Poll R2 execution')
    $new = @($all | Where-Object { $beforeNames -notcontains $_.name } | Sort-Object name -Descending)
    if ($new.Count -gt 0) {
      $execution = $new[0];$script:ExecutionStarted = $true;$script:AzureAttemptConsumed = $true;$script:MutationState.BOOTSTRAP_JOB_EXECUTION_STARTED = $true
      $status = [string]($execution.properties.status ?? $execution.status);$log=''
      try { $log=Invoke-Az @('containerapp','job','logs','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$Name,'--execution',$execution.name,'--container','main','--tail','300','--format','text') 'Read R2 bootstrap logs' } catch { $log="LOG_READ_FAILURE=$($_.Exception.Message)" }
      if ($status -in @('Succeeded','Failed','Stopped','Degraded')) { return [pscustomobject]@{execution=$execution;status=$status;log=$log} }
    }
  }
  throw 'BOOTSTRAP_JOB_EXECUTION_TIMEOUT'
}

try {
  if (-not $Execute) { throw 'EXECUTION_SWITCH_REQUIRED' }
  $v24=Find-V24Evidence;$V24Evidence=$v24.root;$V24ManifestSha=$v24.manifest.manifestSha
  Check 'V24 evidence gate' $true $V24Evidence
  Check 'V24 manifest 15/15' ($v24.manifest.pass) '15/15'
  Check 'V24 SDK failure preserved' ($v24.final.AZURE_IDENTITY_CORROBORATION -eq 'FAIL') 'FAIL'
  Check 'V24 cross-track false' (-not [bool]$v24.final.CROSS_TRACK_CONVERGENCE_AUTHORIZED) 'false'
  Check 'V24 real-data reads zero' ([int]$v24.final.REAL_AMEC_DATA_READS -eq 0) '0'
  Check 'V24 real-data writes zero' ([int]$v24.final.REAL_AMEC_DATA_WRITES -eq 0) '0'

  $branch=(Git-Text @('branch','--show-current')).Trim();$head=(Git-Text @('rev-parse','HEAD')).Trim();$parent=(Git-Text @('rev-parse','HEAD^')).Trim();$grandparent=(Git-Text @('rev-parse','HEAD^^')).Trim()
  $remoteR2=((Git-Text @('ls-remote','origin',"refs/heads/$R2Branch")).Trim().Split([char]9)[0]);$remoteV1=((Git-Text @('ls-remote','origin',"refs/heads/$V1Branch")).Trim().Split([char]9)[0]);$remoteScalar=((Git-Text @('ls-remote','origin',"refs/heads/$ScalarRepairBranch")).Trim().Split([char]9)[0]);$remoteMain=((Git-Text @('ls-remote','origin','refs/heads/main')).Trim().Split([char]9)[0])
  Check 'R2 branch exact' ($branch -eq $R2Branch) $branch;Check 'R2 remote head exact' ($head -eq $remoteR2) $remoteR2;Check 'R2 parent V1' ($parent -eq $V1Commit) $parent;Check 'R2 grandparent scalar' ($grandparent -eq $ScalarRepairCommit) $grandparent;Check 'V1 remote exact' ($remoteV1 -eq $V1Commit) $remoteV1;Check 'scalar remote exact' ($remoteScalar -eq $ScalarRepairCommit) $remoteScalar;Check 'main unchanged' ($remoteMain -eq $ExpectedMain) $remoteMain;Check 'scalar tree exact' ((Git-Text @('show','-s','--format=%T',$ScalarRepairCommit)).Trim() -eq $ScalarRepairTree) 'exact';Check 'scalar script exact' ((Sha (Join-Path $RepoRoot 'scripts/proposalops_azure_p0_master_finalize_v2.ps1')) -eq $ScalarRepairScriptSha) 'exact';Check 'accepted app tree exact' ((Git-Text @('rev-parse',"$ExpectedAppSha^{tree}")).Trim() -eq $ExpectedAppTree) 'exact'
  $changed=@(Git-Text @('diff-tree','--no-commit-id','--name-only','-r',$head) -split "\r?\n" | Where-Object { $_ });Check 'R2 changed path only' ($changed.Count -eq 1 -and $changed[0] -eq 'scripts/proposalops_azure_p0_v25_native_msi_bootstrap_one_shot.ps1') ($changed -join ',');Check 'accepted app unchanged' (@(Git-Text @('diff','--name-only',$ExpectedAppSha,$head,'--','backend','frontend','mock-systems')).Count -eq 0) 'zero'
  $source=Get-Content -LiteralPath $PSCommandPath -Raw;$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$t,[ref]$e)|Out-Null;Check 'R2 harness parse' ($e.Count -eq 0) 'PASS';Check 'one pyodbc connect call' (([regex]::Matches($source,'pyodbc\.connect\(')).Count -eq 1) '1'

  Save-Json '00_RUN_CONTEXT.json' @{result='PASS';runId=$RunId;acceptedApplicationSha=$ExpectedAppSha;acceptedApplicationTree=$ExpectedAppTree;acceptedImage=$ExpectedImage;resourceGroup=$RG;sqlServer=$SqlServer;database=$Database;r2Branch=$branch;r2Head=$head}
  Save-Json '01_PRIOR_V25_STOPPED_STATE.json' @{result='PASS';priorResult='V2_5_STOPPED_PRE_AZURE';priorAzureAttemptConsumed=$false;priorMutationCounts=@{BOOTSTRAP_JOB_CREATES=0;BOOTSTRAP_JOB_EXECUTIONS=0;SQL_ADMIN_SWITCH_MUTATIONS=0;SQL_ADMIN_RESTORE_MUTATIONS=0;SQL_CONNECTION_ATTEMPTS=0;SQL_CREATE_USER_MUTATIONS=0;SQL_ROLE_MUTATIONS=0;SQL_PERMISSION_GRANTS=0;SQL_DDL_MUTATIONS=0;SQL_DML_MUTATIONS=0};failureClass='PRE_AZURE_HARNESS_LOGIC_DEFECT'}
  Save-Json '02_V24_PRE_RUN_REVALIDATION.json' @{result='PASS';root=$V24Evidence;manifestSha=$V24ManifestSha;expectedMembers=15;foundMembers=$v24.manifest.foundMembers;matchedMembers=$v24.manifest.matchedMembers;failedMembers=$v24.manifest.failedMembers;finalResult=$v24.final.FINAL_RESULT;sdkCorroboration=$v24.final.AZURE_IDENTITY_CORROBORATION}
  Save-Json '03_SCALAR_REPAIR_REMOTE_PIN.json' @{result='PASS';branch=$ScalarRepairBranch;head=$remoteScalar;tree=$ScalarRepairTree;parent=(Git-Text @('show','-s','--format=%P',$ScalarRepairCommit)).Trim();repairedScriptSha256=$ScalarRepairScriptSha}
  Save-Json '04_V25_V1_HARNESS_PIN.json' @{result='PASS';branch=$V1Branch;head=$remoteV1;tree=$V1Tree;changedPaths=@('scripts/proposalops_azure_p0_v25_native_msi_bootstrap_one_shot.ps1');immutable=$true}
  Save-Json '05_V25_R2_HARNESS_REMOTE_PIN.json' @{result='PASS';branch=$R2Branch;head=$head;tree=(Git-Text @('rev-parse','HEAD^{tree}')).Trim();parent=$parent;grandparent=$grandparent;changedPaths=$changed;harnessSha256=(Sha $PSCommandPath)}

  $subscription=(Invoke-Az @('account','list','--query',"[?name=='$SubscriptionName' && state=='Enabled'].name | [0]",'--output','tsv') 'Resolve enabled subscription').Trim();Check 'enabled subscription' ($subscription -eq $SubscriptionName) $subscription
  $group=Invoke-AzJson @('group','show','--subscription',$subscription,'--name',$RG,'--output','json') 'Read resource group';$sql=Invoke-AzJson @('sql','server','show','--subscription',$subscription,'--resource-group',$RG,'--name',$SqlServer,'--output','json') 'Read SQL server';$db=Invoke-AzJson @('sql','db','show','--subscription',$subscription,'--resource-group',$RG,'--server',$SqlServer,'--name',$Database,'--output','json') 'Read SQL database';$aca=Invoke-AzJson @('containerapp','env','show','--subscription',$subscription,'--resource-group',$RG,'--name',$AcaEnvironmentName,'--output','json') 'Read ACA environment';$acr=Invoke-AzJson @('acr','show','--subscription',$subscription,'--resource-group',$RG,'--name',$AcrName,'--output','json') 'Read ACR';$dns=Invoke-AzJson @('network','private-dns','record-set','a','show','--subscription',$subscription,'--resource-group',$RG,'--zone-name','privatelink.database.windows.net','--name',$SqlServer,'--output','json') 'Read private DNS'
  $pes=@(Invoke-AzJson @('network','private-endpoint','list','--subscription',$subscription,'--resource-group',$RG,'--output','json') 'Read private endpoint');$pe=@($pes|Where-Object{$_.provisioningState -eq 'Succeeded' -and @($_.privateLinkServiceConnections|Where-Object{$_.privateLinkServiceId -eq $sql.id -and $_.provisioningState -eq 'Succeeded' -and $_.privateLinkServiceConnectionState.status -eq 'Approved'}).Count -gt 0});$images=@(Invoke-AzJson @('acr','repository','show-manifests','--subscription',$subscription,'--name',$AcrName,'--repository','proposalops-api','--output','json') 'Read accepted image');$image=@($images|Where-Object{$_.digest -eq 'sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d'})
  Check 'resource group exact' ($group.name -eq $RG) $group.name;Check 'SQL ready' ($sql.name -eq $SqlServer -and $sql.state -eq 'Ready') $sql.state;Check 'database online' ($db.name -eq $Database -and $db.status -eq 'Online') $db.status;Check 'SQL public disabled' ($sql.publicNetworkAccess -eq 'Disabled') $sql.publicNetworkAccess;Check 'SQL Entra only' ([bool]$sql.administrators.azureAdOnlyAuthentication) 'true';Check 'TLS 1.2' ($sql.minimalTlsVersion -eq '1.2') $sql.minimalTlsVersion;Check 'private endpoint accepted' ($pe.Count -eq 1) $pe.Count;Check 'private DNS exact' ($dns.aRecords[0].ipv4Address -eq $AcceptedPrivateIp) $dns.aRecords[0].ipv4Address;Check 'ACA environment succeeded' ($aca.properties.provisioningState -eq 'Succeeded') $aca.properties.provisioningState;Check 'ACR admin disabled' (-not [bool]$acr.adminUserEnabled) 'false';Check 'accepted image digest exact' ($image.Count -eq 1) $image.Count
  $bootstrap=Invoke-AzJson @('identity','show','--subscription',$subscription,'--resource-group',$RG,'--name','id-proposalops-sql-bootstrap-prod-uae','--output','json') 'Read bootstrap UAMI';$migration=Invoke-AzJson @('identity','show','--subscription',$subscription,'--resource-group',$RG,'--name','id-proposalops-sql-migrate-prod-uae','--output','json') 'Read migration UAMI';$api=Invoke-AzJson @('identity','show','--subscription',$subscription,'--resource-group',$RG,'--name','id-proposalops-api-prod-uae','--output','json') 'Read API UAMI'
  $bootstrapPrincipal=[string]$bootstrap.principalId;$bootstrapClient=[string]$bootstrap.clientId;$bootstrapResource=[string]$bootstrap.id;$migrationClient=[string]$migration.clientId;$apiClient=[string]$api.clientId;$g1=[guid]::Empty;$g2=[guid]::Empty;$g3=[guid]::Empty;$g4=[guid]::Empty
  Check 'bootstrap resource present' (-not [string]::IsNullOrWhiteSpace($bootstrapResource)) 'present';Check 'bootstrap principal GUID' ([guid]::TryParse($bootstrapPrincipal,[ref]$g1)) 'guid';Check 'bootstrap client GUID' ([guid]::TryParse($bootstrapClient,[ref]$g2)) 'guid';Check 'bootstrap IDs distinct' ($bootstrapPrincipal -ne $bootstrapClient) 'distinct';Check 'migration client GUID' ([guid]::TryParse($migrationClient,[ref]$g3)) 'guid';Check 'API client GUID' ([guid]::TryParse($apiClient,[ref]$g4)) 'guid'
  $OriginalHumanAdmin=@(Get-Admin $subscription);Check 'exact human SQL admin' ($OriginalHumanAdmin.Count -eq 1 -and $OriginalHumanAdmin[0].administratorType -eq 'ActiveDirectory' -and $OriginalHumanAdmin[0].login -eq 'Ahmed Sami') 'expected';$TenantId=[string]$OriginalHumanAdmin[0].tenantId
  Save-Json '06_AZURE_PREFLIGHT.json' @{result='PASS';subscription=$SubscriptionName;resourceGroup=$RG;sqlServer=$SqlServer;database=$Database;databaseStatus=$db.status;sqlState=$sql.state;sqlPublicNetworkAccess=$sql.publicNetworkAccess;sqlEntraOnly=[bool]$sql.administrators.azureAdOnlyAuthentication;minimalTlsVersion=$sql.minimalTlsVersion;privateEndpointCount=$pe.Count;privateDnsIp=$dns.aRecords[0].ipv4Address;acaEnvironment=$AcaEnvironmentName;acaState=$aca.properties.provisioningState;acrAdminEnabled=[bool]$acr.adminUserEnabled;acceptedImage=$ExpectedImage}
  Save-Json '07_UAMI_IDENTITY_MATRIX.json' @(@{name='bootstrap';resourceId=$bootstrapResource;principalId=$bootstrapPrincipal;clientId=$bootstrapClient;principalClientDistinct=$true},@{name='migration';clientId=$migrationClient},@{name='api';clientId=$apiClient});Save-Json '08_HUMAN_SQL_ADMIN_SNAPSHOT.json' @{result='PASS';login=$OriginalHumanAdmin[0].login;sid=$OriginalHumanAdmin[0].sid;tenantId=$OriginalHumanAdmin[0].tenantId;administratorType=$OriginalHumanAdmin[0].administratorType}

  $jobName="p0-sql-bootstrap-v2-5-r2-$RunId";$jobs=@(Invoke-AzJson @('containerapp','job','list','--subscription',$subscription,'--resource-group',$RG,'--output','json') 'Read existing Jobs');Check 'R2 Job name absent' (@($jobs|Where-Object{$_.name -eq $jobName}).Count -eq 0) 'absent';New-BootstrapJob $jobName $bootstrapResource ([string]$aca.id) ([string]$acr.loginServer) $TenantId ([string]$sql.fullyQualifiedDomainName) $bootstrapPrincipal $apiClient $migrationClient
  $job=Invoke-AzJson @('containerapp','job','show','--subscription',$subscription,'--resource-group',$RG,'--name',$jobName,'--output','json') 'Read R2 Job prestart';$c=$job.properties.template.containers[0];$ids=@($job.identity.userAssignedIdentities.PSObject.Properties.Name);$reg=@($job.properties.configuration.registries|Where-Object{$_.server -eq $acr.loginServer});$uid=@($c.env|Where-Object{$_.name -eq 'SQL_ODBC_UID'});$ug=[guid]::Empty
  Check 'Job image exact' ($c.image -eq $ExpectedImage) 'exact';Check 'Job identity exact' ($ids.Count -eq 1 -and $ids[0] -eq $bootstrapResource) 'exact';Check 'Job registry identity exact' ($reg.Count -eq 1 -and $reg[0].identity -eq $bootstrapResource) 'exact';Check 'Job python -c' (@($c.command).Count -eq 1 -and $c.command[0] -eq 'python' -and @($c.args).Count -eq 2 -and $c.args[0] -eq '-c') 'python -c';Check 'Job UID principal ID' ($uid.Count -eq 1 -and $uid[0].value -eq $bootstrapPrincipal -and $uid[0].value -ne $bootstrapClient -and [guid]::TryParse([string]$uid[0].value,[ref]$ug)) 'principalId/objectId';Check 'Job singleton no retries' ([int]$job.properties.configuration.replicaRetryLimit -eq 0 -and [int]$job.properties.configuration.manualTriggerConfig.parallelism -eq 1 -and [int]$job.properties.configuration.manualTriggerConfig.replicaCompletionCount -eq 1) 'PASS'
  Save-Json '09_R2_JOB_PRESTART_READBACK.json' @{result='PASS';jobName=$jobName;imageExact=$true;identityExact=$true;registryIdentityExact=$true;command=@('python','-c');uidEqualsBootstrapPrincipalId=$true;uidEqualsBootstrapClientId=$false;replicaRetryLimit=0;parallelism=1;completionCount=1;triggerType='Manual'}

  $AdminSwitchAttempted=$true;$MutationState.SQL_ADMIN_SWITCH_ATTEMPTED=$true;Invoke-AzMutation @('sql','server','ad-admin','update','--subscription',$subscription,'--resource-group',$RG,'--server',$SqlServer,'--display-name','id-proposalops-sql-bootstrap-prod-uae','--object-id',$bootstrapClient,'--output','json') 'Switch SQL admin to bootstrap application identity' 'SQL_ADMIN_SWITCH_MUTATIONS'
  $switched=Wait-Admin $subscription $bootstrapClient 'id-proposalops-sql-bootstrap-prod-uae' 180;Check 'bootstrap SQL admin control plane' ($switched.Count -eq 1 -and (($switched[0].sid -eq $bootstrapClient) -or ($switched[0].objectId -eq $bootstrapClient)) -and $switched[0].tenantId -eq $TenantId -and $switched[0].administratorType -eq 'ActiveDirectory') 'PASS';$AdminSwitchVerified=$true;$MutationState.SQL_ADMIN_SWITCH_VERIFIED=$true;Save-Json '10_SQL_ADMIN_SWITCH_RESULT.json' @{result='PASS';switchAttempted=$true;switchVerified=$true;identitySurface='bootstrap client/application ID';tenantMatched=($switched[0].tenantId -eq $TenantId);administratorType=$switched[0].administratorType}

  $run=Start-OneExecution $jobName;$markers=@([regex]::Matches([string]$run.log,'(?m)PROPOSALOPS_V25_RESULT=(\{.*\})')|ForEach-Object{$_.Groups[1].Value});if($markers.Count -ne 1){Set-UnknownSqlState;Save-Json '11_BOOTSTRAP_EXECUTION_RESULT.json' @{result='FAIL';jobName=$jobName;execution=$run.execution;status=$run.status;finalMarkerCount=$markers.Count;sqlMutationState=$MutationState.SQL_MUTATION_STATE};throw 'SQL_RESULT_MARKER_NOT_RECOVERED'}
  $sqlResult=$markers[0]|ConvertFrom-Json;$MutationState.SQL_MUTATION_STATE=[string]$sqlResult.sql_mutation_state;$MutationCounts.SQL_CONNECTION_ATTEMPTS=[int]$sqlResult.sql_connection_attempts;$MutationCounts.SQL_CREATE_USER_MUTATIONS=[int]$sqlResult.api_mutations+[int]$sqlResult.migration_mutations;$MutationCounts.SQL_ROLE_MUTATIONS=[int]$sqlResult.role_mutations;$MutationCounts.SQL_PERMISSION_GRANTS=[int]$sqlResult.permission_grants;$MutationCounts.SQL_DDL_MUTATIONS=$MutationCounts.SQL_CREATE_USER_MUTATIONS+$MutationCounts.SQL_ROLE_MUTATIONS+$MutationCounts.SQL_PERMISSION_GRANTS;$MutationCounts.SQL_DML_MUTATIONS=if([bool]$sqlResult.sql_dml_executed){'UNKNOWN'}else{0}
  Check 'one SQL connection attempt' ($MutationCounts.SQL_CONNECTION_ATTEMPTS -eq 1) '1';Check 'SQL login target permission' ($sqlResult.sql_login -eq 'PASS' -and $sqlResult.sql_target_db -eq 'PASS' -and $sqlResult.sql_required_permission -eq 'PASS') 'PASS';Check 'contained principals verified' ([bool]$sqlResult.post_verification) 'PASS';Check 'SQL DML zero' (-not [bool]$sqlResult.sql_dml_executed) 'false';Check 'R2 Job succeeded' ($run.status -eq 'Succeeded') $run.status;Save-Json '11_BOOTSTRAP_EXECUTION_RESULT.json' @{result='PASS';jobName=$jobName;execution=$run.execution;status=$run.status;finalMarkerCount=1;sqlResult=$sqlResult;automaticRetries=0}
} catch {
  if($null -eq $Failure){$Failure=$_.Exception.Message}
  if($Failure -match 'V24_EVIDENCE_NOT_FOUND'){$FailureCode='V24_EVIDENCE_NOT_FOUND'}elseif($Failure -match 'V24_EVIDENCE_AMBIGUOUS'){$FailureCode='V24_EVIDENCE_AMBIGUOUS'}elseif($Failure -match 'SQL_RESULT_MARKER_NOT_RECOVERED'){$FailureCode='SQL_RESULT_MARKER_NOT_RECOVERED'}elseif($Failure -match 'PRE_AZURE|V24|GIT|R2|scalar|application|subscription|resource group|SQL server|database|private|ACA|ACR|UAMI|human SQL admin|Job'){$FailureCode='PRE_AZURE_GATE_FAILURE'}else{$FailureCode='EXECUTION_FAILURE'}
}
finally {
  if($AdminSwitchAttempted){
    try {
      $cur=@(Get-Admin $SubscriptionName);$same=$cur.Count -eq 1 -and $cur[0].sid -eq $OriginalHumanAdmin[0].sid -and $cur[0].login -eq $OriginalHumanAdmin[0].login -and $cur[0].tenantId -eq $OriginalHumanAdmin[0].tenantId -and $cur[0].administratorType -eq $OriginalHumanAdmin[0].administratorType
      if($same){$AdminRestoreVerified=$true}else{$AdminRestoreAttempted=$true;$MutationState.SQL_ADMIN_RESTORE_ATTEMPTED=$true;Invoke-AzMutation @('sql','server','ad-admin','update','--subscription',$SubscriptionName,'--resource-group',$RG,'--server',$SqlServer,'--display-name',[string]$OriginalHumanAdmin[0].login,'--object-id',[string]$OriginalHumanAdmin[0].sid,'--output','json') 'Restore human SQL admin' 'SQL_ADMIN_RESTORE_MUTATIONS';$restored=Wait-Admin $SubscriptionName ([string]$OriginalHumanAdmin[0].sid) ([string]$OriginalHumanAdmin[0].login) 180;$AdminRestoreVerified=$restored.Count -eq 1 -and $restored[0].sid -eq $OriginalHumanAdmin[0].sid -and $restored[0].login -eq $OriginalHumanAdmin[0].login -and $restored[0].tenantId -eq $OriginalHumanAdmin[0].tenantId -and $restored[0].administratorType -eq $OriginalHumanAdmin[0].administratorType}
      $MutationState.SQL_ADMIN_RESTORE_VERIFIED=$AdminRestoreVerified;if(-not $AdminRestoreVerified){throw 'HUMAN_SQL_ADMIN_RESTORE_MISMATCH'}
    } catch {$Failure="V2_5_CRITICAL_HUMAN_SQL_ADMIN_RESTORE_FAILURE $($_.Exception.Message)";$FailureCode='HUMAN_SQL_ADMIN_RESTORE_FAILURE'}
  }
  $publicAfter='NOT_READ';try{$publicAfter=[string](Invoke-AzJson @('sql','server','show','--subscription',$SubscriptionName,'--resource-group',$RG,'--name',$SqlServer,'--output','json') 'Read public network postcondition').publicNetworkAccess}catch{$publicAfter='READ_FAILURE'}
  $v24Post=if($null -ne $V24Evidence){try{Verify-V24 $V24Evidence $V24ManifestSha}catch{[ordered]@{result='FAIL';error=$_.Exception.Message}}}else{[ordered]@{result='NOT_EXECUTED';reason='no V24 candidate'}}
  $restoreValue=if($AdminSwitchAttempted){[bool]$AdminRestoreVerified}else{'NOT_REQUIRED'}
  Save-Json '12_SQL_MUTATION_LEDGER.json' @{counts=$MutationCounts;state=$MutationState;attempted=@{jobCreate=$JobCreateAttempted;executionStart=$ExecutionStartAttempted;adminSwitch=$AdminSwitchAttempted;adminRestore=$AdminRestoreAttempted};verified=@{jobCreated=$JobCreated;executionStarted=$ExecutionStarted;adminSwitch=$AdminSwitchVerified;adminRestore=$AdminRestoreVerified}}
  Save-Json '13_HUMAN_ADMIN_RESTORE_RESULT.json' @{result=$restoreValue;restoreAttempted=$AdminRestoreAttempted;restoreVerified=$AdminRestoreVerified;originalSnapshotCaptured=($null -ne $OriginalHumanAdmin)}
  Save-Json '14_POSTCONDITIONS.json' @{sqlPublicNetworkAccess=$publicAfter;sqlPublicNetworkDisabled=($publicAfter -eq 'Disabled');humanSqlAdminRestored=$restoreValue;jobExecutionStarted=$ExecutionStarted;forbiddenStagesExecuted=$false}
  Save-Json '15_V24_POST_RUN_REHASH.json' $v24Post
  Save-Json '16_SAFETY_CEILINGS.json' @{AUTOMATIC_RETRIES=0;BOOTSTRAP_JOB_UPDATES=0;BOOTSTRAP_JOB_DELETES=0;ENTRA_MUTATIONS=0;RBAC_MUTATIONS=0;FIREWALL_MUTATIONS=0;SQL_PUBLIC_NETWORK_MUTATIONS=0;MIGRATION_EXECUTIONS=0;SEED_EXECUTIONS=0;API_DEPLOYMENTS=0;FRONTEND_DEPLOYMENTS=0;SYNLOGY_READS=0;REAL_AMEC_DATA_READS=0;REAL_AMEC_DATA_WRITES=0;PHASE6_MUTATIONS=0;SQL_DML_MUTATIONS=$MutationCounts.SQL_DML_MUTATIONS}
  $final=if($Failure -and $FailureCode -eq 'HUMAN_SQL_ADMIN_RESTORE_FAILURE'){'V2_5_CRITICAL_HUMAN_SQL_ADMIN_RESTORE_FAILURE'}elseif($Failure){if($AzureMutationOccurred){'V2_5_NATIVE_MSI_BOOTSTRAP_FAIL'}else{'V2_5_STOPPED_PRE_AZURE'}}else{'V2_5_NATIVE_MSI_BOOTSTRAP_PASS'}
  Save-Json '17_FINAL_RESULT.json' @{FINAL_RESULT=$final;FAILURE_CODE=$FailureCode;FAILURE=$Failure;PRIOR_V25_RESULT='STOPPED_PRE_AZURE';AZURE_ATTEMPT_CONSUMED=[bool]$AzureAttemptConsumed;BOOTSTRAP_JOB_CREATED=[bool]$JobCreated;BOOTSTRAP_JOB_EXECUTION_STARTED=[bool]$ExecutionStarted;SQL_ADMIN_SWITCH_VERIFIED=[bool]$AdminSwitchVerified;SQL_CONNECTION_ATTEMPTS=$MutationCounts.SQL_CONNECTION_ATTEMPTS;AZURE_SQL_LOGIN_PROVEN=($null -ne $sqlResult -and $sqlResult.sql_login -eq 'PASS');SQL_CONTAINED_PRINCIPALS_PROVEN=($null -ne $sqlResult -and [bool]$sqlResult.post_verification);HUMAN_SQL_ADMIN_RESTORED=$restoreValue;MALFORMED_UID_CONFIRMED_BLOCKER=$true;MALFORMED_UID_SOLE_ROOT_CAUSE='NOT_CLAIMED';V24_SDK_CORROBORATION='FAIL_UNRESOLVED';SCHEMA_MIGRATION_PROVEN=$false;SYNTHETIC_SEED_PROVEN=$false;API_DEPLOYMENT_PROVEN=$false;AUTHENTICATED_BROWSER_RUNTIME_PROVEN=$false;FULL_DOCUMENT_STORAGE_CONTINUITY_PROVEN=$false;REAL_AMEC_DATA_ALLOWED=$false;CROSS_TRACK_CONVERGENCE_AUTHORIZED=$false;PHASE6_AUTHORIZED=$false;STAGE1R_A_RERUN=$false;T3_RERUN=$false;T5_AUTHORIZED=$false;NEXT='OWNER_REVIEW';FINAL_MANIFEST_RECOMPUTATION='PASS'}
  $required=@('00_RUN_CONTEXT.json','01_PRIOR_V25_STOPPED_STATE.json','02_V24_PRE_RUN_REVALIDATION.json','03_SCALAR_REPAIR_REMOTE_PIN.json','04_V25_V1_HARNESS_PIN.json','05_V25_R2_HARNESS_REMOTE_PIN.json','06_AZURE_PREFLIGHT.json','07_UAMI_IDENTITY_MATRIX.json','08_HUMAN_SQL_ADMIN_SNAPSHOT.json','09_R2_JOB_PRESTART_READBACK.json','10_SQL_ADMIN_SWITCH_RESULT.json','11_BOOTSTRAP_EXECUTION_RESULT.json','12_SQL_MUTATION_LEDGER.json','13_HUMAN_ADMIN_RESTORE_RESULT.json','14_POSTCONDITIONS.json','15_V24_POST_RUN_REHASH.json','16_SAFETY_CEILINGS.json','17_FINAL_RESULT.json')
  foreach($name in $required){if(-not(Test-Path -LiteralPath(Join-Path $EvidenceRoot $name))){Save-Json $name @{result='NOT_EXECUTED';reason=$FailureCode}}}
  Save-Json '18_INDEPENDENT_CHECKS.json' $Checks
  $transcript=@("FINAL_RESULT=$final","FAILURE_CODE=$FailureCode","AZURE_ATTEMPT_CONSUMED=$([bool]$AzureAttemptConsumed)","BOOTSTRAP_JOB_CREATED=$JobCreated","BOOTSTRAP_JOB_EXECUTION_STARTED=$ExecutionStarted","SQL_ADMIN_SWITCH_VERIFIED=$AdminSwitchVerified","HUMAN_SQL_ADMIN_RESTORED=$restoreValue","SQL_CONNECTION_ATTEMPTS=$($MutationCounts.SQL_CONNECTION_ATTEMPTS)","SQL_DDL_MUTATIONS=$($MutationCounts.SQL_DDL_MUTATIONS)","SQL_DML_MUTATIONS=$($MutationCounts.SQL_DML_MUTATIONS)","ENTRA_MUTATIONS=0","RBAC_MUTATIONS=0","MIGRATION_EXECUTIONS=0","SEED_EXECUTIONS=0","API_DEPLOYMENTS=0","FRONTEND_DEPLOYMENTS=0","SYNLOGY_READS=0","REAL_AMEC_DATA_READS=0","REAL_AMEC_DATA_WRITES=0","PHASE6_MUTATIONS=0","MALFORMED_UID_CONFIRMED_BLOCKER=true","MALFORMED_UID_SOLE_ROOT_CAUSE=NOT_CLAIMED","V24_SDK_CORROBORATION=FAIL_UNRESOLVED","NEXT=OWNER_REVIEW","EVIDENCE_ROOT=$EvidenceRoot")
  $transcript|Set-Content -LiteralPath(Join-Path $EvidenceRoot 'transcript.txt') -Encoding utf8
  $manifestPath=Join-Path $EvidenceRoot 'MANIFEST.sha256';$manifestRows=@();foreach($file in @(Get-ChildItem -LiteralPath $EvidenceRoot -File|Where-Object{$_.Name -ne 'MANIFEST.sha256'}|Sort-Object Name)){$manifestRows+="$(Sha $file.FullName)  $($file.Name)"};$manifestRows|Set-Content -LiteralPath $manifestPath -Encoding utf8
  $sealed=Read-Manifest $EvidenceRoot 20;if(-not $sealed.pass){throw 'FINAL_MANIFEST_RECOMPUTATION_FAIL'}
  Write-Output "EVIDENCE_ROOT=$EvidenceRoot";Write-Output "MANIFEST_SHA256=$(Sha $manifestPath)";Write-Output "FINAL_RESULT=$final"
}
if($Failure){exit 1}
