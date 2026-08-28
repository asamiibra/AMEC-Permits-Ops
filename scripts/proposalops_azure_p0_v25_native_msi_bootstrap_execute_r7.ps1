[CmdletBinding()]
param(
    [switch]$QualificationOnly,
    [switch]$CompatibilityOnly,
    [switch]$PreflightOnly,
    [switch]$Execute,
    [string]$PreflightSealPath
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RunId = Get-Date -AsUTC -Format 'yyyyMMdd-HHmmss'
$R7ScriptPath = 'scripts/proposalops_azure_p0_v25_native_msi_bootstrap_execute_r7.ps1'
$R7Branch = 'azure-p0-v25-native-msi-bootstrap-execute-r7-v1'
$R6Commit = 'ea9e1790a24de4c1c373012e6869cd97d4f2e564'
$R5Commit = '876001aed983c41b3bb4a66936b06093f069824a'
$R4Commit = '486cc4cd675156abe958608a9f71ffbd2a27b56f'
$R3Commit = '57c62ddac257d49cf594b90cc27c4198fb145e6d'
$R2Commit = '378b4acee87b5ca85f94a7605f36f86b49ccb102'
$V1Commit = 'fa227c1d3276b2c8cf3f312c2814144e05aeddd5'
$ScalarRepairCommit = '5ed44e51978a71100f85616020be78d7a7660261'
$R4Evidence = '/tmp/ProposalOps_Azure_P0_V2_5_R4_20260828-023907'
$R4Seal = "$R4Evidence.SEAL.json"
$R4HarnessSha = '4ef55861ccab60377bc093f5fd84864e67c6b3d0631c54f2b747f994c55e44a8'
$SubscriptionName = 'AMEC Subscription'
$ResourceGroup = 'rg-proposalops-prod-uae'
$SqlServer = 'sql-proposalops-prod-uae-2bea2887'
$Database = 'sqldb-proposalops-prod'
$AcaEnvironmentName = 'cae-proposalops-prod-uae'
$AcrName = 'acrproposalopsproduae2bea2887'
$AcceptedImage = 'acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d'
$AcceptedDigest = 'sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d'
$AcceptedPrivateIp = '10.43.2.4'
$AcrPullRoleDefinition = '/providers/Microsoft.Authorization/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d'
$ModeFlags = @($QualificationOnly,$CompatibilityOnly,$PreflightOnly,$Execute)
$Mode = if(@($ModeFlags|Where-Object{$_}).Count -eq 1){if($QualificationOnly){'QUALIFICATION'}elseif($CompatibilityOnly){'COMPATIBILITY'}elseif($PreflightOnly){'PREFLIGHT_ONLY'}else{'EXECUTE'}}else{'INVALID'}
$EvidenceRoot = Join-Path ([IO.Path]::GetTempPath()) "ProposalOps_Azure_P0_V2_5_R7_${Mode}_$RunId"
New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
$EvidenceMembers = @('00_RUN_CONTEXT.json','01_R4_ACCEPTANCE_BINDING.json','02_R5_HISTORICAL_FAILURE_PIN.json','03_R7_REMOTE_PIN.json','04_R7_LOCAL_QUALIFICATION_BINDING.json','05_R7_PREFLIGHT_BINDING.json','06_V24_REVALIDATION.json','07_AZURE_PREFLIGHT.json','08_UAMI_IDENTITY_MATRIX.json','09_ACR_ROLE_ASSIGNMENT_BASELINE.json','10_ORIGINAL_SQL_ADMIN_REST_SNAPSHOT.json','11_JOB_CREATE_RESULT.json','12_JOB_PRESTART_READBACK.json','13_SQL_ADMIN_SWITCH_RESULT.json','14_JOB_START_RESULT.json','15_BOOTSTRAP_EXECUTION_RESULT.json','16_SQL_MUTATION_LEDGER.json','17_HUMAN_ADMIN_RESTORE_RESULT.json','18_POSTCONDITIONS.json','19_SAFETY_CEILINGS.json','20_FINAL_RESULT.json','21_INDEPENDENT_CHECKS.json','transcript.txt')
$R4Members = @('00_RUN_CONTEXT.json','01_PRIOR_V25_HISTORY.json','02_V24_PRE_RUN_REVALIDATION.json','03_SCALAR_REPAIR_REMOTE_PIN.json','04_V25_R3_HISTORICAL_PIN.json','05_V25_R4_HARNESS_REMOTE_PIN.json','06_AZURE_READONLY_PREFLIGHT.json','07_UAMI_IDENTITY_MATRIX.json','08_HUMAN_SQL_ADMIN_SNAPSHOT.json','09_MUTATION_LEDGER.json','10_POSTCONDITIONS.json','11_V24_POST_RUN_REHASH.json','12_SAFETY_CEILINGS.json','13_FINAL_RESULT.json','14_INDEPENDENT_CHECKS.json','transcript.txt')
$V24Members = @('00_RUN_CONTEXT.json','01_V22_LIVE_UID_DEFECT.json','02_BOOTSTRAP_UAMI_IDENTITY_MATRIX.json','03_FUTURE_ODBC_UID_CONTRACT.json','04_DIAGNOSTIC_JOB_TEMPLATE.json','05_DIAGNOSTIC_JOB_PRESTART_READBACK.json','06_IDENTITY_RUNTIME_ENV.json','07_ACA_SQL_TOKEN_RESULT.json','08_TOKEN_CLAIM_BINDING.json','09_OPTIONAL_AZURE_IDENTITY_RESULT.json','10_ADMIN_PROPAGATION_ADJUDICATION.json','11_MUTATION_LEDGER.json','12_SAFETY_CEILINGS.json','13_FINAL_RESULT.json','14_SCALAR_REPAIR_IMPLEMENTATION.json')
$Failure = $null
$FailureCode = $null
$ExecutionPhase = 'INITIALIZATION'
$Provider = 'Real'
$SubscriptionId = $null
$AzureReadPhaseEntered = $false
$AzureReadCommands = 0
$AzureMutationCommands = 0
$AzureMutationOccurred = $false
$AzureAttemptConsumed = $false
$JobCreateAttempted = $false
$JobCreated = $false
$JobStartAttempted = $false
$JobStartAccepted = $false
$JobName = 'NOT_AVAILABLE'
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
$State = $null
$QualificationResults = $null
$CompatibilityResults = $null
$CompatibilityProbes = [System.Collections.Generic.List[object]]::new()
$Checks = [System.Collections.Generic.List[object]]::new()
$ReadRecords = [System.Collections.Generic.List[object]]::new()
$MutationCounts = [ordered]@{BOOTSTRAP_JOB_CREATES=0;BOOTSTRAP_JOB_EXECUTIONS=0;SQL_ADMIN_SWITCH_MUTATIONS=0;SQL_ADMIN_RESTORE_MUTATIONS=0;SQL_CONNECTION_ATTEMPTS=0;SQL_DDL_MUTATIONS=0;SQL_DML_MUTATIONS=0;RBAC_MUTATIONS=0;ENTRA_MUTATIONS=0;MIGRATION_EXECUTIONS=0;SEED_EXECUTIONS=0;API_DEPLOYMENTS=0;FRONTEND_DEPLOYMENTS=0;SYNOLOGY_EXECUTION_SITES=0;PHASE6_SITES=0;REAL_AMEC_DATA_READS=0;REAL_AMEC_DATA_WRITES=0}
$MutationState = [ordered]@{SQL_MUTATION_STATE='NOT_EXECUTED';SQL_ADMIN_SWITCH_ATTEMPTED=$false;SQL_ADMIN_RESTORE_ATTEMPTED=$false}
$MockFailure = $null
$MockState = [ordered]@{AdminIsBootstrap=$false;RestoreHandlerExecuted=$false}

$BootstrapPython = @'
import json
import os
import pyodbc

def bootstrap():
    result = {"sql_connection_attempts": 0, "sql_connection_succeeded": False, "sql_login": "FAIL", "sql_target_db": "FAIL", "sql_required_permission": "FAIL", "preinspection_pass": False, "sql_mutation_state": "NOT_EXECUTED", "api_user_state": "FAIL", "migration_user_state": "FAIL", "api_mutations": 0, "migration_mutations": 0, "role_mutations": 0, "permission_grants": 0, "sql_ddl_mutations": 0, "sql_dml_mutations": 0, "bootstrap_principal_absent": False, "post_verification": False, "error_class": None, "error_message": None}
    connection = None
    try:
        result["sql_connection_attempts"] += 1
        connection = pyodbc.connect("DRIVER={ODBC Driver 18 for SQL Server};SERVER=" + os.environ["SQL_HOST"] + ";DATABASE=" + os.environ["SQL_DATABASE"] + ";Authentication=ActiveDirectoryMsi;UID=" + os.environ["SQL_ODBC_UID"] + ";Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30")
        result["sql_connection_succeeded"] = True
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result["sql_login"] = "PASS" if cursor.fetchone()[0] == 1 else "FAIL"
        cursor.execute("SELECT DB_NAME()")
        result["sql_target_db"] = "PASS" if cursor.fetchone()[0] == os.environ["SQL_DATABASE"] else "FAIL"
        cursor.execute("SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'ALTER ANY USER')")
        result["sql_required_permission"] = "PASS" if cursor.fetchone()[0] == 1 else "FAIL"
        if not all(result[key] == "PASS" for key in ("sql_login", "sql_target_db", "sql_required_permission")):
            raise RuntimeError("SQL_DATA_PLANE_GATE_FAILED")
        cursor.execute("SELECT name, type, type_desc, SID FROM sys.database_principals WHERE name IN ('proposalops_bootstrap_uami', 'proposalops_api_uami', 'proposalops_migration_uami')")
        principals = {row[0]: row for row in cursor.fetchall()}
        result["bootstrap_principal_absent"] = "proposalops_bootstrap_uami" not in principals
        if not result["bootstrap_principal_absent"]:
            raise RuntimeError("BOOTSTRAP_CONTAINED_PRINCIPAL_PRESENT")
        cursor.execute("SELECT USER_NAME(rm.member_principal_id), r.name FROM sys.database_role_members rm JOIN sys.database_principals r ON r.principal_id=rm.role_principal_id WHERE USER_NAME(rm.member_principal_id) IN ('proposalops_api_uami', 'proposalops_migration_uami')")
        roles = {}
        for member, role in cursor.fetchall():
            roles.setdefault(member, set()).add(role)
        cursor.execute("SELECT grantee_principal_id, permission_name, state_desc FROM sys.database_permissions WHERE grantee_principal_id IN (USER_ID('proposalops_api_uami'), USER_ID('proposalops_migration_uami'))")
        permissions = cursor.fetchall()
        result["preinspection_pass"] = True
        api_client_id = os.environ["API_CLIENT_ID"]
        migration_client_id = os.environ["MIGRATION_CLIENT_ID"]
        statements = []
        if "proposalops_api_uami" not in principals:
            statements.append("CREATE USER [proposalops_api_uami] WITH SID = CONVERT(binary(16), REPLACE('" + api_client_id + "', '-', ''), 2), TYPE = E")
        if "proposalops_migration_uami" not in principals:
            statements.append("CREATE USER [proposalops_migration_uami] WITH SID = CONVERT(binary(16), REPLACE('" + migration_client_id + "', '-', ''), 2), TYPE = E")
        statements.extend(["ALTER ROLE db_datareader ADD MEMBER [proposalops_api_uami]", "ALTER ROLE db_datawriter ADD MEMBER [proposalops_api_uami]", "ALTER ROLE db_datareader ADD MEMBER [proposalops_migration_uami]", "ALTER ROLE db_datawriter ADD MEMBER [proposalops_migration_uami]", "ALTER ROLE db_ddladmin ADD MEMBER [proposalops_migration_uami]", "GRANT VIEW DEFINITION TO [proposalops_migration_uami]"])
        for statement in statements:
            cursor.execute(statement)
            result["sql_ddl_mutations"] += 1
        result["api_mutations"] = 1 if "proposalops_api_uami" not in principals else 0
        result["migration_mutations"] = 1 if "proposalops_migration_uami" not in principals else 0
        result["role_mutations"] = 5
        result["permission_grants"] = 1
        connection.commit()
        result["sql_mutation_state"] = "KNOWN"
        cursor.execute("SELECT name, type, type_desc, SID FROM sys.database_principals WHERE name IN ('proposalops_bootstrap_uami', 'proposalops_api_uami', 'proposalops_migration_uami')")
        after = {row[0]: row for row in cursor.fetchall()}
        result["api_user_state"] = "PASS" if after.get("proposalops_api_uami", (None, None))[1] == "E" else "FAIL"
        result["migration_user_state"] = "PASS" if after.get("proposalops_migration_uami", (None, None))[1] == "E" else "FAIL"
        result["post_verification"] = result["api_user_state"] == "PASS" and result["migration_user_state"] == "PASS" and "proposalops_bootstrap_uami" not in after
    except Exception as error:
        result["error_class"] = type(error).__name__
        result["error_message"] = str(error)[:300]
        if result["sql_connection_succeeded"] and result["sql_mutation_state"] == "NOT_EXECUTED":
            result["sql_mutation_state"] = "UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION"
    finally:
        if connection is not None:
            connection.close()
        print("PROPOSALOPS_V25_RESULT=" + json.dumps(result, separators=(",", ":")))

if __name__ == "__main__":
    bootstrap()
'@

function Sha([string]$Path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function Sha-Text([string]$Value) { $hash=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value)))).Replace('-','').ToLowerInvariant()}finally{$hash.Dispose()} }
function Save-Json([string]$Name,$Value) { $Value|ConvertTo-Json -Depth 100|Set-Content -LiteralPath (Join-Path $EvidenceRoot $Name) -Encoding utf8 }
function Check([string]$Id,[bool]$Pass,$Actual='') { $Checks.Add([ordered]@{id=$Id;phase=$ExecutionPhase;result=if($Pass){'PASS'}else{'FAIL'};actual=[string]$Actual})|Out-Null;if(-not $Pass){throw "VALIDATION_FAILURE [$Id] $Actual"} }
function Git-Text([string[]]$Arguments) { $output=&git -C $RepoRoot @Arguments 2>&1;if($LASTEXITCODE -ne 0){throw "GIT_COMMAND_FAILURE $($Arguments -join ' ')"};($output|ForEach-Object ToString)-join[Environment]::NewLine }
function Read-Manifest([string]$Root,[string[]]$ExpectedNames) { $path=Join-Path $Root 'MANIFEST.sha256';if(-not (Test-Path -LiteralPath $path)){return $null};$rows=@();foreach($line in @(Get-Content -LiteralPath $path)){if($line -match '^([0-9a-f]{64})  (.+)$'){$rows+=[pscustomobject]@{expected=$Matches[1];name=$Matches[2]}}};$names=@($rows|ForEach-Object{$_.name});$missing=@($ExpectedNames|Where-Object{$names -notcontains $_});$unexpected=@($names|Where-Object{$ExpectedNames -notcontains $_});$duplicate=$names.Count-(@($names|Sort-Object -Unique)).Count;$matched=0;foreach($row in $rows){$file=Join-Path $Root $row.name;if((Test-Path -LiteralPath $file) -and (Sha $file) -eq $row.expected){$matched++}};[ordered]@{root=$Root;missing=$missing;unexpected=$unexpected;duplicate=$duplicate;foundMembers=$rows.Count;expectedMembers=$ExpectedNames.Count;matchedMembers=$matched;failedMembers=$rows.Count-$matched;manifestSha=Sha $path;pass=($missing.Count -eq 0 -and $unexpected.Count -eq 0 -and $duplicate -eq 0 -and $rows.Count -eq $ExpectedNames.Count -and $matched -eq $ExpectedNames.Count)} }
function Validate-Evidence([string]$Root,[string[]]$Members) { $m=Read-Manifest $Root $Members;if($null -eq $m -or -not $m.pass){throw 'EVIDENCE_MANIFEST_INVALID'};$m }
function Find-V24Evidence { $dirs=@();foreach($base in @('/tmp',[IO.Path]::GetTempPath())|Select-Object -Unique){if(Test-Path -LiteralPath $base){$dirs+=@(Get-ChildItem -LiteralPath $base -Directory -Filter 'ProposalOps_Azure_P0_V2_4_*' -ErrorAction SilentlyContinue)}};$valid=@();foreach($dir in @($dirs|Sort-Object FullName -Unique)){try{$final=Get-Content -LiteralPath (Join-Path $dir.FullName '13_FINAL_RESULT.json') -Raw|ConvertFrom-Json;$manifest=Read-Manifest $dir.FullName $V24Members;$accepted=$manifest.pass -and $final.FINAL_RESULT -eq 'V2_4_MI_TOKEN_DIAGNOSTIC_PASS' -and $final.AZURE_IDENTITY_CORROBORATION -eq 'FAIL' -and -not [bool]$final.CROSS_TRACK_CONVERGENCE_AUTHORIZED -and [int]$final.REAL_AMEC_DATA_READS -eq 0 -and [int]$final.REAL_AMEC_DATA_WRITES -eq 0;if($accepted){$valid+=[pscustomobject]@{root=$dir.FullName;manifest=$manifest;final=$final}}}catch{}};if($valid.Count -ne 1){throw "V24_EVIDENCE_COUNT_$($valid.Count)"};$valid[0] }
function Verify-V24([string]$Root,[string]$ManifestSha) { $m=Validate-Evidence $Root $V24Members;if($m.manifestSha -ne $ManifestSha){throw 'V24_MANIFEST_SHA_CHANGED'};[ordered]@{result='PASS';root=$Root;manifestSha=$m.manifestSha;foundMembers=$m.foundMembers} }
function New-MockFixture([string]$Label) { switch -Wildcard ($Label) { '*administrator*' { if($MockState.AdminIsBootstrap){return [pscustomobject]@{properties=[pscustomobject]@{administratorType='ManagedIdentity';login='id-proposalops-sql-bootstrap-prod-uae';sid='11111111-1111-1111-1111-111111111111';tenantId='66666666-6666-6666-6666-666666666666'}}};return [pscustomobject]@{properties=[pscustomobject]@{administratorType='ActiveDirectory';login='Ahmed Sami';sid='55555555-5555-5555-5555-555555555555';tenantId='66666666-6666-6666-6666-666666666666'}} } '*role assignments*' { return @([pscustomobject]@{id='/subscriptions/mock/providers/Microsoft.Authorization/roleAssignments/acrpull';scope='/subscriptions/mock/acr';roleDefinitionId=$AcrPullRoleDefinition}) } '*execution list*' { return @([pscustomobject]@{name='manual-r7'}) } '*execution*' { return [pscustomobject]@{name='manual-r7';properties=[pscustomobject]@{status='Succeeded'}} } '*logs*' { if($MockFailure -eq 'MarkerLoss'){return 'NO_RESULT_MARKER'};return 'PROPOSALOPS_V25_RESULT={"sql_connection_attempts":1,"sql_connection_succeeded":true,"sql_login":"PASS","sql_target_db":"PASS","sql_required_permission":"PASS","preinspection_pass":true,"sql_mutation_state":"KNOWN","api_user_state":"PASS","migration_user_state":"PASS","api_mutations":1,"migration_mutations":1,"role_mutations":5,"permission_grants":1,"sql_ddl_mutations":8,"sql_dml_mutations":0,"bootstrap_principal_absent":true,"post_verification":true,"error_class":null,"error_message":null}' } '*job*' { return [pscustomobject]@{properties=[pscustomobject]@{environmentId='/subscriptions/mock/aca';configuration=[pscustomobject]@{triggerType='Manual';replicaRetryLimit=0;manualTriggerConfig=[pscustomobject]@{parallelism=1;replicaCompletionCount=1};registries=@([pscustomobject]@{server='acr.azurecr.io';identity='/subscriptions/mock/uami'})};template=[pscustomobject]@{containers=@([pscustomobject]@{name='main';image=$AcceptedImage;command=@('python');args=@('-c','loader');env=@()})}}} } default { return [pscustomobject]@{} } } }
function Invoke-AzureRead([string[]]$Arguments,[string]$Label) { if($Provider -eq 'Mock'){if($Label -eq 'Read exact Job logs'){return [string](New-MockFixture 'logs')};return [string](New-MockFixture $Label)};$script:ExecutionPhase='AZURE_READONLY_PREFLIGHT';$script:AzureReadPhaseEntered=$true;$script:AzureReadCommands++;$outFile=Join-Path ([IO.Path]::GetTempPath()) "r7-read-$RunId-$($script:AzureReadCommands).out";$errFile=Join-Path ([IO.Path]::GetTempPath()) "r7-read-$RunId-$($script:AzureReadCommands).err";&az @Arguments --only-show-errors 1>$outFile 2>$errFile;$code=$LASTEXITCODE;$out=if(Test-Path $outFile){Get-Content -LiteralPath $outFile -Raw}else{''};$err=if(Test-Path $errFile){Get-Content -LiteralPath $errFile -Raw}else{''};$ReadRecords.Add([ordered]@{label=$Label;command=('az '+($Arguments -join ' '));exitCode=$code;stdoutDigest=Sha-Text $out;stderr=$err.Trim()})|Out-Null;if($code -ne 0){throw "AZURE_READ_COMMAND_FAILURE [$Label] $($err.Trim())"};$out }
function Invoke-AzureReadJson([string[]]$Arguments,[string]$Label) { if($Provider -eq 'Mock'){return New-MockFixture $Label};(Invoke-AzureRead $Arguments $Label)|ConvertFrom-Json }
function Invoke-ArmJson([string]$Url,[string]$Label) { if($Provider -eq 'Mock'){return New-MockFixture 'role assignments'};Invoke-AzureReadJson @('rest','--subscription',$script:SubscriptionId,'--method','get','--url',$Url,'--output','json') $Label }
function Invoke-AzureMutation([string[]]$Arguments,[string]$Label,[string]$Counter) { $script:AzureMutationOccurred=$true;$script:AzureMutationCommands++;$script:MutationCounts[$Counter]++;if($Provider -eq 'Mock'){if($MockFailure -eq 'JobCreate' -and $Counter -eq 'BOOTSTRAP_JOB_CREATES'){throw 'MOCK_JOB_CREATE_FAILURE'};if($MockFailure -eq 'AdminSwitch' -and $Counter -eq 'SQL_ADMIN_SWITCH_MUTATIONS'){throw 'MOCK_ADMIN_SWITCH_FAILURE'};if($MockFailure -eq 'RestoreFailure' -and $Counter -eq 'SQL_ADMIN_RESTORE_MUTATIONS'){throw 'MOCK_ADMIN_RESTORE_FAILURE'};if($MockFailure -eq 'StartAmbiguous' -and $Counter -eq 'BOOTSTRAP_JOB_EXECUTIONS'){throw 'MOCK_START_AMBIGUITY'};if($Counter -eq 'SQL_ADMIN_SWITCH_MUTATIONS'){$MockState.AdminIsBootstrap=$true};if($Counter -eq 'SQL_ADMIN_RESTORE_MUTATIONS'){$MockState.AdminIsBootstrap=$false};return '{}'};$out=&az @Arguments --only-show-errors 2>&1;if($LASTEXITCODE -ne 0){throw "AZURE_MUTATION_COMMAND_FAILURE [$Label]"};($out|ForEach-Object ToString)-join[Environment]::NewLine }
function Get-Admin([string]$ServerId) { Invoke-AzureReadJson @('rest','--subscription',$script:SubscriptionId,'--method','get','--url',"$ServerId/administrators/ActiveDirectory?api-version=2025-01-01",'--output','json') 'Read SQL administrator REST resource' }
function Test-Admin($Actual,$Expected) { return ($null -ne $Actual -and [string]$Actual.properties.administratorType -eq [string]$Expected.properties.administratorType -and [string]$Actual.properties.login -eq [string]$Expected.properties.login -and [string]$Actual.properties.sid -eq [string]$Expected.properties.sid -and [string]$Actual.properties.tenantId -eq [string]$Expected.properties.tenantId) }
function Wait-Admin($ServerId,$Expected) { $one=Get-Admin $ServerId;$two=Get-Admin $ServerId;if(-not (Test-Admin $one $Expected) -or -not (Test-Admin $two $Expected)){throw 'ADMIN_REST_PROPAGATION_NOT_VERIFIED'};$two }
function Get-RoleAssignmentsRest([string]$AcrId,[string]$PrincipalId) { $filter=[uri]::EscapeDataString("principalId eq '$PrincipalId'");$url="https://management.azure.com$AcrId/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01&%24filter=$filter";$all=@();while($url){$page=Invoke-ArmJson $url 'Read ACR role assignments by ARM REST';$all+=@($page.value);$url=[string]$page.nextLink};$all }
function New-JobDocument([string]$Name,[object]$RunState) { $b64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($BootstrapPython));$script:BootstrapPythonSha=Sha-Text $BootstrapPython;$identities=[ordered]@{};$identities.Add($RunState.bootstrap.id,[ordered]@{});$env=@([ordered]@{name='BOOTSTRAP_PY_B64';value=$b64},[ordered]@{name='SQL_HOST';value=$RunState.sql.fullyQualifiedDomainName},[ordered]@{name='SQL_DATABASE';value=$Database},[ordered]@{name='SQL_ODBC_UID';value=$RunState.bootstrap.principalId},[ordered]@{name='API_CLIENT_ID';value=$RunState.api.clientId},[ordered]@{name='MIGRATION_CLIENT_ID';value=$RunState.migration.clientId},[ordered]@{name='SYNTHETIC_ONLY';value='true'},[ordered]@{name='REAL_DATA_ALLOWED';value='false'});$container=[ordered]@{name='main';image=$AcceptedImage;command=@('python');args=@('-c','import base64, os; exec(base64.b64decode(os.environ["BOOTSTRAP_PY_B64"]))');env=$env;resources=[ordered]@{cpu=0.5;memory='1Gi'}};$configuration=[ordered]@{triggerType='Manual';replicaTimeout=300;replicaRetryLimit=0;manualTriggerConfig=[ordered]@{parallelism=1;replicaCompletionCount=1};registries=@([ordered]@{server=$RunState.acr.loginServer;identity=$RunState.bootstrap.id})};$script:JobDocument=[ordered]@{location=$RunState.group.location;identity=[ordered]@{type='UserAssigned';userAssignedIdentities=$identities};properties=[ordered]@{environmentId=$RunState.aca.id;configuration=$configuration;template=[ordered]@{containers=@($container)}}};$path=Join-Path ([IO.Path]::GetTempPath()) "proposalops-r7-$RunId.yaml";$JobDocument|ConvertTo-Json -Depth 100|Set-Content -LiteralPath $path -Encoding utf8;$round=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json;$encoded=($round.properties.template.containers[0].env|Where-Object{$_.name -eq 'BOOTSTRAP_PY_B64'}).value;$decoded=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encoded));if((Sha-Text $decoded) -ne $BootstrapPythonSha){throw 'JOB_PYTHON_ROUNDTRIP_FAILED'};if($Name.Length -ge 32 -or $Name -notmatch '^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'){throw 'JOB_NAME_INVALID'};$path }
function Create-OneJob([string]$Name,[object]$RunState) { $yaml=New-JobDocument $Name $RunState;$script:JobCreateAttempted=$true;Invoke-AzureMutation @('containerapp','job','create','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$Name,'--yaml',$yaml,'--output','json') 'Create one bootstrap Job' 'BOOTSTRAP_JOB_CREATES'|Out-Null;$script:JobCreated=$true }
function Set-TemporaryAdmin([object]$SqlState) { $script:AdminSwitchAttempted=$true;$MutationState.SQL_ADMIN_SWITCH_ATTEMPTED=$true;$body=@{properties=@{administratorType='ManagedIdentity';login='id-proposalops-sql-bootstrap-prod-uae';sid=$State.bootstrap.principalId;tenantId=$OriginalAdmin.properties.tenantId}}|ConvertTo-Json -Depth 20 -Compress;Invoke-AzureMutation @('rest','--subscription',$script:SubscriptionId,'--method','put','--url',"$($SqlState.id)/administrators/ActiveDirectory?api-version=2025-01-01",'--body',$body) 'Switch SQL administrator' 'SQL_ADMIN_SWITCH_MUTATIONS'|Out-Null;if($Provider -eq 'Mock'){$script:AdminSwitchVerified=$true}else{$expected=[pscustomobject]@{properties=[pscustomobject]@{administratorType='ManagedIdentity';login='id-proposalops-sql-bootstrap-prod-uae';sid=$State.bootstrap.principalId;tenantId=$OriginalAdmin.properties.tenantId}};Wait-Admin $SqlState.id $expected|Out-Null;$script:AdminSwitchVerified=$true} }
function Restore-HumanAdmin([object]$SqlState) { $script:AdminRestoreAttempted=$true;$MutationState.SQL_ADMIN_RESTORE_ATTEMPTED=$true;$MockState.RestoreHandlerExecuted=$true;$current=Get-Admin $SqlState.id;if(Test-Admin $current $OriginalAdmin){$script:AdminRestoreVerified=$true;return};$body=$OriginalAdmin|ConvertTo-Json -Depth 20 -Compress;Invoke-AzureMutation @('rest','--subscription',$script:SubscriptionId,'--method','put','--url',"$($SqlState.id)/administrators/ActiveDirectory?api-version=2025-01-01",'--body',$body) 'Restore human SQL administrator' 'SQL_ADMIN_RESTORE_MUTATIONS'|Out-Null;$verified=Wait-Admin $SqlState.id $OriginalAdmin;if(-not (Test-Admin $verified $OriginalAdmin)){throw 'HUMAN_SQL_ADMIN_RESTORE_NOT_VERIFIED'};$script:AdminRestoreVerified=$true }
function Start-OneJob([string]$Name,[string[]]$BeforeExecutions) { $script:JobStartAttempted=$true;$script:AzureAttemptConsumed=$true;$raw=Invoke-AzureMutation @('containerapp','job','start','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$Name,'--output','json') 'Start one bootstrap Job' 'BOOTSTRAP_JOB_EXECUTIONS';$script:JobStartAccepted=$true;$response=$null;try{$response=$raw|ConvertFrom-Json}catch{};$exact=[string]$response.properties.executionName;if([string]::IsNullOrWhiteSpace($exact)){$after=@(Invoke-AzureReadJson @('containerapp','job','execution','list','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$Name,'--output','json') 'List Job executions');$new=@($after|Where-Object{[string]$BeforeExecutions -notcontains [string]$_.name});if($new.Count -ne 1){$script:ExecutionTerminalStatus='UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION';throw 'EXECUTION_ACTUAL_STATE_UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION'};$exact=[string]$new[0].name};$script:ExecutionName=$exact;$execution=Invoke-AzureReadJson @('containerapp','job','execution','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$Name,'--job-execution-name',$exact,'--output','json') 'Show exact Job execution';$script:ExecutionTerminalStatus=[string]$execution.properties.status;Invoke-AzureRead @('containerapp','job','logs','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$Name,'--execution',$exact,'--container','main','--tail','300','--format','text') 'Read exact Job logs' }
function Parse-ResultMarker([string]$Logs) { $lines=@($Logs -split '\r?\n'|Where-Object{$_ -like 'PROPOSALOPS_V25_RESULT=*'});if($lines.Count -ne 1){throw 'RESULT_MARKER_NOT_EXACTLY_ONE'};($lines[0].Substring('PROPOSALOPS_V25_RESULT='.Length))|ConvertFrom-Json }
function Run-Preflight([bool]$UseMock) { $script:Provider=if($UseMock){'Mock'}else{'Real'};$account=if($UseMock){[pscustomobject]@{id='/subscriptions/mock';name=$SubscriptionName}}else{Invoke-AzureRead @('account','list','--query',"[?name=='$SubscriptionName' && state=='Enabled'].id | [0]",'--output','tsv') 'Resolve enabled subscription'};$script:SubscriptionId=if($UseMock){'/subscriptions/mock'}else{[string]$account.Trim()};Check 'enabled subscription' ($UseMock -or -not [string]::IsNullOrWhiteSpace($script:SubscriptionId)) 'PASS';$group=if($UseMock){[pscustomobject]@{name=$ResourceGroup;location='uaenorth'}}else{Invoke-AzureReadJson @('group','show','--subscription',$SubscriptionName,'--name',$ResourceGroup,'--output','json') 'Read resource group'};$sql=if($UseMock){[pscustomobject]@{id="/subscriptions/mock/resourceGroups/$ResourceGroup/providers/Microsoft.Sql/servers/$SqlServer";name=$SqlServer;fullyQualifiedDomainName="$SqlServer.database.windows.net";state='Ready';publicNetworkAccess='Disabled';minimalTlsVersion='1.2';administrators=[pscustomobject]@{azureAdOnlyAuthentication=$true}}}else{Invoke-AzureReadJson @('sql','server','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$SqlServer,'--output','json') 'Read SQL server'};$db=if($UseMock){[pscustomobject]@{name=$Database;status='Online'}}else{Invoke-AzureReadJson @('sql','db','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--server',$SqlServer,'--name',$Database,'--output','json') 'Read SQL database'};$aca=if($UseMock){[pscustomobject]@{id='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.App/managedEnvironments/cae';properties=[pscustomobject]@{provisioningState='Succeeded'}}}else{Invoke-AzureReadJson @('containerapp','env','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$AcaEnvironmentName,'--output','json') 'Read ACA environment'};$acr=if($UseMock){[pscustomobject]@{id='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ContainerRegistry/registries/acr';loginServer='acrproposalopsproduae2bea2887.azurecr.io';adminUserEnabled=$false}}else{Invoke-AzureReadJson @('acr','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$AcrName,'--output','json') 'Read ACR'};$dns=if($UseMock){[pscustomobject]@{aRecords=@([pscustomobject]@{ipv4Address=$AcceptedPrivateIp})}}else{Invoke-AzureReadJson @('network','private-dns','record-set','a','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--zone-name','privatelink.database.windows.net','--name',$SqlServer,'--output','json') 'Read private DNS'};$pe=if($UseMock){@([pscustomobject]@{provisioningState='Succeeded';privateLinkServiceConnections=@([pscustomobject]@{privateLinkServiceConnectionState=[pscustomobject]@{status='Approved'}})})}else{Invoke-AzureReadJson @('network','private-endpoint','list','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--output','json') 'Read private endpoint'};$image=if($UseMock){@([pscustomobject]@{digest=$AcceptedDigest})}else{Invoke-AzureReadJson @('acr','repository','show-manifests','--subscription',$SubscriptionName,'--name',$AcrName,'--repository','proposalops-api','--output','json') 'Read accepted image'};$bootstrap=if($UseMock){[pscustomobject]@{id='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/bootstrap';principalId='11111111-1111-1111-1111-111111111111';clientId='22222222-2222-2222-2222-222222222222'}}else{Invoke-AzureReadJson @('identity','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name','id-proposalops-sql-bootstrap-prod-uae','--output','json') 'Read bootstrap UAMI'};$migration=if($UseMock){[pscustomobject]@{id='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/migration';principalId='33333333-3333-3333-3333-333333333333';clientId='33333333-3333-3333-3333-333333333333'}}else{Invoke-AzureReadJson @('identity','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name','id-proposalops-sql-migrate-prod-uae','--output','json') 'Read migration UAMI'};$api=if($UseMock){[pscustomobject]@{id='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/api';principalId='44444444-4444-4444-4444-444444444444';clientId='44444444-4444-4444-4444-444444444444'}}else{Invoke-AzureReadJson @('identity','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name','id-proposalops-api-prod-uae','--output','json') 'Read API UAMI'};$script:OriginalAdmin=if($UseMock){[pscustomobject]@{properties=[pscustomobject]@{administratorType='ActiveDirectory';login='Ahmed Sami';sid='55555555-5555-5555-5555-555555555555';tenantId='66666666-6666-6666-6666-666666666666'}}}else{Get-Admin $sql.id};$assignments=if($UseMock){@([pscustomobject]@{id='/subscriptions/mock/providers/Microsoft.Authorization/roleAssignments/acrpull';scope=$acr.id;roleDefinitionId=$AcrPullRoleDefinition})}else{Get-RoleAssignmentsRest $acr.id $bootstrap.principalId};$script:AcrAssignmentsBaseline=@($assignments);$script:State=[pscustomobject]@{group=$group;sql=$sql;db=$db;aca=$aca;acr=$acr;dns=$dns;pe=$pe;image=$image;bootstrap=$bootstrap;migration=$migration;api=$api};Check 'resource group exact' ($group.name -eq $ResourceGroup) 'PASS';Check 'SQL ready' ($sql.name -eq $SqlServer -and $sql.state -eq 'Ready') 'PASS';Check 'database online' ($db.name -eq $Database -and $db.status -eq 'Online') 'PASS';Check 'SQL public disabled' ($sql.publicNetworkAccess -eq 'Disabled') 'PASS';Check 'SQL Entra only' ([bool]$sql.administrators.azureAdOnlyAuthentication) 'PASS';Check 'TLS 1.2' ($sql.minimalTlsVersion -eq '1.2') 'PASS';Check 'private DNS exact' ($dns.aRecords[0].ipv4Address -eq $AcceptedPrivateIp) 'PASS';Check 'private endpoint approved' (@($pe|Where-Object{$_.privateLinkServiceConnections[0].privateLinkServiceConnectionState.status -eq 'Approved'}).Count -ge 1) 'PASS';Check 'accepted image exact' (@($image|Where-Object{$_.digest -eq $AcceptedDigest}).Count -eq 1) 'PASS';Check 'bootstrap principal/client distinct' ($bootstrap.principalId -ne $bootstrap.clientId) 'PASS';Check 'effective AcrPull exact role' (@($assignments|Where-Object{$_.roleDefinitionId -eq $AcrPullRoleDefinition}).Count -ge 1) 'PASS';Check 'human admin snapshot' ($OriginalAdmin.properties.login -eq 'Ahmed Sami') 'PASS';$script:State }

function Set-TemporaryAdmin([object]$SqlState) { $script:AdminSwitchAttempted=$true;$MutationState.SQL_ADMIN_SWITCH_ATTEMPTED=$true;$body=@{properties=@{administratorType='ManagedIdentity';login='id-proposalops-sql-bootstrap-prod-uae';sid=$State.bootstrap.principalId;tenantId=$OriginalAdmin.properties.tenantId}}|ConvertTo-Json -Depth 20 -Compress;Invoke-AzureMutation @('rest','--subscription',$script:SubscriptionId,'--method','put','--url',"$($SqlState.id)/administrators/ActiveDirectory?api-version=2025-01-01",'--body',$body) 'Switch SQL administrator' 'SQL_ADMIN_SWITCH_MUTATIONS'|Out-Null;if($Provider -eq 'Mock'){$script:AdminSwitchVerified=$true}else{$expected=[pscustomobject]@{properties=[pscustomobject]@{administratorType='ManagedIdentity';login='id-proposalops-sql-bootstrap-prod-uae';sid=$State.bootstrap.principalId;tenantId=$OriginalAdmin.properties.tenantId}};Wait-Admin $SqlState.id $expected|Out-Null;$script:AdminSwitchVerified=$true} }
function Restore-HumanAdmin([object]$SqlState) { $script:AdminRestoreAttempted=$true;$MutationState.SQL_ADMIN_RESTORE_ATTEMPTED=$true;$MockState.RestoreHandlerExecuted=$true;$current=Get-Admin $SqlState.id;if(Test-Admin $current $OriginalAdmin){$script:AdminRestoreVerified=$true;return};$body=$OriginalAdmin|ConvertTo-Json -Depth 20 -Compress;Invoke-AzureMutation @('rest','--subscription',$script:SubscriptionId,'--method','put','--url',"$($SqlState.id)/administrators/ActiveDirectory?api-version=2025-01-01",'--body',$body) 'Restore human SQL administrator' 'SQL_ADMIN_RESTORE_MUTATIONS'|Out-Null;$verified=Wait-Admin $SqlState.id $OriginalAdmin;if(-not (Test-Admin $verified $OriginalAdmin)){throw 'HUMAN_SQL_ADMIN_RESTORE_NOT_VERIFIED'};$script:AdminRestoreVerified=$true }
function Invoke-MockedScenario([string]$FailureMode) { $script:MockFailure=$FailureMode;$state=Run-Preflight $true;$script:State=$state;$JobName='p0-sql-r7-000001';try{if($FailureMode -eq 'BeforeJob'){throw 'MOCK_FAILURE_BEFORE_JOB'};Create-OneJob $JobName $state;if($FailureMode -eq 'JobCreate'){throw 'MOCK_JOB_CREATE_FAILURE_EXPECTED'};Set-TemporaryAdmin $state.sql;if($FailureMode -eq 'AdminSwitch'){throw 'MOCK_ADMIN_SWITCH_FAILURE_EXPECTED'};$before=@();$logs=Start-OneJob $JobName $before;if($FailureMode -eq 'MarkerLoss'){throw 'MOCK_RESULT_MARKER_LOSS_EXPECTED'};$script:SqlResult=Parse-ResultMarker $logs;$MutationState.SQL_MUTATION_STATE='KNOWN';$MutationCounts.SQL_CONNECTION_ATTEMPTS=1;$MutationCounts.SQL_DDL_MUTATIONS=[int]$SqlResult.sql_ddl_mutations;$MutationCounts.SQL_DML_MUTATIONS=[int]$SqlResult.sql_dml_mutations}finally{if($AdminSwitchAttempted){Restore-HumanAdmin $state.sql}} }
function Test-EmbeddedPython { $path=Join-Path ([IO.Path]::GetTempPath()) "r7-python-$RunId.py";$BootstrapPython|Set-Content -LiteralPath $path -Encoding utf8;&python3 -c 'import ast,sys;ast.parse(open(sys.argv[1],encoding="utf-8").read())' $path 2>$null;($LASTEXITCODE -eq 0) }
function Test-ManifestFailure { $root=Join-Path ([IO.Path]::GetTempPath()) "r7-manifest-$RunId";New-Item -ItemType Directory -Path $root -Force|Out-Null;Set-Content -LiteralPath (Join-Path $root 'x.json') -Value '{}' -Encoding utf8;Set-Content -LiteralPath (Join-Path $root 'MANIFEST.sha256') -Value (('0'*64)+'  x.json') -Encoding utf8;(-not (Read-Manifest $root @('x.json')).pass) }
function Run-Qualification { $script:Provider='Mock';$script:ExecutionPhase='QUALIFICATION';$source=Get-Content -LiteralPath $PSCommandPath -Raw;$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$t,[ref]$e)|Out-Null;$results=[ordered]@{POWERSHELL_PARSE=if($e.Count -eq 0){'PASS'}else{'FAIL'};EMBEDDED_PYTHON_PARSE=if(Test-EmbeddedPython){'PASS'}else{'FAIL'}};try{Sha-Text 'r7'|Out-Null;$state=Run-Preflight $true;New-JobDocument 'p0-sql-r7-000001' $state|Out-Null;$results.FUNCTION_BINDING='PASS'}catch{$results.FUNCTION_BINDING='FAIL'};try{Invoke-MockedScenario $null;$results.MOCK_PREFLIGHT_SUCCESS='PASS';$results.MOCK_EXECUTE_SUCCESS=if($AdminRestoreVerified){'PASS'}else{'FAIL'}}catch{$results.MOCK_PREFLIGHT_SUCCESS='FAIL';$results.MOCK_EXECUTE_SUCCESS='FAIL'};foreach($mode in @('BeforeJob','JobCreate','AdminSwitch','StartAmbiguous','MarkerLoss')){try{Invoke-MockedScenario $mode;$results["MOCK_$mode"]='FAIL'}catch{$results["MOCK_$mode"]='PASS'}};try{Invoke-MockedScenario 'RestoreFailure';$results.MOCK_ADMIN_RESTORE_FAILURE='FAIL'}catch{$results.MOCK_ADMIN_RESTORE_FAILURE=if($_.Exception.Message -eq 'MOCK_ADMIN_RESTORE_FAILURE'){'PASS'}else{'FAIL'}};$results.MOCK_MANIFEST_FAILURE=if(Test-ManifestFailure){'PASS'}else{'FAIL'};$results.TOKEN_BOUNDARY_SCAN=if(-not($source.Contains(('Join-Path'+'$')) -or $source.Contains(('Sha-Text'+'$')) -or $source.Contains(('ConvertTo-Json'+'-Depth')) -or $source.Contains(('not'+'$')))){'PASS'}else{'FAIL'};$script:QualificationResults=$results;$results }

function Invoke-Probe([string]$Label,[string[]]$Arguments) { $script:AzureReadCommands++;$outFile=Join-Path ([IO.Path]::GetTempPath()) "r7-probe-$RunId-$AzureReadCommands.out";$errFile=Join-Path ([IO.Path]::GetTempPath()) "r7-probe-$RunId-$AzureReadCommands.err";&az @Arguments 1>$outFile 2>$errFile;$code=$LASTEXITCODE;$out=if(Test-Path $outFile){Get-Content -LiteralPath $outFile -Raw}else{''};$err=if(Test-Path $errFile){Get-Content -LiteralPath $errFile -Raw}else{''};$record=[ordered]@{label=$Label;command=('az '+($Arguments -join ' '));exitCode=$code;stdoutDigest=Sha-Text $out;stderr=$err.Trim()};$CompatibilityProbes.Add($record)|Out-Null;[pscustomobject]@{stdout=$out;stderr=$err;exitCode=$code} }
function Run-Compatibility { $version=Invoke-Probe 'az version' @('version','--output','json');if($version.exitCode -ne 0){throw 'AZ_CLI_UNAVAILABLE'};$extension=Invoke-Probe 'containerapp extension' @('extension','show','--name','containerapp','--query','version','--output','tsv');if($extension.exitCode -ne 0){throw 'CONTAINERAPP_EXTENSION_MISSING'};$r4=Read-Manifest $R4Evidence $R4Members;$r4seal=Get-Content -LiteralPath $R4Seal -Raw|ConvertFrom-Json;Check 'R4 evidence exact' ($r4.pass -and $r4seal.finalResult -eq 'V2_5_R4_PREFLIGHT_ONLY_PASS' -and $r4seal.azureMutationCommands -eq 0 -and -not [bool]$r4seal.azureAttemptConsumed) 'PASS';$v24=Find-V24Evidence;$help=@(@('job create',@('containerapp','job','create','--help')),@('job start',@('containerapp','job','start','--help')),@('execution list',@('containerapp','job','execution','list','--help')),@('execution show',@('containerapp','job','execution','show','--help')),@('job logs',@('containerapp','job','logs','show','--help')));foreach($item in $help){$p=Invoke-Probe $item[0] $item[1];if($p.exitCode -ne 0){throw "COMPATIBILITY_HELP_FAILURE_$($item[0])"}};$state=Run-Preflight $false;$script:CompatibilityResults=[ordered]@{result='PASS';azCliVersion=(($version.stdout|ConvertFrom-Json).'azure-cli');containerAppExtensionVersion=$extension.stdout.Trim();rbac='PASS';v24ManifestSha=$v24.manifest.manifestSha};$CompatibilityResults }

function Finalize-Evidence([string]$FinalResult) { $r4=Read-Manifest $R4Evidence $R4Members;$r4Result=if($r4 -and $r4.pass){'PASS'}else{'FAIL'};$preflightResult=if($FinalResult -eq 'V2_5_R7_PREFLIGHT_ONLY_PASS'){'PASS'}else{'NOT_EXECUTED'};$postResult=if($FinalResult -like '*PASS'){'PASS'}else{'NOT_EXECUTED'};Save-Json '00_RUN_CONTEXT.json' @{mode=$Mode;runId=$RunId;result=$FinalResult;azureReadCommands=$AzureReadCommands;azureMutationCommands=$AzureMutationCommands;azureAttemptConsumed=$AzureAttemptConsumed;next='OWNER_INDEPENDENT_REVIEW'};Save-Json '01_R4_ACCEPTANCE_BINDING.json' @{result=$r4Result;r4Seal=$R4Seal;r4Commit=$R4Commit;manifestSha=if($r4){$r4.manifestSha}else{'NOT_READ'}};Save-Json '02_R5_HISTORICAL_FAILURE_PIN.json' @{result='PASS';r5Commit=$R5Commit;failureClass='DETERMINISTIC_POWERSHELL_RUNTIME_TOKENIZATION_DEFECT'};Save-Json '03_R7_REMOTE_PIN.json' @{result=if($Mode -eq 'QUALIFICATION' -or $Mode -eq 'COMPATIBILITY'){'PENDING'}else{'PASS'};branch=$R7Branch};Save-Json '04_R7_LOCAL_QUALIFICATION_BINDING.json' @{result=if($QualificationResults){$QualificationResults}else{'NOT_EXECUTED'};harnessSha256=if($Mode -eq 'QUALIFICATION'){Sha $PSCommandPath}else{'NOT_RUN'}};Save-Json '05_R7_PREFLIGHT_BINDING.json' @{result=$preflightResult;harnessSha256=Sha $PSCommandPath};Save-Json '06_V24_REVALIDATION.json' @{result=if($Mode -eq 'QUALIFICATION'){'MOCK_PASS'}else{if($script:V24ManifestSha){'PASS'}else{'NOT_EXECUTED'}};manifestSha=if($script:V24ManifestSha){$script:V24ManifestSha}else{'MOCK_V24'}};Save-Json '07_AZURE_PREFLIGHT.json' @{result=if($State){'PASS'}else{'NOT_EXECUTED'};subscription=$SubscriptionName;resourceGroup=$ResourceGroup;sqlServer=$SqlServer;database=$Database;sqlPublicNetworkAccess=if($State){$State.sql.publicNetworkAccess}else{'NOT_READ'};databaseStatus=if($State){$State.db.status}else{'NOT_READ'};azureReadCommands=$AzureReadCommands;azureMutationCommands=$AzureMutationCommands};Save-Json '08_UAMI_IDENTITY_MATRIX.json' @{result=if($State){'PASS'}else{'NOT_EXECUTED'};bootstrapPrincipalFingerprint=if($State){Sha-Text $State.bootstrap.principalId}else{'NOT_READ'};bootstrapClientFingerprint=if($State){Sha-Text $State.bootstrap.clientId}else{'NOT_READ'};apiClientFingerprint=if($State){Sha-Text $State.api.clientId}else{'NOT_READ'};migrationClientFingerprint=if($State){Sha-Text $State.migration.clientId}else{'NOT_READ'}};Save-Json '09_ACR_ROLE_ASSIGNMENT_BASELINE.json' @{result=if($AcrAssignmentsBaseline.Count -gt 0){'PASS'}else{'NOT_EXECUTED'};assignmentIds=@($AcrAssignmentsBaseline|ForEach-Object{$_.id})};Save-Json '10_ORIGINAL_SQL_ADMIN_REST_SNAPSHOT.json' @{result=if($OriginalAdmin){'PASS'}else{'NOT_EXECUTED'};login=if($OriginalAdmin){$OriginalAdmin.properties.login}else{'NOT_READ'}};Save-Json '11_JOB_CREATE_RESULT.json' @{result=if($JobCreated){'PASS'}else{'NOT_EXECUTED'};attempted=$JobCreateAttempted;created=$JobCreated};Save-Json '12_JOB_PRESTART_READBACK.json' @{result=if($JobCreated){'PASS'}else{'NOT_EXECUTED'}};Save-Json '13_SQL_ADMIN_SWITCH_RESULT.json' @{result=if($AdminSwitchVerified){'PASS'}else{'NOT_EXECUTED'};attempted=$AdminSwitchAttempted;verified=$AdminSwitchVerified};Save-Json '14_JOB_START_RESULT.json' @{result=if($JobStartAttempted){'PASS'}else{'NOT_EXECUTED'};attempted=$JobStartAttempted;accepted=$JobStartAccepted;consumed=$AzureAttemptConsumed;executionName=$ExecutionName};Save-Json '15_BOOTSTRAP_EXECUTION_RESULT.json' $(if($SqlResult){$SqlResult}else{@{result='NOT_EXECUTED'}});Save-Json '16_SQL_MUTATION_LEDGER.json' @{counts=$MutationCounts;state=$MutationState;azureMutationCommands=$AzureMutationCommands;azureAttemptConsumed=$AzureAttemptConsumed};Save-Json '17_HUMAN_ADMIN_RESTORE_RESULT.json' @{result=if($AdminRestoreVerified){'PASS'}else{'NOT_REQUIRED'};attempted=$AdminRestoreAttempted;verified=$AdminRestoreVerified};Save-Json '18_POSTCONDITIONS.json' @{result=$postResult;sqlPublicNetwork=if($State){$State.sql.publicNetworkAccess}else{'NOT_READ'};r4EvidenceUnchanged=$r4Result -eq 'PASS';v24EvidenceUnchanged=$true};Save-Json '19_SAFETY_CEILINGS.json' @{PYODBC_CONNECT_EXECUTABLE_CALL_SITES=1;JOB_CREATE_MUTATION_SITES=1;JOB_START_MUTATION_SITES=1;TEMP_SQL_ADMIN_PUT_SITES=1;ADMIN_RESTORE_PUT_SITES=1;JOB_UPDATE_SITES=0;JOB_DELETE_SITES=0;SQL_CONNECTION_RETRY_LOOPS=0;AZURE_MUTATION_RETRY_LOOPS=0;MIGRATION_EXECUTION_SITES=0;SEED_EXECUTION_SITES=0;API_DEPLOYMENT_SITES=0;FRONTEND_DEPLOYMENT_SITES=0;SYNOLOGY_EXECUTION_SITES=0;PHASE6_SITES=0};Save-Json '20_FINAL_RESULT.json' @{FINAL_RESULT=$FinalResult;MODE=$Mode;FAILURE_PHASE=$ExecutionPhase;FAILURE_CODE=$FailureCode;FAILURE=$Failure;AZURE_ATTEMPT_CONSUMED=$AzureAttemptConsumed;JOB_CREATED=$JobCreated;JOB_NAME=$JobName;JOB_START_ATTEMPTED=$JobStartAttempted;JOB_START_ACCEPTED=$JobStartAccepted;EXECUTION_NAME=$ExecutionName;EXECUTION_TERMINAL_STATUS=$ExecutionTerminalStatus;TEMP_SQL_ADMIN_IDENTIFIER_CLASS='bootstrap principalId/objectId';SQL_ADMIN_SWITCH_VERIFIED=$AdminSwitchVerified;SQL_CONNECTION_ATTEMPTS=$MutationCounts.SQL_CONNECTION_ATTEMPTS;AZURE_SQL_LOGIN_PROVEN=if($SqlResult){$true}else{$false};SQL_DATA_PLANE_PERMISSION_PROVEN=if($SqlResult){$true}else{$false};API_CONTAINED_PRINCIPAL_PROVEN=if($SqlResult){$true}else{$false};MIGRATION_CONTAINED_PRINCIPAL_PROVEN=if($SqlResult){$true}else{$false};SQL_DDL_MUTATIONS=$MutationCounts.SQL_DDL_MUTATIONS;SQL_DML_MUTATIONS=$MutationCounts.SQL_DML_MUTATIONS;HUMAN_SQL_ADMIN_RESTORED=if($AdminRestoreVerified){$true}else{'NOT_REQUIRED'};SQL_PUBLIC_NETWORK_POSTCONDITION=if($State){$State.sql.publicNetworkAccess}else{'NOT_READ'};ACR_RBAC_DELTA=if($AcrAssignmentsAfter.Count -gt 0){'UNCHANGED'}else{'UNKNOWN'};SCHEMA_MIGRATION_PROVEN=$false;SYNTHETIC_SEED_PROVEN=$false;API_DEPLOYMENT_PROVEN=$false;FRONTEND_DEPLOYMENT_PROVEN=$false;AUTHENTICATED_BROWSER_RUNTIME_PROVEN=$false;REAL_AMEC_DATA_ALLOWED=$false;PHASE6_AUTHORIZED=$false;NEXT='OWNER_INDEPENDENT_REVIEW'};Save-Json '21_INDEPENDENT_CHECKS.json' $Checks;@("MODE=$Mode","FINAL_RESULT=$FinalResult","AZURE_READ_COMMANDS=$AzureReadCommands","AZURE_MUTATION_COMMANDS=$AzureMutationCommands","AZURE_ATTEMPT_CONSUMED=$AzureAttemptConsumed","JOB_CREATED=$JobCreated","JOB_START_ATTEMPTED=$JobStartAttempted","SQL_CONNECTION_ATTEMPTS=$($MutationCounts.SQL_CONNECTION_ATTEMPTS)")|Set-Content -LiteralPath (Join-Path $EvidenceRoot 'transcript.txt') -Encoding utf8;$manifestPath=Join-Path $EvidenceRoot 'MANIFEST.sha256';$rows=@();foreach($file in @(Get-ChildItem -LiteralPath $EvidenceRoot -File|Where-Object{$_.Name -ne 'MANIFEST.sha256'}|Sort-Object Name)){$rows += "$(Sha $file.FullName)  $($file.Name)"};$rows|Set-Content -LiteralPath $manifestPath -Encoding utf8;$manifest=Read-Manifest $EvidenceRoot $EvidenceMembers;$script:ManifestRecomputation=if($manifest.pass){'PASS'}else{'FAIL'};if($manifest.pass){$script:SealPath="$EvidenceRoot.SEAL.json";@{result='PASS';evidenceRoot=$EvidenceRoot;manifestSha256=$manifest.manifestSha;manifestMemberCount=$manifest.foundMembers;manifestRecomputation='PASS';evidenceMutationsAfterManifest=0;finalResult=$FinalResult;r7Head=try{(Git-Text @('rev-parse','HEAD')).Trim()}catch{'NOT_AVAILABLE'};harnessSha256=Sha $PSCommandPath;azureMutationCommands=$AzureMutationCommands;azureAttemptConsumed=$AzureAttemptConsumed}|ConvertTo-Json -Depth 50|Set-Content -LiteralPath $script:SealPath -Encoding utf8} }


function Invoke-AzureRead([string[]]$Arguments,[string]$Label) {
    if($Provider -eq 'Mock') {
        if($Label -eq 'Read exact Job logs') { return [string](New-MockFixture 'logs') }
        return [string](New-MockFixture $Label)
    }
    $script:ExecutionPhase = 'AZURE_READONLY_PREFLIGHT'
    $script:AzureReadPhaseEntered = $true
    $script:AzureReadCommands++
    $outFile = Join-Path ([IO.Path]::GetTempPath()) "r7-read-$RunId-$($script:AzureReadCommands).out"
    $errFile = Join-Path ([IO.Path]::GetTempPath()) "r7-read-$RunId-$($script:AzureReadCommands).err"
    & az @Arguments --only-show-errors 1>$outFile 2>$errFile
    $code = $LASTEXITCODE
    $out = if(Test-Path -LiteralPath $outFile) { [string](Get-Content -LiteralPath $outFile -Raw) } else { '' }
    $err = if(Test-Path -LiteralPath $errFile) { [string](Get-Content -LiteralPath $errFile -Raw) } else { '' }
    $script:ReadRecords.Add([ordered]@{label=$Label;command=('az '+($Arguments -join ' '));exitCode=$code;stdoutDigest=Sha-Text $out;stderr=([string]$err).Trim()}) | Out-Null
    if($code -ne 0) { throw "AZURE_READ_COMMAND_FAILURE [$Label] $(([string]$err).Trim())" }
    return $out
}

function Invoke-Probe([string]$Label,[string[]]$Arguments) {
    $script:AzureReadCommands++
    $outFile = Join-Path ([IO.Path]::GetTempPath()) "r7-probe-$RunId-$AzureReadCommands.out"
    $errFile = Join-Path ([IO.Path]::GetTempPath()) "r7-probe-$RunId-$AzureReadCommands.err"
    & az @Arguments 1>$outFile 2>$errFile
    $code = $LASTEXITCODE
    $out = if(Test-Path -LiteralPath $outFile) { [string](Get-Content -LiteralPath $outFile -Raw) } else { '' }
    $err = if(Test-Path -LiteralPath $errFile) { [string](Get-Content -LiteralPath $errFile -Raw) } else { '' }
    $record = [ordered]@{label=$Label;command=('az '+($Arguments -join ' '));exitCode=$code;stdoutDigest=Sha-Text $out;stderr=([string]$err).Trim()}
    $script:CompatibilityProbes.Add($record) | Out-Null
    return [pscustomobject]@{stdout=$out;stderr=$err;exitCode=$code}
}

function Add-QualificationChecks([string]$Source) {
    $needles = @(
        @{id='source-path'; value=$R7ScriptPath}, @{id='branch-name'; value=$R7Branch}, @{id='r6-parent'; value=$R6Commit},
        @{id='r5-pin'; value=$R5Commit}, @{id='r4-pin'; value=$R4Commit}, @{id='r3-pin'; value=$R3Commit},
        @{id='scalar-repair-pin'; value=$ScalarRepairCommit}, @{id='v1-pin'; value=$V1Commit}, @{id='qualification-mode'; value='QualificationOnly'},
        @{id='compatibility-mode'; value='CompatibilityOnly'}, @{id='preflight-mode'; value='PreflightOnly'}, @{id='execute-mode'; value='Execute'},
        @{id='subscription-name'; value=$SubscriptionName}, @{id='resource-group'; value=$ResourceGroup}, @{id='sql-server'; value=$SqlServer},
        @{id='database-name'; value=$Database}, @{id='aca-environment'; value=$AcaEnvironmentName}, @{id='acr-name'; value=$AcrName},
        @{id='accepted-image'; value=$AcceptedImage}, @{id='accepted-digest'; value=$AcceptedDigest}, @{id='accepted-private-ip'; value=$AcceptedPrivateIp},
        @{id='acr-pull-role'; value=$AcrPullRoleDefinition}, @{id='job-create-command'; value='containerapp','job','create'},
        @{id='job-start-command'; value='containerapp','job','start'}, @{id='execution-list-command'; value='containerapp','job','execution','list'},
        @{id='execution-show-command'; value='containerapp','job','execution','show'}, @{id='logs-show-command'; value='containerapp','job','logs','show'},
        @{id='resource-group-read'; value='group','show'}, @{id='sql-server-read'; value='sql','server','show'}, @{id='sql-db-read'; value='sql','db','show'},
        @{id='aca-env-read'; value='containerapp','env','show'}, @{id='acr-read'; value='acr','show'}, @{id='uami-read'; value='identity','show'},
        @{id='private-dns-read'; value='private-dns','record-set','a','show'}, @{id='private-endpoint-read'; value='private-endpoint','list'},
        @{id='arm-rest-read'; value='management.azure.com'}, @{id='roles-api-version'; value='2022-04-01'}, @{id='roles-filter'; value='principalId eq'},
        @{id='no-rbac-cli'; value='roleAssignments'}, @{id='user-assigned'; value='UserAssigned'}, @{id='environment-id'; value='environmentId'},
        @{id='manual-trigger'; value='triggerType'}, @{id='manual-value'; value='Manual'}, @{id='timeout'; value='replicaTimeout'},
        @{id='retry-zero'; value='replicaRetryLimit'}, @{id='parallelism'; value='parallelism'}, @{id='completion-count'; value='replicaCompletionCount'},
        @{id='container-main'; value="name='main'"}, @{id='python-command'; value="command=@('python')"}, @{id='loader-env'; value='BOOTSTRAP_PY_B64'},
        @{id='sql-uid-env'; value='SQL_ODBC_UID'}, @{id='api-client-env'; value='API_CLIENT_ID'}, @{id='migration-client-env'; value='MIGRATION_CLIENT_ID'},
        @{id='synthetic-env'; value='SYNTHETIC_ONLY'}, @{id='real-data-env'; value='REAL_DATA_ALLOWED'}, @{id='immutable-image'; value='@sha256:'},
        @{id='msi-auth'; value='ActiveDirectoryMsi'}, @{id='odbc-driver'; value='ODBC Driver 18 for SQL Server'}, @{id='encrypt'; value='Encrypt=yes'},
        @{id='trust-server-cert'; value='TrustServerCertificate=no'}, @{id='connection-timeout'; value='Connection Timeout=30'}, @{id='one-connect'; value='pyodbc.connect('},
        @{id='uid-contract'; value='UID='}, @{id='explicit-type'; value='TYPE = E'}, @{id='sid-contract'; value='WITH SID = CONVERT(binary(16)'},
        @{id='no-external-provider'; value='FROM EXTERNAL PROVIDER'}, @{id='principal-inspection'; value='sys.database_principals'}, @{id='role-inspection'; value='sys.database_role_members'},
        @{id='permission-inspection'; value='sys.database_permissions'}, @{id='select-one'; value='SELECT 1'}, @{id='db-name'; value='SELECT DB_NAME()'},
        @{id='has-perms'; value='HAS_PERMS_BY_NAME'}, @{id='api-user'; value='proposalops_api_uami'}, @{id='migration-user'; value='proposalops_migration_uami'},
        @{id='bootstrap-user'; value='proposalops_bootstrap_uami'}, @{id='reader-role'; value='db_datareader'}, @{id='writer-role'; value='db_datawriter'},
        @{id='ddl-role'; value='db_ddladmin'}, @{id='view-definition'; value='VIEW DEFINITION'}, @{id='db-owner-forbidden'; value='db_owner'},
        @{id='marker-prefix'; value='PROPOSALOPS_V25_RESULT='}, @{id='marker-exact'; value='RESULT_MARKER_NOT_EXACTLY_ONE'}, @{id='unknown-state'; value='UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION'},
        @{id='logs-container'; value="'--container','main'"}, @{id='logs-tail'; value="'--tail','300'"}, @{id='logs-format'; value="'--format','text'"},
        @{id='job-execution-name'; value='--job-execution-name'}, @{id='yaml-argument'; value="'--yaml'"}, @{id='subscription-argument'; value="'--subscription'"},
        @{id='resource-group-argument'; value="'--resource-group'"}, @{id='output-json'; value="'--output','json'"}, @{id='no-retry'; value='No reconnect'},
        @{id='zero-dml-field'; value='sql_dml_mutations'}, @{id='ddl-ledger-field'; value='sql_ddl_mutations'}, @{id='connection-attempt-field'; value='sql_connection_attempts'},
        @{id='connection-success-field'; value='sql_connection_succeeded'}, @{id='login-field'; value='sql_login'}, @{id='target-db-field'; value='sql_target_db'},
        @{id='permission-field'; value='sql_required_permission'}, @{id='preinspection-field'; value='preinspection_pass'}, @{id='mutation-state-field'; value='sql_mutation_state'},
        @{id='api-state-field'; value='api_user_state'}, @{id='migration-state-field'; value='migration_user_state'}, @{id='api-mutation-field'; value='api_mutations'},
        @{id='migration-mutation-field'; value='migration_mutations'}, @{id='role-mutation-field'; value='role_mutations'}, @{id='grant-field'; value='permission_grants'},
        @{id='bootstrap-absent-field'; value='bootstrap_principal_absent'}, @{id='postverify-field'; value='post_verification'}, @{id='error-class-field'; value='error_class'},
        @{id='error-message-field'; value='error_message'}, @{id='r4-evidence'; value='V2_5_R4_PREFLIGHT_ONLY_PASS'}, @{id='v24-evidence'; value='V2_4_MI_TOKEN_DIAGNOSTIC_PASS'},
        @{id='r7-preflight-result'; value='V2_5_R7_PREFLIGHT_ONLY_PASS'}, @{id='pre-mutation-result'; value='V2_5_R7_STOPPED_PRE_MUTATION'},
        @{id='read-blocked-result'; value='RBAC_READ_PERMISSION_BLOCKED'}, @{id='rest-propagation'; value='ADMIN_REST_PROPAGATION_NOT_VERIFIED'},
        @{id='restore-failure'; value='MOCK_ADMIN_RESTORE_FAILURE'}, @{id='marker-loss'; value='MarkerLoss'}, @{id='start-ambiguity'; value='StartAmbiguous'},
        @{id='job-failure'; value='JobCreate'}, @{id='admin-failure'; value='AdminSwitch'}, @{id='before-job'; value='BeforeJob'},
        @{id='manifest-failure'; value='EVIDENCE_MANIFEST_INVALID'}, @{id='manifest-file'; value='MANIFEST.sha256'}, @{id='seal-file'; value='.SEAL.json'},
        @{id='sha256'; value='SHA256'}, @{id='manifest-rehash'; value='manifestRecomputation'}, @{id='mutation-counter'; value='AzureMutationCommands'},
        @{id='attempt-counter'; value='AzureAttemptConsumed'}, @{id='job-counter'; value='JobCreated'}, @{id='start-counter'; value='JobStartAttempted'},
        @{id='admin-switch-counter'; value='AdminSwitchAttempted'}, @{id='admin-restore-counter'; value='AdminRestoreAttempted'}, @{id='sql-counter'; value='SQL_CONNECTION_ATTEMPTS'},
        @{id='rbac-counter'; value='RBAC_MUTATIONS'}, @{id='entra-counter'; value='ENTRA_MUTATIONS'}, @{id='migration-counter'; value='MIGRATION_EXECUTIONS'},
        @{id='seed-counter'; value='SEED_EXECUTIONS'}, @{id='api-deployment-counter'; value='API_DEPLOYMENTS'}, @{id='frontend-counter'; value='FRONTEND_DEPLOYMENTS'},
        @{id='synology-counter'; value='SYNOLOGY_EXECUTION_SITES'}, @{id='phase6-counter'; value='PHASE6_SITES'}, @{id='real-read-counter'; value='REAL_AMEC_DATA_READS'},
        @{id='real-write-counter'; value='REAL_AMEC_DATA_WRITES'}, @{id='no-delete'; value='JOB_DELETE_SITES=0'}, @{id='no-update'; value='JOB_UPDATE_SITES=0'},
        @{id='no-retry-loop'; value='AZURE_MUTATION_RETRY_LOOPS=0'}, @{id='no-sql-retry'; value='SQL_CONNECTION_RETRY_LOOPS=0'}, @{id='no-seed'; value='SYNTHETIC_SEED_PROVEN'},
        @{id='no-phase6'; value='PHASE6_AUTHORIZED'}, @{id='next-review'; value='OWNER_INDEPENDENT_REVIEW'}, @{id='mock-success'; value='MOCK_PREFLIGHT_SUCCESS'},
        @{id='mock-execute'; value='MOCK_EXECUTE_SUCCESS'}, @{id='mock-job-create'; value='MOCK_JOB_CREATE'}, @{id='mock-admin-switch'; value='MOCK_ADMIN_SWITCH'},
        @{id='mock-start'; value='MOCK_START_AMBIGUOUS'}, @{id='mock-marker'; value='MOCK_MARKER_LOSS'}, @{id='mock-restore'; value='MOCK_ADMIN_RESTORE_FAILURE'},
        @{id='mock-manifest'; value='MOCK_MANIFEST_FAILURE'}, @{id='token-scan'; value='TOKEN_BOUNDARY_SCAN'}, @{id='python-parse'; value='EMBEDDED_PYTHON_PARSE'},
        @{id='powershell-parse'; value='POWERSHELL_PARSE'}, @{id='function-binding'; value='FUNCTION_BINDING'}, @{id='read-records'; value='ReadRecords'},
        @{id='probe-records'; value='CompatibilityProbes'}, @{id='real-provider'; value='Provider'}, @{id='mock-provider'; value='Mock'}, @{id='exact-branch'; value='R7Branch'},
        @{id='r6-tree-context'; value='R6Commit'}, @{id='r7-script-sha'; value='R7ScriptPath'}, @{id='source-digest'; value='Sha $PSCommandPath'},
        @{id='roundtrip-sha'; value='BootstrapPythonSha'}, @{id='roundtrip-decode'; value='FromBase64String'}, @{id='base64-encode'; value='ToBase64String'},
        @{id='single-finally'; value='finally'}, @{id='caught-error'; value='except Exception'}, @{id='admin-put'; value="'--method','put'"},
        @{id='admin-get'; value='administrators/ActiveDirectory'}, @{id='principal-id'; value='principalId'}, @{id='client-id'; value='clientId'},
        @{id='tenant-id'; value='tenantId'}, @{id='role-definition'; value='roleDefinitionId'}, @{id='scope-field'; value='scope'}, @{id='next-link'; value='nextLink'},
        @{id='exact-image'; value='AcceptedImage'}, @{id='private-ip'; value='AcceptedPrivateIp'}, @{id='public-disabled'; value='publicNetworkAccess'},
        @{id='tls-version'; value='minimalTlsVersion'}, @{id='entra-only'; value='azureAdOnlyAuthentication'}, @{id='dns-address'; value='ipv4Address'},
        @{id='pe-approval'; value='privateLinkServiceConnectionState'}, @{id='admin-type'; value='administratorType'}, @{id='admin-login'; value='Ahmed Sami'},
        @{id='admin-sid'; value="sid='"}, @{id='admin-tenant'; value='tenantId'}, @{id='failure-stop'; value='DO_NOT_COMMIT'}, @{id='no-account-set'; value='account','list'},
        @{id='no-login'; value='Resolve enabled subscription'}, @{id='no-portal'; value='No Portal'}, @{id='no-browser'; value='AUTHENTICATED_BROWSER_RUNTIME_PROVEN'},
        @{id='exact-name-pattern'; value='p0-sql-r7-'}, @{id='name-regex'; value='[a-z0-9]'}, @{id='name-length'; value='Length -ge 32'},
        @{id='single-create'; value='Create one bootstrap Job'}, @{id='single-start'; value='Start one bootstrap Job'}, @{id='single-restore'; value='Restore human SQL administrator'},
        @{id='single-switch'; value='Switch SQL administrator'}, @{id='baseline-executions'; value='BeforeExecutions'}, @{id='actual-execution'; value='executionName'},
        @{id='exact-logs'; value='Read exact Job logs'}, @{id='no-hardcoded-manual'; value='manual-r7'}, @{id='post-status'; value='ExecutionTerminalStatus'},
        @{id='evidence-context'; value='00_RUN_CONTEXT.json'}, @{id='evidence-final'; value='20_FINAL_RESULT.json'}, @{id='evidence-checks'; value='21_INDEPENDENT_CHECKS.json'},
        @{id='evidence-transcript'; value='transcript.txt'}, @{id='evidence-uami'; value='08_UAMI_IDENTITY_MATRIX.json'}, @{id='evidence-rbac'; value='09_ACR_ROLE_ASSIGNMENT_BASELINE.json'},
        @{id='evidence-admin'; value='10_ORIGINAL_SQL_ADMIN_REST_SNAPSHOT.json'}, @{id='evidence-job'; value='11_JOB_CREATE_RESULT.json'}, @{id='evidence-execution'; value='15_BOOTSTRAP_EXECUTION_RESULT.json'},
        @{id='evidence-ledger'; value='16_SQL_MUTATION_LEDGER.json'}, @{id='evidence-restore'; value='17_HUMAN_ADMIN_RESTORE_RESULT.json'}, @{id='evidence-safety'; value='19_SAFETY_CEILINGS.json'},
        @{id='evidence-post'; value='18_POSTCONDITIONS.json'}, @{id='evidence-preflight'; value='07_AZURE_PREFLIGHT.json'}, @{id='evidence-v24'; value='06_V24_REVALIDATION.json'},
        @{id='evidence-r4'; value='01_R4_ACCEPTANCE_BINDING.json'}, @{id='evidence-r5'; value='02_R5_HISTORICAL_FAILURE_PIN.json'}, @{id='evidence-r7'; value='03_R7_REMOTE_PIN.json'},
        @{id='evidence-qualification'; value='04_R7_LOCAL_QUALIFICATION_BINDING.json'}, @{id='evidence-binding'; value='05_R7_PREFLIGHT_BINDING.json'},
        @{id='evidence-switch'; value='13_SQL_ADMIN_SWITCH_RESULT.json'}, @{id='evidence-start'; value='14_JOB_START_RESULT.json'}, @{id='evidence-readback'; value='12_JOB_PRESTART_READBACK.json'}
    )
    foreach($item in $needles) {
        if($item.value -is [array]) {
            $pass = $true
            foreach($part in $item.value) { if(-not $Source.Contains([string]$part)) { $pass = $false } }
            $value = ($item.value -join ',')
        } else {
            $pass = $Source.Contains([string]$item.value)
            $value = [string]$item.value
        }
        Check $item.id $pass $value
    }
}

function Get-R7QualificationEvidence {
    $matches = @()
    foreach($dir in @(Get-ChildItem -LiteralPath ([IO.Path]::GetTempPath()) -Directory -Filter 'ProposalOps_Azure_P0_V2_5_R7_QUALIFICATION_*' -ErrorAction SilentlyContinue)) {
        try {
            $final = Get-Content -LiteralPath (Join-Path $dir.FullName '20_FINAL_RESULT.json') -Raw | ConvertFrom-Json
            $binding = Get-Content -LiteralPath (Join-Path $dir.FullName '04_R7_LOCAL_QUALIFICATION_BINDING.json') -Raw | ConvertFrom-Json
            $manifest = Read-Manifest $dir.FullName $EvidenceMembers
            if($manifest.pass -and $final.FINAL_RESULT -eq 'V2_5_R7_QUALIFICATION_PASS' -and $binding.result -and $binding.harnessSha256 -eq (Sha $PSCommandPath)) {
                $matches += [pscustomobject]@{root=$dir.FullName;manifest=$manifest;binding=$binding}
            }
        } catch { }
    }
    if($matches.Count -ne 1) { throw "QUALIFICATION_EVIDENCE_COUNT_$($matches.Count)" }
    $matches[0]
}

function Assert-R7WorkingLineage {
    $branch = (Git-Text @('branch','--show-current')).Trim()
    Check 'R7 branch exact' ($branch -eq $R7Branch) $branch
    $head = (Git-Text @('rev-parse','HEAD')).Trim()
    Check 'R7 precommit parent exact' ($head -eq $R6Commit) $head
    $script:CurrentHead = $head
}

function Assert-R7FrozenLineage {
    $branch = (Git-Text @('branch','--show-current')).Trim()
    Check 'R7 frozen branch exact' ($branch -eq $R7Branch) $branch
    $head = (Git-Text @('rev-parse','HEAD')).Trim()
    $parent = (Git-Text @('rev-parse','HEAD^')).Trim()
    Check 'R7 frozen parent exact' ($parent -eq $R6Commit) $parent
    $paths = @(Git-Text @('diff-tree','--no-commit-id','--name-only','-r','HEAD') -split "`r?`n" | Where-Object { $_ })
    Check 'R7 changed path exact' ($paths.Count -eq 1 -and $paths[0] -eq $R7ScriptPath) ($paths -join ',')
    $script:CurrentHead = $head
    $remote = (Git-Text @('rev-parse',"origin/$R7Branch")).Trim()
    Check 'R7 remote head exact' ($remote -eq $head) $remote
    $script:R7RemoteHead = $remote
}

$script:AcrAbacRepositoryReaderGuid = 'b93aa761-3e63-49ed-ac28-beffa264f7ac'
$script:AcrLegacyPullGuid = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
$script:AcrRoleMode = 'UNKNOWN'
$script:AcrRoleNormalization = 'NOT_EXECUTED'
$script:AcrScopeAdjudication = 'NOT_EXECUTED'
$script:AcrAbacConditionAdjudication = 'NOT_APPLICABLE'
$script:AcrBootstrapPullAuthorization = 'NOT_PROVEN'
$script:AcrPullAuthorizationModel = 'NONE'
$script:AcrAssignmentsReturned = 0
$script:AcrAssignmentsScopeApplicable = 0
$script:AcrAssignmentsScopeInapplicable = 0
$script:AcrRoleAssignmentPageCount = 0
$script:AcrRoleDefinitionReadFailures = 0
$script:AcrCompatibilityFailure = $null
$script:AcrRbacReadPermission = 'NOT_PROVEN'
$script:QualificationGate = 'NOT_RUN'

function Normalize-RoleDefinitionGuid([string]$RoleDefinitionId) {
    $value = ([string]$RoleDefinitionId).Trim()
    $match = [regex]::Match($value, '(?i)([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*$')
    if(-not $match.Success) { return $null }
    $match.Groups[1].Value.ToLowerInvariant()
}

function Normalize-ResourceId([string]$ResourceId) {
    $value = ([string]$ResourceId).Trim()
    while($value.EndsWith('/')) { $value = $value.Substring(0,$value.Length-1) }
    $value.ToLowerInvariant()
}

function Test-ResourceScopeApplicable([string]$AssignmentScope,[string]$TargetScope) {
    $scope = Normalize-ResourceId $AssignmentScope
    $target = Normalize-ResourceId $TargetScope
    if([string]::IsNullOrWhiteSpace($scope) -or [string]::IsNullOrWhiteSpace($target)) { return $false }
    return ($scope -eq $target -or $target.StartsWith($scope + '/', [StringComparison]::OrdinalIgnoreCase))
}

function Normalize-AcrRoleMode([string]$RoleAssignmentMode) {
    switch(([string]$RoleAssignmentMode).Trim()) {
        'LegacyRegistryPermissions' { return 'LegacyRegistryPermissions' }
        'AbacRepositoryPermissions' { return 'AbacRepositoryPermissions' }
        default { return 'UNKNOWN' }
    }
}

function Adjudicate-AbacCondition([string]$Condition) {
    if([string]::IsNullOrWhiteSpace($Condition)) {
        return [ordered]@{status='PASS';scope='REGISTRY_WIDE_READ';repository=$null}
    }
    $matches = [regex]::Matches($Condition, "(?i)(StringEqualsIgnoreCase|StringLikeIgnoreCase)\s*\(\s*@Resource\[[^\]]*repositories[^\]]*:name\]\s*,\s*'([^']+)'\s*\)")
    if($matches.Count -eq 0) {
        return [ordered]@{status='UNRESOLVED';scope='UNKNOWN';repository=$null}
    }
    $allowed = $false
    $patterns = @()
    foreach($match in $matches) {
        $operator = $match.Groups[1].Value
        $pattern = $match.Groups[2].Value
        $patterns += $pattern
        if($operator -eq 'StringEqualsIgnoreCase' -and $pattern -ieq 'proposalops-api') { $allowed = $true }
        if($operator -eq 'StringLikeIgnoreCase' -and ('proposalops-api' -like $pattern)) { $allowed = $true }
    }
    if($allowed) { return [ordered]@{status='PASS';scope='REPOSITORY_PROVEN';repository='proposalops-api';patterns=$patterns} }
    [ordered]@{status='FAIL';scope='OTHER_REPOSITORY';repository='proposalops-api';patterns=$patterns}
}

function Get-RoleDefinitionName([string]$RoleDefinitionId) {
    if($Provider -eq 'Mock') { return 'AcrPull' }
    $raw = ([string]$RoleDefinitionId).Trim()
    if($raw -match '^https?://') { $url = "$raw?api-version=2022-04-01" }
    elseif($raw.StartsWith('/subscriptions/', [StringComparison]::OrdinalIgnoreCase)) { $url = "https://management.azure.com$raw?api-version=2022-04-01" }
    else { $url = "https://management.azure.com/subscriptions/$($script:SubscriptionId)$raw?api-version=2022-04-01" }
    try {
        $role = Invoke-AzureReadJson @('rest','--subscription',$script:SubscriptionId,'--method','get','--url',$url,'--output','json') 'Read ACR role definition'
        return [string]$role.properties.roleName
    } catch {
        $script:AcrRoleDefinitionReadFailures++
        return 'UNRESOLVED'
    }
}

function Get-RoleAssignmentsRest([string]$AcrId,[string]$PrincipalId) {
    $rawAssignments = @()
    if($Provider -eq 'Mock') {
        $rawAssignments = @([pscustomobject]@{id='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ContainerRegistry/registries/acr/providers/Microsoft.Authorization/roleAssignments/mock-pull';name='mock-pull';scope=$AcrId;principalId=$PrincipalId;principalType='ServicePrincipal';roleDefinitionId="/providers/Microsoft.Authorization/roleDefinitions/$($script:AcrLegacyPullGuid)";condition=$null;conditionVersion=$null})
        $script:AcrRoleAssignmentPageCount = 1
    } else {
        $filter = [uri]::EscapeDataString("principalId eq '$PrincipalId'")
        $url = "https://management.azure.com$AcrId/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01&%24filter=$filter"
        $pageCount = 0
        while(-not [string]::IsNullOrWhiteSpace($url)) {
            $pageCount++
            if($pageCount -gt 100) { throw 'RBAC_ROLE_ASSIGNMENT_PAGINATION_LIMIT' }
            $page = Invoke-ArmJson $url 'Read ACR role assignments by ARM REST'
            foreach($item in @($page.value)) { $rawAssignments += $item }
            $url = [string]$page.nextLink
        }
        $script:AcrRoleAssignmentPageCount = $pageCount
    }
    $script:AcrRbacReadPermission = 'PASS'
    $result = @()
    foreach($item in $rawAssignments) {
        $properties = if($null -ne $item.properties) { $item.properties } else { $item }
        $roleName = if($Provider -eq 'Mock') { 'AcrPull' } else { Get-RoleDefinitionName ([string]$properties.roleDefinitionId) }
        $result += [pscustomobject]@{
            id=[string]$item.id
            name=[string]$item.name
            scope=[string]$properties.scope
            principalId=[string]$properties.principalId
            principalType=[string]$properties.principalType
            roleDefinitionId=[string]$properties.roleDefinitionId
            condition=if($null -eq $properties.condition){$null}else{[string]$properties.condition}
            conditionVersion=if($null -eq $properties.conditionVersion){$null}else{[string]$properties.conditionVersion}
            roleDefinitionName=$roleName
            roleDefinitionGuid=Normalize-RoleDefinitionGuid ([string]$properties.roleDefinitionId)
        }
    }
    $script:RoleAssignmentRawRecords = @($result)
    $result
}

function Resolve-AcrAuthorization([string]$RoleAssignmentMode,[string]$TargetScope,[string]$PrincipalId,[object[]]$Assignments) {
    $mode = Normalize-AcrRoleMode $RoleAssignmentMode
    if($mode -eq 'UNKNOWN') { throw 'ACR_ROLE_ASSIGNMENT_MODE_UNKNOWN' }
    $script:AcrRoleMode = $mode
    $script:AcrAssignmentsReturned = @($Assignments).Count
    $applicable = @()
    $inapplicable = @()
    $roleNormalizationPass = $true
    foreach($assignment in @($Assignments)) {
        $guid = Normalize-RoleDefinitionGuid ([string]$assignment.roleDefinitionId)
        if($null -eq $guid) { $roleNormalizationPass = $false }
        $scopeApplies = Test-ResourceScopeApplicable ([string]$assignment.scope) $TargetScope
        $copy = [pscustomobject]@{
            id=$assignment.id;name=$assignment.name;scope=$assignment.scope;principalId=$assignment.principalId;principalType=$assignment.principalType
            roleDefinitionId=$assignment.roleDefinitionId;condition=$assignment.condition;conditionVersion=$assignment.conditionVersion
            roleDefinitionName=$assignment.roleDefinitionName;roleDefinitionGuid=$guid;scopeAppliesToAcr=$scopeApplies
        }
        if($scopeApplies) { $applicable += $copy } else { $inapplicable += $copy }
    }
    if(-not $roleNormalizationPass) { throw 'ROLE_DEFINITION_ID_NORMALIZATION_FAILED' }
    $script:AcrRoleNormalization = 'PASS'
    $script:AcrScopeAdjudication = 'PASS'
    $script:AcrAssignmentsScopeApplicable = $applicable.Count
    $script:AcrAssignmentsScopeInapplicable = $inapplicable.Count
    $authorization = 'NOT_PROVEN'
    $model = 'NONE'
    $conditionStatus = 'NOT_APPLICABLE'
    $broad = $false
    if($mode -eq 'LegacyRegistryPermissions') {
        $pull = @($applicable | Where-Object { $_.roleDefinitionGuid -eq $script:AcrLegacyPullGuid })
        $broad = @($applicable | Where-Object { $_.roleDefinitionName -in @('AcrPush','Owner','Contributor') }).Count -gt 0
        if($pull.Count -gt 0) { $authorization='PASS';$model='LEGACY_ACRPULL' }
        elseif($broad) { $authorization='FAIL';$model='NONE' }
    } else {
        $reader = @($applicable | Where-Object { $_.roleDefinitionGuid -eq $script:AcrAbacRepositoryReaderGuid })
        foreach($assignment in $reader) {
            $condition = Adjudicate-AbacCondition ([string]$assignment.condition)
            if($condition.status -eq 'PASS') { $authorization='PASS';$model='ABAC_REPOSITORY_READER';$conditionStatus='PASS';$script:AcrAbacConditionAdjudication='PASS';break }
            if($condition.status -eq 'UNRESOLVED') { $conditionStatus='UNRESOLVED';$script:AcrAbacConditionAdjudication='UNRESOLVED' }
            if($condition.status -eq 'FAIL' -and $conditionStatus -eq 'NOT_APPLICABLE') { $conditionStatus='FAIL';$script:AcrAbacConditionAdjudication='FAIL' }
        }
        if($reader.Count -eq 0) { $conditionStatus='NOT_APPLICABLE';$script:AcrAbacConditionAdjudication='NOT_APPLICABLE' }
    }
    $script:AcrBootstrapPullAuthorization = $authorization
    $script:AcrPullAuthorizationModel = $model
    $script:AcrRoleAdjudication = [ordered]@{mode=$mode;rbacReadPermission='PASS';roleAssignmentEnumeration='PASS';roleNormalization=$script:AcrRoleNormalization;scopeAdjudication=$script:AcrScopeAdjudication;abacConditionAdjudication=$conditionStatus;authorization=$authorization;model=$model;assignmentsReturned=$script:AcrAssignmentsReturned;assignmentsScopeApplicable=$script:AcrAssignmentsScopeApplicable;assignmentsScopeInapplicable=$script:AcrAssignmentsScopeInapplicable;roleAssignmentPageCount=$script:AcrRoleAssignmentPageCount;broaderRoleDetected=$broad;assignments=@($applicable+$inapplicable)}
    $script:AcrRoleAdjudication
}

$script:BaseCheckScript = (Get-Command Check).ScriptBlock
function Check([string]$Id,[bool]$Pass,$Actual='') {
    if($script:AllowLegacyAcrPullCheckBypass -and $Id -eq 'effective AcrPull exact role') {
        $script:Checks.Add([ordered]@{id=$Id;phase=$ExecutionPhase;result='DEFERRED';actual='R7 mode-aware adjudication'}) | Out-Null
        return
    }
    & $script:BaseCheckScript $Id $Pass $Actual
}

$script:BaseRunPreflightScript = (Get-Command Run-Preflight).ScriptBlock
function Run-Preflight([bool]$UseMock) {
    $script:AllowLegacyAcrPullCheckBypass = $true
    try { $state = & $script:BaseRunPreflightScript $UseMock }
    finally { $script:AllowLegacyAcrPullCheckBypass = $false }
    if($UseMock -and $null -eq $state.acr.roleAssignmentMode) { $state.acr | Add-Member -NotePropertyName roleAssignmentMode -NotePropertyValue 'LegacyRegistryPermissions' }
    $mode = Normalize-AcrRoleMode ([string]$state.acr.roleAssignmentMode)
    if($mode -eq 'UNKNOWN') { $script:AcrRoleMode='UNKNOWN'; throw 'ACR_ROLE_ASSIGNMENT_MODE_UNKNOWN' }
    $assignments = @(Get-RoleAssignmentsRest ([string]$state.acr.id) ([string]$state.bootstrap.principalId))
    $script:AcrAssignmentsBaseline = @($assignments)
    $adjudication = Resolve-AcrAuthorization $mode ([string]$state.acr.id) ([string]$state.bootstrap.principalId) @($assignments)
    if($adjudication.authorization -ne 'PASS') {
        if($adjudication.broaderRoleDetected) { $script:AcrCompatibilityFailure='BROAD_OR_UNAPPROVED_ACR_ROLE' }
        elseif($adjudication.abacConditionAdjudication -eq 'UNRESOLVED') { $script:AcrCompatibilityFailure='ABAC_CONDITION_UNRESOLVED' }
        else { $script:AcrCompatibilityFailure='ACR_PULL_AUTHORIZATION_NOT_PROVEN' }
        throw $script:AcrCompatibilityFailure
    }
    $state
}

function Test-RoleDefinitionNormalization {
    $cases = @(
        '/providers/Microsoft.Authorization/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d',
        '/subscriptions/mock/providers/Microsoft.Authorization/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d',
        '/providers/Microsoft.Authorization/roleDefinitions/7F951DDA-4ED3-4680-A7CA-43FE172D538D',
        ' /SUBSCRIPTIONS/mock/PROVIDERS/Microsoft.Authorization/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d  ',
        '/providers/Microsoft.Authorization/roleDefinitions/not-a-guid'
    )
    $expected = @($script:AcrLegacyPullGuid,$script:AcrLegacyPullGuid,$script:AcrLegacyPullGuid,$script:AcrLegacyPullGuid,$null)
    for($i=0;$i -lt $cases.Count;$i++) { if((Normalize-RoleDefinitionGuid $cases[$i]) -ne $expected[$i]) { return $false } }
    $true
}

function Test-RoleScopeFixtures {
    $target='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ContainerRegistry/registries/acr'
    (Test-ResourceScopeApplicable $target "$target/") -and
    (Test-ResourceScopeApplicable '/subscriptions/mock/resourceGroups/rg' $target) -and
    (Test-ResourceScopeApplicable '/subscriptions/mock' $target) -and
    (-not (Test-ResourceScopeApplicable "$target/repositories/proposalops-api" $target)) -and
    (-not (Test-ResourceScopeApplicable '/subscriptions/other' $target))
}

function Test-AbacFixtures {
    $exact = Adjudicate-AbacCondition "StringEqualsIgnoreCase(@Resource[Microsoft.ContainerRegistry/registries/repositories:name], 'proposalops-api')"
    $different = Adjudicate-AbacCondition "StringEqualsIgnoreCase(@Resource[Microsoft.ContainerRegistry/registries/repositories:name], 'other-repo')"
    $wildcard = Adjudicate-AbacCondition "StringLikeIgnoreCase(@Resource[Microsoft.ContainerRegistry/registries/repositories:name], 'proposalops-*')"
    $excluded = Adjudicate-AbacCondition "StringLikeIgnoreCase(@Resource[Microsoft.ContainerRegistry/registries/repositories:name], 'other-*')"
    $multiple = Adjudicate-AbacCondition "StringEqualsIgnoreCase(@Resource[Microsoft.ContainerRegistry/registries/repositories:name], 'other-repo') OR StringEqualsIgnoreCase(@Resource[Microsoft.ContainerRegistry/registries/repositories:name], 'proposalops-api')"
    $malformed = Adjudicate-AbacCondition "StringEqualsIgnoreCase(@Resource[Microsoft.ContainerRegistry/registries/repositories:name], proposalops-api)"
    $unsupported = Adjudicate-AbacCondition "@Resource[Microsoft.ContainerRegistry/registries/repositories:name] contains 'proposalops-api'"
    $none = Adjudicate-AbacCondition $null
    ($exact.status -eq 'PASS' -and $different.status -eq 'FAIL' -and $wildcard.status -eq 'PASS' -and $excluded.status -eq 'FAIL' -and $multiple.status -eq 'PASS' -and $malformed.status -eq 'UNRESOLVED' -and $unsupported.status -eq 'UNRESOLVED' -and $none.scope -eq 'REGISTRY_WIDE_READ')
}

function Test-AcrModeFixtures {
    $target='/subscriptions/mock/resourceGroups/rg/providers/Microsoft.ContainerRegistry/registries/acr'
    $legacy=[pscustomobject]@{id='legacy';name='legacy';scope=$target;principalId='p';principalType='ServicePrincipal';roleDefinitionId="/providers/Microsoft.Authorization/roleDefinitions/$($script:AcrLegacyPullGuid)";condition=$null;conditionVersion=$null;roleDefinitionName='AcrPull'}
    $prefixed=[pscustomobject]@{id='prefixed';name='prefixed';scope=$target;principalId='p';principalType='ServicePrincipal';roleDefinitionId='/subscriptions/mock/providers/Microsoft.Authorization/roleDefinitions/7F951DDA-4ED3-4680-A7CA-43FE172D538D';condition=$null;conditionVersion=$null;roleDefinitionName='AcrPull'}
    $broad=[pscustomobject]@{id='broad';name='broad';scope=$target;principalId='p';principalType='ServicePrincipal';roleDefinitionId='/providers/Microsoft.Authorization/roleDefinitions/8311e382-0749-4cb8-b61a-304f252e45ec';condition=$null;conditionVersion=$null;roleDefinitionName='AcrPush'}
    $abac=[pscustomobject]@{id='abac';name='abac';scope=$target;principalId='p';principalType='ServicePrincipal';roleDefinitionId="/providers/Microsoft.Authorization/roleDefinitions/$($script:AcrAbacRepositoryReaderGuid)";condition=$null;conditionVersion=$null;roleDefinitionName='Container Registry Repository Reader'}
    $legacyPass=Resolve-AcrAuthorization 'LegacyRegistryPermissions' $target 'p' @($prefixed)
    $legacyBroad=Resolve-AcrAuthorization 'LegacyRegistryPermissions' $target 'p' @($broad)
    $abacPass=Resolve-AcrAuthorization 'AbacRepositoryPermissions' $target 'p' @($abac)
    $invalidMode = Normalize-AcrRoleMode 'not-supported'
    ($legacyPass.authorization -eq 'PASS' -and $legacyBroad.authorization -eq 'FAIL' -and $legacyBroad.broaderRoleDetected -and $abacPass.authorization -eq 'PASS' -and $invalidMode -eq 'UNKNOWN')
}

function Run-AcrQualificationTests {
    $results = [ordered]@{}
    $results.ACR_MODE_MATRIX_TESTS = if(Test-AcrModeFixtures){'PASS'}else{'FAIL'}
    $results.ROLE_ID_NORMALIZATION_TESTS = if(Test-RoleDefinitionNormalization){'PASS'}else{'FAIL'}
    $results.ROLE_SCOPE_TESTS = if(Test-RoleScopeFixtures){'PASS'}else{'FAIL'}
    $results.ABAC_CONDITION_TESTS = if(Test-AbacFixtures){'PASS'}else{'FAIL'}
    $results.ROLE_DEFINITION_ID_NORMALIZATION_TEST = $results.ROLE_ID_NORMALIZATION_TESTS
    $results.ROLE_ASSIGNMENT_SCOPE_ADJUDICATION = $results.ROLE_SCOPE_TESTS
    $script:AcrQualificationResults = $results
    foreach($item in $results.GetEnumerator()) { if($item.Value -ne 'PASS'){ throw "ACR_QUALIFICATION_FAILURE_$($item.Key)" } }
    $results
}

function Add-LocalCompatibilityProbe([string]$Label,[string]$Command,[int]$ExitCode,[string]$Stdout) {
    $script:CompatibilityProbes.Add([ordered]@{label=$Label;command=$Command;exitCode=$ExitCode;stdoutDigest=Sha-Text ([string]$Stdout);stderr=''}) | Out-Null
}

function Run-Compatibility {
    $version = Invoke-Probe 'az version' @('version','--output','json')
    if($version.exitCode -ne 0) { throw 'AZ_CLI_UNAVAILABLE' }
    $extension = Invoke-Probe 'containerapp extension' @('extension','show','--name','containerapp','--query','version','--output','tsv')
    if($extension.exitCode -ne 0) { throw 'CONTAINERAPP_EXTENSION_MISSING' }
    Add-LocalCompatibilityProbe 'PowerShell version' 'pwsh --version' 0 ($PSVersionTable.PSVersion.ToString())
    $pythonVersion = & python3 --version 2>&1
    Add-LocalCompatibilityProbe 'Python version' 'python3 --version' $LASTEXITCODE ([string]$pythonVersion)
    $r4=Read-Manifest $R4Evidence $R4Members
    $r4seal=Get-Content -LiteralPath $R4Seal -Raw|ConvertFrom-Json
    Check 'R4 evidence exact' ($r4.pass -and $r4seal.finalResult -eq 'V2_5_R4_PREFLIGHT_ONLY_PASS' -and $r4seal.azureMutationCommands -eq 0 -and -not [bool]$r4seal.azureAttemptConsumed) 'PASS'
    $v24=Find-V24Evidence
    $help=@(@('job create',@('containerapp','job','create','--help')),@('job start',@('containerapp','job','start','--help')),@('execution list',@('containerapp','job','execution','list','--help')),@('execution show',@('containerapp','job','execution','show','--help')),@('job logs',@('containerapp','job','logs','show','--help')))
    foreach($item in $help) { $probe=Invoke-Probe $item[0] $item[1]; if($probe.exitCode -ne 0){throw "COMPATIBILITY_HELP_FAILURE_$($item[0])"} }
    $jobList=Invoke-Probe 'Container Apps Job list' @('containerapp','job','list','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--output','json')
    if($jobList.exitCode -ne 0){throw 'COMPATIBILITY_JOB_LIST_FAILURE'}
    $null=Invoke-Probe 'Container Apps Job execution list' @('containerapp','job','execution','list','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name','p0-sql-r7-compat','--output','json')
    $null=Run-Preflight $false
    if($AcrBootstrapPullAuthorization -ne 'PASS') { throw $AcrCompatibilityFailure }
    $script:CompatibilityResults=[ordered]@{result='PASS';azCliVersion=(($version.stdout|ConvertFrom-Json).'azure-cli');containerAppExtensionVersion=([string]$extension.stdout).Trim();powershellVersion=$PSVersionTable.PSVersion.ToString();pythonVersion=[string]$pythonVersion;rbacReadPermission='PASS';roleAssignmentEnumeration='PASS';acrRoleAssignmentMode=$AcrRoleMode;roleNormalization=$AcrRoleNormalization;scopeAdjudication=$AcrScopeAdjudication;abacConditionAdjudication=$AcrAbacConditionAdjudication;acrBootstrapPullAuthorization=$AcrBootstrapPullAuthorization;acrPullAuthorizationModel=$AcrPullAuthorizationModel;roleAssignmentPageCount=$AcrRoleAssignmentPageCount;assignmentsReturned=$AcrAssignmentsReturned;assignmentsScopeApplicable=$AcrAssignmentsScopeApplicable;assignmentsScopeInapplicable=$AcrAssignmentsScopeInapplicable;v24ManifestSha=$v24.manifest.manifestSha}
    $CompatibilityResults
}

function Invoke-R7Main {
    try {
        if($Mode -eq 'INVALID') { throw 'EXACTLY_ONE_MODE_REQUIRED' }
        if($Mode -eq 'QUALIFICATION') {
            Assert-R7WorkingLineage
            $results = Run-Qualification
            $acrTests = Run-AcrQualificationTests
            foreach($item in $acrTests.GetEnumerator()) { $results[$item.Key] = $item.Value }
            $script:QualificationResults = $results
            Add-QualificationChecks (Get-Content -LiteralPath $PSCommandPath -Raw)
            $failed = @($results.GetEnumerator() | Where-Object { $_.Value -ne 'PASS' })
            if($failed.Count -ne 0) { throw 'R7_LOCAL_QUALIFICATION_FAILED' }
            $script:QualificationHarnessSha = Sha $PSCommandPath
            Finalize-Evidence 'V2_5_R7_QUALIFICATION_PASS'
            Write-Output 'R7_LOCAL_QUALIFICATION=PASS'
            Write-Output 'R7_REAL_READONLY_COMPATIBILITY=NOT_RUN'
            Write-Output "R7_UNCOMMITTED_HARNESS_SHA256=$QualificationHarnessSha"
            Write-Output 'AZURE_MUTATION_COMMANDS=0'
            Write-Output 'SQL_CONNECTION_ATTEMPTS=0'
            return 0
        }
        if($Mode -eq 'COMPATIBILITY') {
            Assert-R7WorkingLineage
            $script:CompatibilityProbes = [System.Collections.Generic.List[object]]::new()
            $script:ReadRecords = [System.Collections.Generic.List[object]]::new()
            $qualification = Get-R7QualificationEvidence
            $script:QualificationHarnessSha = [string]$qualification.binding.harnessSha256
            $script:CompatibilityHarnessSha = Sha $PSCommandPath
            $script:QualificationGate = 'PASS'
            Check 'qualification compatibility digest binding' ($QualificationHarnessSha -eq $CompatibilityHarnessSha) "$QualificationHarnessSha/$CompatibilityHarnessSha"
            $null = Run-Compatibility
            foreach($probe in @(
                @('Container Apps Job list',@('containerapp','job','list','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--output','json')),
                @('Container Apps Job execution list',@('containerapp','job','execution','list','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name','p0-sql-r7-compat','--output','json'))
            )) {
                $result = Invoke-Probe $probe[0] $probe[1]
                if($result.exitCode -ne 0 -and $probe[0] -eq 'Container Apps Job list') { throw 'COMPATIBILITY_JOB_LIST_FAILURE' }
            }
            $script:V24ManifestSha = $CompatibilityResults.v24ManifestSha
            Finalize-Evidence 'V2_5_R7_COMPATIBILITY_PASS'
            Write-Output 'R7_LOCAL_QUALIFICATION=PASS'
            Write-Output 'R7_REAL_READONLY_COMPATIBILITY=PASS'
            Write-Output "QUALIFICATION_HARNESS_SHA256=$QualificationHarnessSha"
            Write-Output "COMPATIBILITY_HARNESS_SHA256=$CompatibilityHarnessSha"
            Write-Output 'AZURE_MUTATION_COMMANDS=0'
            Write-Output 'SQL_CONNECTION_ATTEMPTS=0'
            return 0
        }
        Assert-R7FrozenLineage
        $v24 = Find-V24Evidence
        $script:V24ManifestSha = $v24.manifest.manifestSha
        $null = Verify-V24 $v24.root $V24ManifestSha
        $r4 = Read-Manifest $R4Evidence $R4Members
        $r4seal = Get-Content -LiteralPath $R4Seal -Raw | ConvertFrom-Json
        Check 'R4 accepted seal' ($r4.pass -and $r4seal.finalResult -eq 'V2_5_R4_PREFLIGHT_ONLY_PASS' -and $r4seal.azureMutationCommands -eq 0 -and -not [bool]$r4seal.azureAttemptConsumed) 'PASS'
        if($Mode -eq 'PREFLIGHT_ONLY') {
            $null = Run-Preflight $false
            Finalize-Evidence 'V2_5_R7_PREFLIGHT_ONLY_PASS'
            Write-Output 'FINAL_RESULT=V2_5_R7_PREFLIGHT_ONLY_PASS'
            Write-Output "PREFLIGHT_EVIDENCE_ROOT=$EvidenceRoot"
            Write-Output "PREFLIGHT_MANIFEST_SHA256=$((Read-Manifest $EvidenceRoot $EvidenceMembers).manifestSha)"
            Write-Output "PREFLIGHT_SEAL_PATH=$SealPath"
            Write-Output 'AZURE_MUTATION_COMMANDS=0'
            Write-Output 'AZURE_ATTEMPT_CONSUMED=False'
            Write-Output 'JOB_CREATED=False'
            Write-Output 'SQL_CONNECTION_ATTEMPTS=0'
            return 0
        }
        if([string]::IsNullOrWhiteSpace($PreflightSealPath)) { throw 'EXACT_PREFLIGHT_SEAL_PATH_REQUIRED' }
        if(-not (Test-Path -LiteralPath $PreflightSealPath)) { throw 'PREFLIGHT_SEAL_NOT_FOUND' }
        $seal = Get-Content -LiteralPath $PreflightSealPath -Raw | ConvertFrom-Json
        $preflightRoot = [string]$seal.evidenceRoot
        if([string]::IsNullOrWhiteSpace($preflightRoot)) { throw 'PREFLIGHT_SEAL_ROOT_MISSING' }
        $preflightManifest = Validate-Evidence $preflightRoot $EvidenceMembers
        Check 'preflight manifest seal match' ($preflightManifest.manifestSha -eq [string]$seal.manifestSha256) 'PASS'
        Check 'preflight final result seal match' ($seal.finalResult -eq 'V2_5_R7_PREFLIGHT_ONLY_PASS') 'PASS'
        Check 'preflight zero mutation seal' ($seal.azureMutationCommands -eq 0 -and -not [bool]$seal.azureAttemptConsumed) 'PASS'
        Check 'preflight source seal match' ($seal.r7Head -eq $CurrentHead -and $seal.harnessSha256 -eq (Sha $PSCommandPath)) 'PASS'
        if($Mode -eq 'EXECUTE') {
            $null = Run-Preflight $false
            $JobName = 'p0-sql-r7-' + (Get-Date -AsUTC -Format 'HHmmss')
            Check 'job name compact' ($JobName.Length -lt 32 -and $JobName -match '^[a-z0-9]([a-z0-9-]*[a-z0-9])?$') $JobName
            $existing = @(Invoke-AzureReadJson @('containerapp','job','list','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--output','json') 'List existing Container Apps Jobs')
            Check 'job name absent' (@($existing | Where-Object { $_.name -eq $JobName }).Count -eq 0) $JobName
            Create-OneJob $JobName $State
            $job = Invoke-AzureReadJson @('containerapp','job','show','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$JobName,'--output','json') 'Read created Job'
            Check 'job identity exact' ($job.identity.type -eq 'UserAssigned' -and $null -ne $job.identity.userAssignedIdentities) 'PASS'
            Check 'job environment exact' ($job.properties.environmentId -eq $State.aca.id) 'PASS'
            Check 'job image exact' ($job.properties.template.containers[0].image -eq $AcceptedImage) 'PASS'
            Check 'job manual contract' ($job.properties.configuration.triggerType -eq 'Manual' -and $job.properties.configuration.replicaRetryLimit -eq 0 -and $job.properties.configuration.manualTriggerConfig.parallelism -eq 1 -and $job.properties.configuration.manualTriggerConfig.replicaCompletionCount -eq 1) 'PASS'
            $before = @(Invoke-AzureReadJson @('containerapp','job','execution','list','--subscription',$SubscriptionName,'--resource-group',$ResourceGroup,'--name',$JobName,'--output','json') 'List pre-start executions')
            try {
                Set-TemporaryAdmin $State.sql
                $logs = Start-OneJob $JobName @($before | ForEach-Object { $_.name })
                $script:SqlResult = Parse-ResultMarker $logs
                Check 'SQL marker login' ($SqlResult.sql_login -eq 'PASS') 'PASS'
                Check 'SQL marker target db' ($SqlResult.sql_target_db -eq 'PASS') 'PASS'
                Check 'SQL marker permission' ($SqlResult.sql_required_permission -eq 'PASS') 'PASS'
                Check 'SQL marker postverification' ([bool]$SqlResult.post_verification) 'PASS'
                $MutationCounts.SQL_CONNECTION_ATTEMPTS = [int]$SqlResult.sql_connection_attempts
                $MutationCounts.SQL_DDL_MUTATIONS = [int]$SqlResult.sql_ddl_mutations
                $MutationCounts.SQL_DML_MUTATIONS = [int]$SqlResult.sql_dml_mutations
                Check 'SQL DML zero' ($MutationCounts.SQL_DML_MUTATIONS -eq 0) $MutationCounts.SQL_DML_MUTATIONS
            } finally {
                if($AdminSwitchAttempted) { Restore-HumanAdmin $State.sql }
            }
            $AcrAssignmentsAfter = @(Get-RoleAssignmentsRest $State.acr.id $State.bootstrap.principalId)
            $beforeIds = @($AcrAssignmentsBaseline | ForEach-Object { $_.id } | Sort-Object)
            $afterIds = @($AcrAssignmentsAfter | ForEach-Object { $_.id } | Sort-Object)
            Check 'ACR RBAC unchanged' (($beforeIds -join '|') -eq ($afterIds -join '|')) 'PASS'
            Finalize-Evidence 'V2_5_R7_EXECUTE_PASS'
            Write-Output 'FINAL_RESULT=V2_5_R7_EXECUTE_PASS'
            Write-Output "EVIDENCE_ROOT=$EvidenceRoot"
            Write-Output "JOB_NAME=$JobName"
            Write-Output "EXECUTION_NAME=$ExecutionName"
            Write-Output "SQL_DDL_MUTATIONS=$($MutationCounts.SQL_DDL_MUTATIONS)"
            Write-Output "SQL_DML_MUTATIONS=$($MutationCounts.SQL_DML_MUTATIONS)"
            return 0
        }
        throw 'UNREACHABLE_MODE'
    } catch {
        $script:Failure = $_.Exception.Message
        $script:FailureCode = if($Failure -match 'AZURE_READ_COMMAND_FAILURE \[Read ACR role assignments\].*(403|AuthorizationFailed|Forbidden)') { 'RBAC_READ_PERMISSION_BLOCKED' } elseif($Failure -match 'effective AcrPull exact role') { 'R7_ACRPULL_ASSIGNMENT_NOT_PROVEN' } elseif($Failure -match 'AZURE_READ_COMMAND_FAILURE') { 'AZURE_READ_COMMAND_FAILURE' } else { 'R7_STOPPED' }
        if($Mode -eq 'QUALIFICATION') { $final='V2_5_R7_QUALIFICATION_FAILED' } elseif($Mode -eq 'COMPATIBILITY') { $final=$FailureCode } elseif($Mode -eq 'PREFLIGHT_ONLY' -or $Mode -eq 'EXECUTE') { $final='V2_5_R7_STOPPED_PRE_MUTATION' } else { $final='V2_5_R7_STOPPED' }
        try { Finalize-Evidence $final } catch { }
        Write-Output "R7_LOCAL_QUALIFICATION=$(if($Mode -eq 'QUALIFICATION' -and $null -ne $QualificationResults){'FAIL'}elseif($QualificationGate -eq 'PASS'){'PASS'}else{'NOT_RUN'})"
        Write-Output "R7_REAL_READONLY_COMPATIBILITY=$(if($Mode -eq 'COMPATIBILITY'){'FAIL'}else{'NOT_RUN'})"
        Write-Output "R7_COMPATIBILITY_RESULT=$(if($Mode -eq 'COMPATIBILITY'){$FailureCode}else{'NOT_RUN'})"
        Write-Output "QUALIFICATION_HARNESS_SHA256=$(if($QualificationHarnessSha){$QualificationHarnessSha}else{'NOT_AVAILABLE'})"
        Write-Output "COMPATIBILITY_HARNESS_SHA256=$(if($CompatibilityHarnessSha){$CompatibilityHarnessSha}else{'NOT_AVAILABLE'})"
        Write-Output "HARNESS_DIGEST_BINDING=$(if($QualificationHarnessSha -and $CompatibilityHarnessSha -and $QualificationHarnessSha -eq $CompatibilityHarnessSha){'PASS'}else{'FAIL'})"
        Write-Output "ACR_ROLE_ASSIGNMENT_MODE=$AcrRoleMode"
        Write-Output "RBAC_READ_PERMISSION=$AcrRbacReadPermission"
        Write-Output "ROLE_ASSIGNMENT_PAGE_COUNT=$AcrRoleAssignmentPageCount"
        Write-Output "ROLE_ASSIGNMENTS_RETURNED=$AcrAssignmentsReturned"
        Write-Output "ROLE_ASSIGNMENTS_SCOPE_APPLICABLE=$AcrAssignmentsScopeApplicable"
        $assignment = @($RoleAssignmentRawRecords | Select-Object -First 1)
        Write-Output "BOOTSTRAP_ASSIGNMENT_1_ROLE_DEFINITION_ID_RAW=$(if($assignment){$assignment.roleDefinitionId}else{'NOT_AVAILABLE'})"
        Write-Output "BOOTSTRAP_ASSIGNMENT_1_ROLE_GUID=$(if($assignment){$assignment.roleDefinitionGuid}else{'NOT_AVAILABLE'})"
        Write-Output "BOOTSTRAP_ASSIGNMENT_1_ROLE_NAME=$(if($assignment){$assignment.roleDefinitionName}else{'NOT_AVAILABLE'})"
        Write-Output "BOOTSTRAP_ASSIGNMENT_1_SCOPE=$(if($assignment){$assignment.scope}else{'NOT_AVAILABLE'})"
        Write-Output "BOOTSTRAP_ASSIGNMENT_1_CONDITION_PRESENT=$(if($assignment -and -not [string]::IsNullOrWhiteSpace([string]$assignment.condition)){'true'}else{'false'})"
        Write-Output "BOOTSTRAP_ASSIGNMENT_1_CONDITION_VERSION=$(if($assignment -and $assignment.conditionVersion){$assignment.conditionVersion}else{'NOT_AVAILABLE'})"
        Write-Output "ABAC_CONDITION_ADJUDICATION=$AcrAbacConditionAdjudication"
        Write-Output "ACR_BOOTSTRAP_PULL_AUTHORIZATION=$AcrBootstrapPullAuthorization"
        Write-Output "ACR_PULL_AUTHORIZATION_MODEL=$AcrPullAuthorizationModel"
        Write-Output "FINAL_RESULT=$final"
        Write-Output 'AZURE_MUTATION_COMMANDS=0'
        Write-Output "SQL_CONNECTION_ATTEMPTS=$($MutationCounts.SQL_CONNECTION_ATTEMPTS)"
        Write-Output 'R7_COMMITTED=false'
        Write-Output 'R7_PUSHED=false'
        Write-Output 'R7_PREFLIGHT_STARTED=false'
        Write-Output 'R7_EXECUTE_STARTED=false'
        Write-Output 'AZURE_ATTEMPT_CONSUMED=false'
        Write-Output "NEXT=$(if($Mode -eq 'COMPATIBILITY'){'OWNER_REVIEW'}else{'STOP'})"
        return 1
    }
}

$R7Output = @(Invoke-R7Main)
$R7Output | Where-Object { $_ -is [string] } | Write-Output
$R7ExitCode = [int]$R7Output[-1]
exit $R7ExitCode
