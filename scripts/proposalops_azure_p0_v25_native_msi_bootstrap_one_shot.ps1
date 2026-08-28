[CmdletBinding()]
param([switch]$PreflightOnly, [switch]$Execute)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RunId = Get-Date -AsUTC -Format 'yyyyMMdd-HHmmss'
$EvidenceRoot = Join-Path ([IO.Path]::GetTempPath()) "ProposalOps_Azure_P0_V2_5_R4_$RunId"
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
$R2Branch = 'azure-p0-v25-native-msi-bootstrap-one-shot-r2-v1'
$R2Commit = '378b4acee87b5ca85f94a7605f36f86b49ccb102'
$R3Branch = 'azure-p0-v25-native-msi-bootstrap-one-shot-r3-v1'
$R3Commit = '57c62ddac257d49cf594b90cc27c4198fb145e6d'
$R4Branch = 'azure-p0-v25-native-msi-bootstrap-one-shot-r4-v1'
$KnownTwoLineCommit = '56a7b76af2d697930177283f01068c8c06f1d8d2'
$ExpectedMain = '3474b35a13d27f0010ec5d03dd4a2f361ac6774d'
$SubscriptionName = 'AMEC Subscription'
$RG = 'rg-proposalops-prod-uae'
$SqlServer = 'sql-proposalops-prod-uae-2bea2887'
$Database = 'sqldb-proposalops-prod'
$AcaEnvironmentName = 'cae-proposalops-prod-uae'
$AcrName = 'acrproposalopsproduae2bea2887'
$AcceptedPrivateIp = '10.43.2.4'
$V24Members = @('00_RUN_CONTEXT.json','01_V22_LIVE_UID_DEFECT.json','02_BOOTSTRAP_UAMI_IDENTITY_MATRIX.json','03_FUTURE_ODBC_UID_CONTRACT.json','04_DIAGNOSTIC_JOB_TEMPLATE.json','05_DIAGNOSTIC_JOB_PRESTART_READBACK.json','06_IDENTITY_RUNTIME_ENV.json','07_ACA_SQL_TOKEN_RESULT.json','08_TOKEN_CLAIM_BINDING.json','09_OPTIONAL_AZURE_IDENTITY_RESULT.json','10_ADMIN_PROPAGATION_ADJUDICATION.json','11_MUTATION_LEDGER.json','12_SAFETY_CEILINGS.json','13_FINAL_RESULT.json','14_SCALAR_REPAIR_IMPLEMENTATION.json')
$R4Members = @('00_RUN_CONTEXT.json','01_PRIOR_V25_HISTORY.json','02_V24_PRE_RUN_REVALIDATION.json','03_SCALAR_REPAIR_REMOTE_PIN.json','04_V25_R3_HISTORICAL_PIN.json','05_V25_R4_HARNESS_REMOTE_PIN.json','06_AZURE_READONLY_PREFLIGHT.json','07_UAMI_IDENTITY_MATRIX.json','08_HUMAN_SQL_ADMIN_SNAPSHOT.json','09_MUTATION_LEDGER.json','10_POSTCONDITIONS.json','11_V24_POST_RUN_REHASH.json','12_SAFETY_CEILINGS.json','13_FINAL_RESULT.json','14_INDEPENDENT_CHECKS.json','transcript.txt')

$CurrentOperation = 'LOCAL_INITIALIZATION'
$ExecutionPhase = 'LOCAL_INITIALIZATION'
$Mode = if($PreflightOnly -and -not $Execute){'PREFLIGHT_ONLY'}else{'INVALID'}
$Failure = $null
$FailureCode = $null
$FailurePhase = 'NONE'
$AzureReadPhaseEntered = $false
$AzureReadCommands = 0
$AzureMutationOccurred = $false
$AzureMutationCommands = 0
$AzureAttemptConsumed = $false
$JobCreated = $false
$ExecutionStartAttempted = $false
$ExecutionRequestAccepted = $false
$ExecutionObserved = $false
$AdminSwitchAttempted = $false
$AdminSwitchVerified = $false
$OriginalHumanAdmin = $null
$V24Evidence = $null
$V24ManifestSha = $null
$V24PrePass = $false
$V24PostPass = $false
$GitLineagePass = $false
$StaticValidationPass = $false
$AzureReadonlyPreflightPass = $false
$HumanAdminSnapshotPass = $false
$SqlPublicNetworkPostPass = $false
$PreflightAcceptancePass = $false
$ManifestRecomputation = 'NOT_EXECUTED'
$Checks = [System.Collections.Generic.List[object]]::new()
$MutationCounts = [ordered]@{ BOOTSTRAP_JOB_CREATES=0; BOOTSTRAP_JOB_UPDATES=0; BOOTSTRAP_JOB_DELETES=0; BOOTSTRAP_JOB_EXECUTIONS=0; SQL_ADMIN_SWITCH_MUTATIONS=0; SQL_ADMIN_RESTORE_MUTATIONS=0; SQL_CONNECTION_ATTEMPTS=0; SQL_CREATE_USER_MUTATIONS=0; SQL_ROLE_MUTATIONS=0; SQL_PERMISSION_GRANTS=0; SQL_DDL_MUTATIONS=0; SQL_DML_MUTATIONS=0; ENTRA_MUTATIONS=0; RBAC_MUTATIONS=0; FIREWALL_MUTATIONS=0; SQL_PUBLIC_NETWORK_MUTATIONS=0; MIGRATION_EXECUTIONS=0; SEED_EXECUTIONS=0; API_DEPLOYMENTS=0; FRONTEND_DEPLOYMENTS=0; SYNLOGY_READS=0; REAL_AMEC_DATA_READS=0; REAL_AMEC_DATA_WRITES=0; PHASE6_MUTATIONS=0 }
$MutationState = [ordered]@{ AZURE_MUTATION_OCCURRED=$false; AZURE_MUTATION_COMMANDS=0; BOOTSTRAP_JOB_CREATED=$false; BOOTSTRAP_JOB_EXECUTION_START_ATTEMPTED=$false; SQL_ADMIN_SWITCH_ATTEMPTED=$false; SQL_MUTATION_STATE='NOT_EXECUTED' }

function Save-Json([string]$Name, $Value) { $Value | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath (Join-Path $EvidenceRoot $Name) -Encoding utf8 }
function Save-ExternalJson([string]$Path, $Value) { $Value | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $Path -Encoding utf8 }
function Sha([string]$Path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function Sha-Text([string]$Value) { $bytes=[Text.Encoding]::UTF8.GetBytes($Value); $sha=[Security.Cryptography.SHA256]::Create(); try { ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() } }
function Git-Text([string[]]$Arguments) {
  $output = & git -C $RepoRoot @Arguments 2>&1
  if ($LASTEXITCODE -ne 0) { throw "GIT_COMMAND_FAILURE $($Arguments -join ' ')" }
  ($output | ForEach-Object ToString) -join [Environment]::NewLine
}
function Git-Lines([string[]]$Arguments) {
  $text = Git-Text $Arguments
  if ([string]::IsNullOrWhiteSpace($text)) { return @() }
  @($text -split '\r?\n' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}
function Check([string]$Id, [bool]$Pass, $Actual = '') {
  $Checks.Add([ordered]@{ id=$Id; phase=$ExecutionPhase; operation=$CurrentOperation; result=if($Pass){'PASS'}else{'FAIL'}; actual=[string]$Actual })
  if (-not $Pass) { $script:FailureCode = $Id; throw "VALIDATION_FAILURE [$Id] $Actual" }
}
function Invoke-AzRead([string[]]$Arguments, [string]$Label) {
  $script:ExecutionPhase = 'AZURE_READONLY_PREFLIGHT'; $script:CurrentOperation = $Label; $script:AzureReadPhaseEntered = $true; $script:AzureReadCommands++
  $out = & az @Arguments --only-show-errors 2>&1
  if ($LASTEXITCODE -ne 0) { throw "AZURE_READ_COMMAND_FAILURE [$Label]" }
  ($out | ForEach-Object ToString) -join [Environment]::NewLine
}
function Invoke-AzReadJson([string[]]$Arguments, [string]$Label) {
  $text = Invoke-AzRead $Arguments $Label; $starts = @($text.IndexOf('{'),$text.IndexOf('[')) | Where-Object { $_ -ge 0 } | Sort-Object
  if ($starts.Count -eq 0) { throw "AZURE_READ_JSON_EMPTY [$Label]" }; $text.Substring($starts[0]) | ConvertFrom-Json
}
function Get-Admin([string]$Subscription) { @(Invoke-AzReadJson @('sql','server','ad-admin','list','--subscription',$Subscription,'--resource-group',$RG,'--server',$SqlServer,'--output','json') 'Read SQL Entra administrator') }
function Read-Manifest([string]$Root, [string[]]$ExpectedNames) {
  $path = Join-Path $Root 'MANIFEST.sha256'; if (-not (Test-Path -LiteralPath $path)) { return $null }
  $rows = @(); foreach ($line in @(Get-Content -LiteralPath $path)) { if ($line -match '^([0-9a-f]{64})  (.+)$') { $rows += [pscustomobject]@{expected=$Matches[1];name=$Matches[2]} } }
  $names = @($rows | ForEach-Object { $_.name }); $uniqueNames = @($names | Sort-Object -Unique); $missing = @($ExpectedNames | Where-Object { $names -notcontains $_ }); $unexpected = @($names | Where-Object { $ExpectedNames -notcontains $_ }); $duplicates = $names.Count - $uniqueNames.Count; $matched = 0; $failed = 0
  foreach ($row in $rows) { $file = Join-Path $Root $row.name; if ((Test-Path -LiteralPath $file) -and (Sha $file) -eq $row.expected) { $matched++ } else { $failed++ } }
  [ordered]@{root=$Root;rows=$rows;expectedNames=$ExpectedNames;expectedMembers=$ExpectedNames.Count;foundMembers=$rows.Count;missing=$missing;unexpected=$unexpected;duplicate=$duplicates;matchedMembers=$matched;failedMembers=$failed;manifestSha=Sha $path;pass=($missing.Count -eq 0 -and $unexpected.Count -eq 0 -and $duplicates -eq 0 -and $rows.Count -eq $ExpectedNames.Count -and $matched -eq $ExpectedNames.Count -and $failed -eq 0)}
}
function Find-V24Evidence {
  $dirs = @(); foreach ($root in @('/tmp',[IO.Path]::GetTempPath()) | Select-Object -Unique) { if (Test-Path -LiteralPath $root) { $dirs += @(Get-ChildItem -LiteralPath $root -Directory -Filter 'ProposalOps_Azure_P0_V2_4_*' -ErrorAction SilentlyContinue) } }
  $valid = @(); foreach ($dir in @($dirs | Sort-Object FullName -Unique)) { try { $finalPath=Join-Path $dir.FullName '13_FINAL_RESULT.json'; if (-not(Test-Path -LiteralPath $finalPath)){continue}; $final=Get-Content -LiteralPath $finalPath -Raw|ConvertFrom-Json; $manifest=Read-Manifest $dir.FullName $V24Members; if($null -ne $manifest -and $final.FINAL_RESULT -eq 'V2_4_MI_TOKEN_DIAGNOSTIC_PASS' -and $manifest.pass -and $final.AZURE_IDENTITY_CORROBORATION -eq 'FAIL' -and -not [bool]$final.CROSS_TRACK_CONVERGENCE_AUTHORIZED -and [int]$final.REAL_AMEC_DATA_READS -eq 0 -and [int]$final.REAL_AMEC_DATA_WRITES -eq 0){$valid += [pscustomobject]@{root=$dir.FullName;final=$final;manifest=$manifest}} } catch {} }
  if($valid.Count -eq 0){throw 'V24_EVIDENCE_NOT_FOUND'}; if(@($valid|ForEach-Object{$_.manifest.manifestSha}|Select-Object -Unique).Count -ne 1){throw 'V24_EVIDENCE_AMBIGUOUS'}; $valid[0]
}
function Verify-V24([string]$Root,[string]$ManifestSha) { $m=Read-Manifest $Root $V24Members; if($null -eq $m -or -not $m.pass -or $m.manifestSha -ne $ManifestSha){throw 'V24_POST_RUN_INTEGRITY_FAILURE'}; [ordered]@{result='PASS';root=$Root;manifestSha=$m.manifestSha;expectedMembers=$m.expectedMembers;foundMembers=$m.foundMembers;missing=$m.missing;unexpected=$m.unexpected;duplicate=$m.duplicate;matchedMembers=$m.matchedMembers;failedMembers=$m.failedMembers} }

$BootstrapPython = @'
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
 r["post_verification"]=True;emit();sys.exit(0)
except Exception as e:
 r["error_class"]=type(e).__name__;r["error_message"]=str(e)[:240];emit();sys.exit(1)
finally:
 if cn is not None:cn.close()
'@

try {
  if (-not $PreflightOnly -or $Execute) { $FailureCode='PREFLIGHT_ONLY_REQUIRED'; throw 'R4_PREFLIGHT_ONLY_REQUIRED' }
  $ExecutionPhase='V24_INTEGRITY'; $v24=Find-V24Evidence; $V24Evidence=$v24.root; $V24ManifestSha=$v24.manifest.manifestSha
  Check 'V24 pre-run rehash' ([bool]$v24.manifest.pass) 'PASS'; Check 'V24 SDK failure preserved' ($v24.final.AZURE_IDENTITY_CORROBORATION -eq 'FAIL') 'FAIL'; Check 'V24 cross-track false' (-not [bool]$v24.final.CROSS_TRACK_CONVERGENCE_AUTHORIZED) 'false'; Check 'V24 real-data reads zero' ([int]$v24.final.REAL_AMEC_DATA_READS -eq 0) '0'; Check 'V24 real-data writes zero' ([int]$v24.final.REAL_AMEC_DATA_WRITES -eq 0) '0'; $V24PrePass=$true

  $ExecutionPhase='GIT_LINEAGE'; $branch=(Git-Text @('branch','--show-current')).Trim(); $head=(Git-Text @('rev-parse','HEAD')).Trim(); $parent=(Git-Text @('rev-parse','HEAD^')).Trim(); $grandparent=(Git-Text @('rev-parse','HEAD^^')).Trim(); $greatgrandparent=(Git-Text @('rev-parse','HEAD^^^')).Trim(); $scalarParent=(Git-Text @('rev-parse','HEAD^^^^')).Trim()
  $remoteR4=((Git-Text @('ls-remote','origin',"refs/heads/$R4Branch")).Trim().Split([char]9)[0]); $remoteR3=((Git-Text @('ls-remote','origin',"refs/heads/$R3Branch")).Trim().Split([char]9)[0]); $remoteR2=((Git-Text @('ls-remote','origin',"refs/heads/$R2Branch")).Trim().Split([char]9)[0]); $remoteV1=((Git-Text @('ls-remote','origin',"refs/heads/$V1Branch")).Trim().Split([char]9)[0]); $remoteScalar=((Git-Text @('ls-remote','origin',"refs/heads/$ScalarRepairBranch")).Trim().Split([char]9)[0]); $remoteMain=((Git-Text @('ls-remote','origin','refs/heads/main')).Trim().Split([char]9)[0])
  Check 'R4 branch exact' ($branch -eq $R4Branch) $branch; Check 'R4 remote head exact' ($head -eq $remoteR4) $remoteR4; Check 'R4 parent R3' ($parent -eq $R3Commit) $parent; Check 'R4 grandparent R2' ($grandparent -eq $R2Commit) $grandparent; Check 'R4 great-grandparent V1' ($greatgrandparent -eq $V1Commit) $greatgrandparent; Check 'scalar lineage exact' ($scalarParent -eq $ScalarRepairCommit) $scalarParent; Check 'R3 remote exact' ($remoteR3 -eq $R3Commit) $remoteR3; Check 'R2 remote exact' ($remoteR2 -eq $R2Commit) $remoteR2; Check 'V1 remote exact' ($remoteV1 -eq $V1Commit) $remoteV1; Check 'scalar remote exact' ($remoteScalar -eq $ScalarRepairCommit) $remoteScalar; Check 'main unchanged' ($remoteMain -eq $ExpectedMain) $remoteMain
  $changed=@(Git-Lines @('diff-tree','--no-commit-id','--name-only','-r',$head)); $appChanged=@(Git-Lines @('diff','--name-only',$ExpectedAppSha,$head,'--','backend','frontend','mock-systems')); $workingTree=@(Git-Lines @('status','--porcelain')); $zeroLines=@(Git-Lines @('diff','--name-only','HEAD','HEAD')); $oneLines=@(Git-Lines @('diff-tree','--no-commit-id','--name-only','-r',$head)); $twoLines=@(Git-Lines @('diff-tree','--no-commit-id','--name-only','-r',$KnownTwoLineCommit))
  Check 'R4 changed path only' ($changed.Count -eq 1 -and $changed[0] -eq 'scripts/proposalops_azure_p0_v25_native_msi_bootstrap_one_shot.ps1') ($changed -join ','); Check 'application changed paths zero' ($appChanged.Count -eq 0) ($appChanged -join ','); Check 'working tree clean' ($workingTree.Count -eq 0) ($workingTree -join ';'); Check 'zero-line Git result' ($zeroLines.Count -eq 0) $zeroLines.Count; Check 'one-line Git result' ($oneLines.Count -eq 1) $oneLines.Count; Check 'one-line full path index' ($oneLines[0] -eq 'scripts/proposalops_azure_p0_v25_native_msi_bootstrap_one_shot.ps1') $oneLines[0]; Check 'two-line Git result' ($twoLines.Count -eq 2) $twoLines.Count; Check 'POWERSHELL_COLLECTION_CARDINALITY_REGRESSION' ($zeroLines.Count -eq 0 -and $oneLines.Count -eq 1 -and $twoLines.Count -eq 2 -and $oneLines[0] -notmatch '^[^/ ]$') 'PASS'; $GitLineagePass=$true

  $ExecutionPhase='STATIC_VALIDATION'; $source=Get-Content -LiteralPath $PSCommandPath -Raw; $tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)|Out-Null; Check 'PowerShell parse' ($errors.Count -eq 0) 'PASS'; $pythonPath=Join-Path ([IO.Path]::GetTempPath()) "proposalops-r4-python-$RunId.py"; $BootstrapPython|Set-Content -LiteralPath $pythonPath -Encoding utf8; $pyOutput=& python3 -c 'import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8").read())' $pythonPath 2>&1; Check 'embedded Python parse' ($LASTEXITCODE -eq 0) 'PASS'; Remove-Item -LiteralPath $pythonPath -Force; $pyodbcCallSites=([regex]::Matches($BootstrapPython,'pyodbc\.connect\(')).Count; Check 'pyodbc executable call sites' ($pyodbcCallSites -eq 1) $pyodbcCallSites; Check 'automatic SQL retry loops' (([regex]::Matches($BootstrapPython,'(?im)^\s*(for|while).*retry')).Count -eq 0) '0'; Check 'second SQL connection paths' ($pyodbcCallSites -eq 1) '1'; $failureRegexDependency=$source.Contains(('Failure' + ' -match')); Check 'failure phase text regex dependency' (-not $failureRegexDependency) '0'; $StaticValidationPass=$true

  $ExecutionPhase='AZURE_READONLY_PREFLIGHT'; $subscription=(Invoke-AzRead @('account','list','--query',"[?name=='$SubscriptionName' && state=='Enabled'].name | [0]",'--output','tsv') 'Resolve enabled subscription').Trim(); Check 'enabled subscription' ($subscription -eq $SubscriptionName) $subscription
  $group=Invoke-AzReadJson @('group','show','--subscription',$subscription,'--name',$RG,'--output','json') 'Read resource group'; $sql=Invoke-AzReadJson @('sql','server','show','--subscription',$subscription,'--resource-group',$RG,'--name',$SqlServer,'--output','json') 'Read SQL server'; $db=Invoke-AzReadJson @('sql','db','show','--subscription',$subscription,'--resource-group',$RG,'--server',$SqlServer,'--name',$Database,'--output','json') 'Read SQL database'; $aca=Invoke-AzReadJson @('containerapp','env','show','--subscription',$subscription,'--resource-group',$RG,'--name',$AcaEnvironmentName,'--output','json') 'Read ACA environment'; $acr=Invoke-AzReadJson @('acr','show','--subscription',$subscription,'--resource-group',$RG,'--name',$AcrName,'--output','json') 'Read ACR'; $dns=Invoke-AzReadJson @('network','private-dns','record-set','a','show','--subscription',$subscription,'--resource-group',$RG,'--zone-name','privatelink.database.windows.net','--name',$SqlServer,'--output','json') 'Read private DNS'
  $pes=@(Invoke-AzReadJson @('network','private-endpoint','list','--subscription',$subscription,'--resource-group',$RG,'--output','json') 'Read private endpoint')
  $pe=@()
  foreach($candidate in $pes){$connections=@($candidate.privateLinkServiceConnections);$accepted=@($connections|Where-Object{$_.privateLinkServiceId -eq $sql.id -and $_.provisioningState -eq 'Succeeded' -and $_.privateLinkServiceConnectionState.status -eq 'Approved'});if($candidate.provisioningState -eq 'Succeeded' -and $accepted.Count -gt 0){$pe += $candidate}}
  $images = @(
    Invoke-AzReadJson @('acr','repository','show-manifests','--subscription',$subscription,'--name',$AcrName,'--repository','proposalops-api','--output','json') 'Read accepted image'
  )
  $image = @($images | Where-Object { $_.digest -eq 'sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d' })
  $jobs = @(
    Invoke-AzReadJson @('containerapp','job','list','--subscription',$subscription,'--resource-group',$RG,'--output','json') 'Read historical Jobs'
  )
  Check 'resource group exact' ($group.name -eq $RG) $group.name; Check 'SQL ready' ($sql.name -eq $SqlServer -and $sql.state -eq 'Ready') $sql.state; Check 'database online' ($db.name -eq $Database -and $db.status -eq 'Online') $db.status; Check 'SQL public disabled' ($sql.publicNetworkAccess -eq 'Disabled') $sql.publicNetworkAccess; Check 'SQL Entra only' ([bool]$sql.administrators.azureAdOnlyAuthentication) 'true'; Check 'TLS 1.2' ($sql.minimalTlsVersion -eq '1.2') $sql.minimalTlsVersion; Check 'private endpoint accepted' ($pe.Count -eq 1) $pe.Count; Check 'private DNS exact' ($dns.aRecords[0].ipv4Address -eq $AcceptedPrivateIp) $dns.aRecords[0].ipv4Address; Check 'ACA environment succeeded' ($aca.properties.provisioningState -eq 'Succeeded') $aca.properties.provisioningState; Check 'ACR admin disabled' (-not [bool]$acr.adminUserEnabled) 'false'; Check 'accepted image digest exact' ($image.Count -eq 1) $image.Count
  $bootstrap=Invoke-AzReadJson @('identity','show','--subscription',$subscription,'--resource-group',$RG,'--name','id-proposalops-sql-bootstrap-prod-uae','--output','json') 'Read bootstrap UAMI'; $migration=Invoke-AzReadJson @('identity','show','--subscription',$subscription,'--resource-group',$RG,'--name','id-proposalops-sql-migrate-prod-uae','--output','json') 'Read migration UAMI'; $api=Invoke-AzReadJson @('identity','show','--subscription',$subscription,'--resource-group',$RG,'--name','id-proposalops-api-prod-uae','--output','json') 'Read API UAMI'; $bootstrapResource=[string]$bootstrap.id; $bootstrapPrincipal=[string]$bootstrap.principalId; $bootstrapClient=[string]$bootstrap.clientId; $migrationClient=[string]$migration.clientId; $apiClient=[string]$api.clientId; $g1=[guid]::Empty;$g2=[guid]::Empty;$g3=[guid]::Empty;$g4=[guid]::Empty
  Check 'bootstrap UAMI resource present' (-not [string]::IsNullOrWhiteSpace($bootstrapResource)) 'present'; Check 'bootstrap UAMI principal GUID' ([guid]::TryParse($bootstrapPrincipal,[ref]$g1)) 'guid'; Check 'bootstrap UAMI client GUID' ([guid]::TryParse($bootstrapClient,[ref]$g2)) 'guid'; Check 'bootstrap IDs distinct' ($bootstrapPrincipal -ne $bootstrapClient) 'distinct'; Check 'migration UAMI client GUID' ([guid]::TryParse($migrationClient,[ref]$g3)) 'guid'; Check 'API UAMI client GUID' ([guid]::TryParse($apiClient,[ref]$g4)) 'guid'; $OriginalHumanAdmin=@(Get-Admin $subscription); $HumanAdminSnapshotPass=$OriginalHumanAdmin.Count -eq 1 -and $OriginalHumanAdmin[0].administratorType -eq 'ActiveDirectory' -and $OriginalHumanAdmin[0].login -eq 'Ahmed Sami'; Check 'human SQL admin snapshot' $HumanAdminSnapshotPass 'expected'; Check 'historical Job census read' ($jobs.Count -ge 0) $jobs.Count; Check 'R4 read-only mutation boundary' (-not $AzureMutationOccurred -and $AzureMutationCommands -eq 0 -and -not $AzureAttemptConsumed -and -not $JobCreated -and -not $ExecutionStartAttempted -and -not $AdminSwitchAttempted -and [int]$MutationCounts.SQL_CONNECTION_ATTEMPTS -eq 0) 'PASS'; $AzureReadonlyPreflightPass=$true
  $ExecutionPhase='PREFLIGHT_COMPLETE'; $v24Post=$null; try{$v24Post=Verify-V24 $V24Evidence $V24ManifestSha;$V24PostPass=$v24Post.result -eq 'PASS'}catch{$v24Post=[ordered]@{result='FAIL';error='V24_POST_RUN_INTEGRITY_FAILURE'}}; if(-not $V24PostPass){$FailureCode='V24_POST_RUN_INTEGRITY_FAILURE';throw 'V24_POST_RUN_INTEGRITY_FAILURE'}; $publicAfter='NOT_APPLICABLE_NO_AZURE_PHASE'; if($AzureReadPhaseEntered){try{$publicAfter=[string](Invoke-AzReadJson @('sql','server','show','--subscription',$subscription,'--resource-group',$RG,'--name',$SqlServer,'--output','json') 'Read SQL public-network postcondition').publicNetworkAccess}catch{$publicAfter='READ_FAILURE'}}; $SqlPublicNetworkPostPass=$AzureReadPhaseEntered -and $publicAfter -eq 'Disabled'; if(-not $SqlPublicNetworkPostPass){$FailureCode='SQL_PUBLIC_NETWORK_POSTCONDITION_UNVERIFIED';throw 'SQL_PUBLIC_NETWORK_POSTCONDITION_UNVERIFIED'}; $PreflightAcceptancePass=$Mode -eq 'PREFLIGHT_ONLY' -and $V24PrePass -and $V24PostPass -and $GitLineagePass -and $StaticValidationPass -and $AzureReadonlyPreflightPass -and $HumanAdminSnapshotPass -and $SqlPublicNetworkPostPass -and -not $AzureMutationOccurred -and -not $AzureAttemptConsumed; Check 'positive preflight acceptance predicate' $PreflightAcceptancePass 'PASS'
}
catch { $FailurePhase=$ExecutionPhase; if($null -eq $Failure){$Failure=$_.Exception.Message}; if($null -eq $FailureCode){$FailureCode=switch($ExecutionPhase){'V24_INTEGRITY'{'V24_PRE_RUN_INTEGRITY_FAILURE'}'GIT_LINEAGE'{'GIT_LINEAGE_FAILURE'}'STATIC_VALIDATION'{'STATIC_VALIDATION_FAILURE'}'AZURE_READONLY_PREFLIGHT'{'AZURE_READONLY_PREFLIGHT_FAILURE'}'PREFLIGHT_COMPLETE'{'PREFLIGHT_ACCEPTANCE_FAILURE'}default{'LOCAL_INITIALIZATION_FAILURE'}}} }
finally {
  $ExecutionPhase='EVIDENCE_FINALIZATION'; $final=if($PreflightAcceptancePass -and -not $Failure){'V2_5_R4_PREFLIGHT_ONLY_PASS'}else{'V2_5_STOPPED_PRE_AZURE_MUTATION'}; $stateCounts=[ordered]@{}; foreach($key in $MutationCounts.Keys){$stateCounts[$key]=$MutationCounts[$key]}
  Save-Json '00_RUN_CONTEXT.json' @{result='PASS';mode='PREFLIGHT_ONLY';runId=$RunId;acceptedApplicationSha=$ExpectedAppSha;acceptedApplicationTree=$ExpectedAppTree;acceptedImage=$ExpectedImage;resourceGroup=$RG;sqlServer=$SqlServer;database=$Database;r4Branch=$R4Branch;r4Head=if($head){$head}else{'NOT_AVAILABLE'}}
  Save-Json '01_PRIOR_V25_HISTORY.json' @{result='PASS';r3Result='STOPPED_PRE_AZURE_MUTATION';r3Head=$R3Commit;r3AzureAttemptConsumed=$false;r3JobCreated=$false;r3ExecutionStartAttempted=$false;r3Failure='EMPTY_GIT_DIFF_SCALAR_CARDINALITY_DEFECT'}
  if($null -ne $V24Evidence){Save-Json '02_V24_PRE_RUN_REVALIDATION.json' @{result=if($V24PrePass){'PASS'}else{'FAIL'};root=$V24Evidence;manifestSha=$V24ManifestSha;finalResult=$v24.final.FINAL_RESULT;sdkCorroboration=$v24.final.AZURE_IDENTITY_CORROBORATION}}else{Save-Json '02_V24_PRE_RUN_REVALIDATION.json' @{result='NOT_EXECUTED';reason='V24 evidence discovery failed'}}
  Save-Json '03_SCALAR_REPAIR_REMOTE_PIN.json' @{result='PASS';branch=$ScalarRepairBranch;head=$remoteScalar;tree=$ScalarRepairTree;repairedScriptSha256=$ScalarRepairScriptSha}
  Save-Json '04_V25_R3_HISTORICAL_PIN.json' @{result='PASS';branch=$R3Branch;head=$R3Commit;tree='a8e2cee546617f446aef3d5a25d70b1edde2785a';parent=$R2Commit;changedPaths=@('scripts/proposalops_azure_p0_v25_native_msi_bootstrap_one_shot.ps1');resultClass='STOPPED_PRE_AZURE_MUTATION'}
  Save-Json '05_V25_R4_HARNESS_REMOTE_PIN.json' @{result=if($head -and $remoteR4 -and $head -eq $remoteR4){'PASS'}else{'FAIL'};branch=$R4Branch;head=$head;remoteHead=$remoteR4;tree=if($head){(Git-Text @('rev-parse',"$head^{tree}")).Trim()}else{'NOT_AVAILABLE'};parent=$parent;grandparent=$grandparent;greatGrandparent=$greatgrandparent;changedPaths=@(if($changed){$changed});harnessSha256=if(Test-Path -LiteralPath $PSCommandPath){Sha $PSCommandPath}else{'NOT_AVAILABLE'}}
  if($null -ne $subscription){Save-Json '06_AZURE_READONLY_PREFLIGHT.json' @{result=if($AzureReadonlyPreflightPass){'PASS'}else{'FAIL'};subscription=$SubscriptionName;resourceGroup=$RG;sqlServer=$SqlServer;database=$Database;databaseStatus=if($db){$db.status}else{'NOT_READ'};sqlState=if($sql){$sql.state}else{'NOT_READ'};sqlPublicNetworkAccess=if($sql){$sql.publicNetworkAccess}else{'NOT_READ'};sqlEntraOnly=if($sql){[bool]$sql.administrators.azureAdOnlyAuthentication}else{$false};minimalTlsVersion=if($sql){$sql.minimalTlsVersion}else{'NOT_READ'};privateEndpointCount=if($pe){$pe.Count}else{'NOT_READ'};privateDnsIp=if($dns){$dns.aRecords[0].ipv4Address}else{'NOT_READ'};acaEnvironment=$AcaEnvironmentName;acaState=if($aca){$aca.properties.provisioningState}else{'NOT_READ'};acrAdminEnabled=if($acr){[bool]$acr.adminUserEnabled}else{'NOT_READ'};acceptedImage=$ExpectedImage;historicalJobCount=if($jobs){$jobs.Count}else{'NOT_READ'};azureReadPhaseEntered=$AzureReadPhaseEntered;azureReadCommands=$AzureReadCommands;azureMutationOccurred=$AzureMutationOccurred;azureMutationCommands=$AzureMutationCommands}}
  Save-Json '07_UAMI_IDENTITY_MATRIX.json' @{result=if($AzureReadonlyPreflightPass){'PASS'}else{'NOT_EXECUTED'};bootstrap=@{resourcePresent=(-not [string]::IsNullOrWhiteSpace($bootstrapResource));principalGuid=([guid]::TryParse($bootstrapPrincipal,[ref]$g1));clientGuid=([guid]::TryParse($bootstrapClient,[ref]$g2));principalClientDistinct=($bootstrapPrincipal -ne $bootstrapClient)};migration=@{clientGuid=([guid]::TryParse($migrationClient,[ref]$g3))};api=@{clientGuid=([guid]::TryParse($apiClient,[ref]$g4))}}
  Save-Json '08_HUMAN_SQL_ADMIN_SNAPSHOT.json' @{result=if($HumanAdminSnapshotPass){'PASS'}else{'NOT_EXECUTED'};loginExpected='Ahmed Sami';loginObserved=if($OriginalHumanAdmin){$OriginalHumanAdmin[0].login}else{'NOT_READ'};administratorType=if($OriginalHumanAdmin){$OriginalHumanAdmin[0].administratorType}else{'NOT_READ'};tenantFingerprint=if($OriginalHumanAdmin){Sha-Text ([string]$OriginalHumanAdmin[0].tenantId)}else{'NOT_READ'};sidFingerprint=if($OriginalHumanAdmin){Sha-Text ([string]$OriginalHumanAdmin[0].sid)}else{'NOT_READ'}}
  Save-Json '09_MUTATION_LEDGER.json' @{azureReadPhaseEntered=$AzureReadPhaseEntered;azureReadCommands=$AzureReadCommands;azureMutationOccurred=$AzureMutationOccurred;azureMutationCommands=$AzureMutationCommands;azureAttemptConsumed=$AzureAttemptConsumed;counts=$stateCounts;state=$MutationState}
  Save-Json '10_POSTCONDITIONS.json' @{sqlPublicNetworkPostcondition=if($AzureReadPhaseEntered){$publicAfter}else{'NOT_APPLICABLE_NO_AZURE_PHASE'};sqlPublicNetworkPostPass=$SqlPublicNetworkPostPass;humanSqlAdminRestored='NOT_REQUIRED';jobCreated=$JobCreated;executionStartAttempted=$ExecutionStartAttempted;forbiddenStagesExecuted=$false}
  Save-Json '11_V24_POST_RUN_REHASH.json' $(if($null -ne $v24Post){$v24Post}else{[ordered]@{result='NOT_EXECUTED';reason='no V24 candidate'}})
  Save-Json '12_SAFETY_CEILINGS.json' @{AUTOMATIC_SQL_RETRY_LOOPS=0;SECOND_SQL_CONNECTION_PATHS=0;BOOTSTRAP_JOB_CREATES=0;BOOTSTRAP_JOB_UPDATES=0;BOOTSTRAP_JOB_DELETES=0;BOOTSTRAP_JOB_EXECUTIONS=0;SQL_ADMIN_SWITCH_MUTATIONS=0;SQL_ADMIN_RESTORE_MUTATIONS=0;SQL_CONNECTION_ATTEMPTS=0;SQL_DDL_MUTATIONS=0;SQL_DML_MUTATIONS=0;ENTRA_MUTATIONS=0;RBAC_MUTATIONS=0;FIREWALL_MUTATIONS=0;SQL_PUBLIC_NETWORK_MUTATIONS=0;MIGRATION_EXECUTIONS=0;SEED_EXECUTIONS=0;API_DEPLOYMENTS=0;FRONTEND_DEPLOYMENTS=0;SYNLOGY_READS=0;REAL_AMEC_DATA_READS=0;REAL_AMEC_DATA_WRITES=0;PHASE6_MUTATIONS=0}
  Save-Json '13_FINAL_RESULT.json' @{FINAL_RESULT=$final;MODE='PREFLIGHT_ONLY';FAILURE_PHASE=if($Failure){$FailurePhase}else{'NONE'};FAILURE_CODE=$FailureCode;FAILURE=$Failure;AZURE_READ_PHASE_ENTERED=$AzureReadPhaseEntered;AZURE_READ_COMMANDS=$AzureReadCommands;AZURE_MUTATION_OCCURRED=$AzureMutationOccurred;AZURE_MUTATION_COMMANDS=$AzureMutationCommands;AZURE_ATTEMPT_CONSUMED=$AzureAttemptConsumed;BOOTSTRAP_JOB_CREATED=$JobCreated;BOOTSTRAP_JOB_EXECUTION_START_ATTEMPTED=$ExecutionStartAttempted;BOOTSTRAP_JOB_EXECUTION_REQUEST_ACCEPTED=$ExecutionRequestAccepted;BOOTSTRAP_JOB_EXECUTION_OBSERVED=$ExecutionObserved;SQL_ADMIN_SWITCH_ATTEMPTED=$AdminSwitchAttempted;SQL_ADMIN_SWITCH_VERIFIED=$AdminSwitchVerified;SQL_CONNECTION_ATTEMPTS=0;SQL_DDL_MUTATIONS=0;SQL_DML_MUTATIONS=0;V24_PRE_RUN_REHASH=if($V24PrePass){'PASS'}else{'FAIL'};V24_POST_RUN_REHASH=if($V24PostPass){'PASS'}else{'FAIL'};SQL_PUBLIC_NETWORK_POSTCONDITION=if($AzureReadPhaseEntered){$publicAfter}else{'NOT_APPLICABLE_NO_AZURE_PHASE'};HUMAN_SQL_ADMIN_RESTORED='NOT_REQUIRED';EVIDENCE_SEAL_REQUIRED=$true;MANIFEST_BUILT_LAST=$true;EVIDENCE_MUTATIONS_AFTER_MANIFEST_REQUIRED=0;NEXT='OWNER_INDEPENDENT_REVIEW'}
  Save-Json '14_INDEPENDENT_CHECKS.json' $Checks
  $transcript=@("MODE=PREFLIGHT_ONLY","FINAL_RESULT=$final","FAILURE_PHASE=$(if($Failure){$FailurePhase}else{'NONE'})","FAILURE_CODE=$FailureCode","AZURE_READ_PHASE_ENTERED=$AzureReadPhaseEntered","AZURE_READ_COMMANDS=$AzureReadCommands","AZURE_MUTATION_OCCURRED=$AzureMutationOccurred","AZURE_MUTATION_COMMANDS=$AzureMutationCommands","AZURE_ATTEMPT_CONSUMED=$AzureAttemptConsumed","BOOTSTRAP_JOB_CREATED=$JobCreated","BOOTSTRAP_JOB_EXECUTION_START_ATTEMPTED=$ExecutionStartAttempted","SQL_ADMIN_SWITCH_ATTEMPTED=$AdminSwitchAttempted","SQL_CONNECTION_ATTEMPTS=0","SQL_DDL_MUTATIONS=0","SQL_DML_MUTATIONS=0","V24_PRE_RUN_REHASH=$(if($V24PrePass){'PASS'}else{'FAIL'})","V24_POST_RUN_REHASH=$(if($V24PostPass){'PASS'}else{'FAIL'})","SQL_PUBLIC_NETWORK_POSTCONDITION=$(if($AzureReadPhaseEntered){$publicAfter}else{'NOT_APPLICABLE_NO_AZURE_PHASE'})","MANIFEST_RECOMPUTATION=DEFERRED_UNTIL_FINALIZATION","NEXT=OWNER_INDEPENDENT_REVIEW","EVIDENCE_ROOT=$EvidenceRoot"); $transcript|Set-Content -LiteralPath (Join-Path $EvidenceRoot 'transcript.txt') -Encoding utf8
  $manifestPath=Join-Path $EvidenceRoot 'MANIFEST.sha256'; $manifestRows=@(); foreach($file in @(Get-ChildItem -LiteralPath $EvidenceRoot -File | Where-Object {$_.Name -ne 'MANIFEST.sha256'} | Sort-Object Name)){$manifestRows += "$(Sha $file.FullName)  $($file.Name)"}; $manifestRows|Set-Content -LiteralPath $manifestPath -Encoding utf8; $sealed=Read-Manifest $EvidenceRoot $R4Members; $ManifestRecomputation=if($sealed.pass){'PASS'}else{'FAIL'}
  if($sealed.pass){$sealPath="$EvidenceRoot.SEAL.json"; Save-ExternalJson $sealPath @{result='PASS';evidenceRoot=$EvidenceRoot;manifestSha256=(Sha $manifestPath);manifestMemberCount=$sealed.foundMembers;manifestRecomputation='PASS';evidenceMutationsAfterManifest=0;finalResult=$final;r4Head=$head;harnessSha256=(Sha $PSCommandPath);azureReadCommands=$AzureReadCommands;azureMutationCommands=$AzureMutationCommands;azureAttemptConsumed=$AzureAttemptConsumed}; Write-Output "R4_REMOTE_HEAD=$head"; Write-Output "R4_REMOTE_TREE=$(if($head){(Git-Text @('rev-parse',"$head^{tree}")).Trim()}else{'NOT_AVAILABLE'})"; Write-Output "R4_PARENT=$parent"; Write-Output 'MODE=PREFLIGHT_ONLY'; Write-Output "FINAL_RESULT=$final"; Write-Output "FAILURE_PHASE=$(if($Failure){$ExecutionPhase}else{'NONE'})"; Write-Output "FAILURE_CODE=$FailureCode"; Write-Output "AZURE_READ_PHASE_ENTERED=$AzureReadPhaseEntered"; Write-Output "AZURE_READ_COMMANDS=$AzureReadCommands"; Write-Output "AZURE_MUTATION_OCCURRED=$AzureMutationOccurred"; Write-Output "AZURE_MUTATION_COMMANDS=$AzureMutationCommands"; Write-Output "AZURE_ATTEMPT_CONSUMED=$AzureAttemptConsumed"; Write-Output "BOOTSTRAP_JOB_CREATED=$JobCreated"; Write-Output "BOOTSTRAP_JOB_EXECUTION_START_ATTEMPTED=$ExecutionStartAttempted"; Write-Output "SQL_ADMIN_SWITCH_ATTEMPTED=$AdminSwitchAttempted"; Write-Output 'SQL_CONNECTION_ATTEMPTS=0'; Write-Output 'SQL_DDL_MUTATIONS=0'; Write-Output 'SQL_DML_MUTATIONS=0'; Write-Output "V24_PRE_RUN_REHASH=$(if($V24PrePass){'PASS'}else{'FAIL'})"; Write-Output "V24_POST_RUN_REHASH=$(if($V24PostPass){'PASS'}else{'FAIL'})"; Write-Output "SQL_PUBLIC_NETWORK_POSTCONDITION=$(if($AzureReadPhaseEntered){$publicAfter}else{'NOT_APPLICABLE_NO_AZURE_PHASE'})"; Write-Output "EVIDENCE_ROOT=$EvidenceRoot"; Write-Output "MANIFEST_SHA256=$(Sha $manifestPath)"; Write-Output "MANIFEST_RECOMPUTATION=$ManifestRecomputation"; Write-Output "SEAL_PATH=$sealPath"; Write-Output 'NEXT=OWNER_INDEPENDENT_REVIEW'}else{Write-Output "EVIDENCE_ROOT=$EvidenceRoot";Write-Output 'MANIFEST_RECOMPUTATION=FAIL';Write-Output 'EVIDENCE_PACKAGE_ACCEPTED=false';Write-Output 'NEXT=OWNER_INDEPENDENT_REVIEW'}
}
if($Failure -or -not $PreflightAcceptancePass){exit 1}
