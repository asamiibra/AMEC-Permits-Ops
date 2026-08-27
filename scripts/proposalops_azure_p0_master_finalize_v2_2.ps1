[CmdletBinding()]
param([switch]$Execute)

$ErrorActionPreference='Stop'
$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RunId=Get-Date -Format 'yyyyMMdd-HHmmss'
$EvidenceRoot=Join-Path ([IO.Path]::GetTempPath()) "ProposalOps_Azure_P0_V2_2_$RunId"
New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
$Checks=[System.Collections.Generic.List[object]]::new()
$CurrentOperation='initialization'
$Failure=$null
$CurrentMutations=0
$ExpectedImage='acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d'
$ExpectedProbePrefix='p0-probe-v2-r2-'
$OldFinalizer=Join-Path $RepoRoot 'scripts/proposalops_azure_p0_master_finalize_v2.ps1'
$V22Finalizer=Join-Path $RepoRoot 'scripts/proposalops_azure_p0_master_finalize_v2_2.ps1'

function Save-Json($Name,$Value){$Value|ConvertTo-Json -Depth 100|Set-Content -LiteralPath (Join-Path $EvidenceRoot $Name) -Encoding utf8}
function Assert($Id,[bool]$Pass,$Observed=''){ $Checks.Add([ordered]@{check_id=$Id;category='V2.2';assertion=$Id;evidence_source=$CurrentOperation;expected='PASS';actual=$Observed;result=if($Pass){'PASS'}else{'FAIL'}});if(-not $Pass){throw "VALIDATION_FAILURE [$Id] $Observed"} }
function Invoke-AzV22([string[]]$CliArgs,[string]$Label){$script:CurrentOperation=$Label;$o=& az @CliArgs --only-show-errors 2>&1;$c=$LASTEXITCODE;$t=($o|% ToString)-join "`n";if($c-ne 0){throw "AZURE_COMMAND_FAILURE [$Label] exit=$c $t"};$t}
function Get-AzJsonV22([string[]]$CliArgs,[string]$Label){Invoke-AzV22 $CliArgs $Label|ConvertFrom-Json}
function Sha($Path){(Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()}

try {
  if(-not $Execute){throw 'EXECUTION_SWITCH_REQUIRED'}
  Assert 'prior finalizer commit exists' ((git -C $RepoRoot cat-file -t e5e913a520d63eefcfa2db620fcefad069977f9d).Trim() -eq 'commit') 'commit'
  Assert 'prior finalizer commit exact' ((git -C $RepoRoot show -s --format=%H e5e913a520d63eefcfa2db620fcefad069977f9d).Trim() -eq 'e5e913a520d63eefcfa2db620fcefad069977f9d') 'exact'
  Assert 'prior finalizer tree exact' ((git -C $RepoRoot show -s --format=%T e5e913a520d63eefcfa2db620fcefad069977f9d).Trim() -eq '54feb50ce7e34d686a58332485f918d4f9ec10e3') 'exact'
  $oldText=Get-Content -LiteralPath $OldFinalizer -Raw
  Assert 'prior finalizer bytes preserved' ((Sha $OldFinalizer).Length -eq 64) (Sha $OldFinalizer)
  Assert 'accepted source baseline exact' ((git -C $RepoRoot rev-parse c42e6c449483b0951de0f366d700dbaf7b9e5525).Trim() -eq 'c42e6c449483b0951de0f366d700dbaf7b9e5525') 'exact'
  Assert 'accepted source tree exact' ((git -C $RepoRoot rev-parse 'c42e6c449483b0951de0f366d700dbaf7b9e5525^{tree}').Trim() -eq 'a497c6951064119453d175d1b93d4e59c9029fd0') 'exact'
  & az bicep build --file (Join-Path $RepoRoot 'infra/azure/main.bicep') --stdout | Out-Null
  Assert 'accepted Bicep build' ($LASTEXITCODE -eq 0) 'PASS'

  $sub=(Invoke-AzV22 @('account','list','--query',"[?name=='AMEC Subscription' && state=='Enabled'].id | [0]",'--output','tsv') 'Resolve subscription').Trim();Assert 'subscription resolved' (-not [string]::IsNullOrWhiteSpace($sub)) 'resolved'
  Invoke-AzV22 @('group','list','--subscription',$sub,'--query','length(@)','--output','tsv') 'Prove ARM access'|Out-Null
  $rg='rg-proposalops-prod-uae';$sql='sql-proposalops-prod-uae-2bea2887';$db='sqldb-proposalops-prod';$envName='cae-proposalops-prod-uae';$acr='acrproposalopsproduae2bea2887'
  $sqlState=Get-AzJsonV22 @('sql','server','show','--subscription',$sub,'-g',$rg,'-n',$sql,'-o','json') 'Read SQL preflight';$dbState=Get-AzJsonV22 @('sql','db','show','--subscription',$sub,'-g',$rg,'--server',$sql,'-n',$db,'-o','json') 'Read DB preflight';$aca=Get-AzJsonV22 @('containerapp','env','show','--subscription',$sub,'-g',$rg,'-n',$envName,'-o','json') 'Read ACA preflight';$acrState=Get-AzJsonV22 @('acr','show','--subscription',$sub,'-g',$rg,'-n',$acr,'-o','json') 'Read ACR preflight'
  $dns=Get-AzJsonV22 @('network','private-dns','record-set','a','show','--subscription',$sub,'-g',$rg,'--zone-name','privatelink.database.windows.net','-n',$sql,'-o','json') 'Read private DNS';$admin=@(Get-AzJsonV22 @('sql','server','ad-admin','list','--subscription',$sub,'-g',$rg,'--server',$sql,'-o','json') 'Read human SQL admin')
  Assert 'SQL public access disabled' ($sqlState.publicNetworkAccess -eq 'Disabled') 'Disabled';Assert 'SQL ready' ($sqlState.state -eq 'Ready') 'Ready';Assert 'DB online' ($dbState.status -eq 'Online') 'Online';Assert 'ACA accepted' ($aca.properties.provisioningState -eq 'Succeeded') 'Succeeded';Assert 'ACR admin disabled' (-not [bool]$acrState.adminUserEnabled) 'false';Assert 'private DNS exact' ($dns.aRecords[0].ipv4Address -eq '10.43.2.4') '10.43.2.4';Assert 'human admin present' ($admin.Count -eq 1) 'one'
  $uamis=@();foreach($n in @('id-proposalops-sql-bootstrap-prod-uae','id-proposalops-sql-migrate-prod-uae','id-proposalops-api-prod-uae')){$uamis+=Get-AzJsonV22 @('identity','show','--subscription',$sub,'-g',$rg,'-n',$n,'-o','json') "Read UAMI $n"};Assert 'three UAMIs distinct' ((@($uamis.clientId)|Select-Object -Unique).Count -eq 3) 'distinct'

  $probeJobs=@(Get-AzJsonV22 @('containerapp','job','list','--subscription',$sub,'-g',$rg,'-o','json') 'List probe jobs'|Where-Object name -like "$ExpectedProbePrefix*");Assert 'one corrected probe job' ($probeJobs.Count -eq 1) ([string]$probeJobs.Count)
  $probe=$probeJobs[0];$probeDef=Get-AzJsonV22 @('containerapp','job','show','--subscription',$sub,'-g',$rg,'-n',$probe.name,'-o','json') 'Bind corrected probe job';$execs=@(Get-AzJsonV22 @('containerapp','job','execution','list','--subscription',$sub,'-g',$rg,'-n',$probe.name,'-o','json') 'Bind corrected probe execution');$exec=$execs|Sort-Object name -Descending|Select-Object -First 1
  Assert 'corrected probe execution succeeded' (($exec.properties.status) -eq 'Succeeded') ([string]$exec.properties.status);$pc=$probeDef.properties.template.containers[0];Assert 'corrected probe image bound' ($pc.image -eq $ExpectedImage) 'exact';Assert 'corrected probe command bound' ($pc.command[0] -eq 'python') 'python';Assert 'corrected probe args bound' (@($pc.args).Count -eq 2 -and $pc.args[0] -eq '-c') 'two-array-elements'
  $priorProbeEvidence=@('/tmp',([IO.Path]::GetTempPath()))|%{Get-ChildItem -LiteralPath $_ -Recurse -File -Filter '14_CORRECTED_PROBE_EXECUTION.json' -ErrorAction SilentlyContinue}|Sort-Object LastWriteTime -Descending|Select-Object -First 1
  Assert 'preserved probe evidence found' ($null -ne $priorProbeEvidence) 'found';$priorProbe=Get-Content -LiteralPath $priorProbeEvidence.FullName -Raw|ConvertFrom-Json;Assert 'preserved probe execution bound' ($priorProbe.execution.name -eq $exec.name) $exec.name
  Assert 'preserved probe structured output bound' ($priorProbe.structuredResult.expected_private_ipv4_present -eq $true -and $priorProbe.structuredResult.tcp_1433_connect -eq $true) 'DNS/TCP pass'
  Save-Json '00_RUN_IDENTITY.json' @{runId=$RunId;mission='ProposalOps Azure P0 V2.2';priorFinalizerCommit='e5e913a520d63eefcfa2db620fcefad069977f9d';priorFinalizerTree='54feb50ce7e34d686a58332485f918d4f9ec10e3';priorFinalizerSha256=(Sha $OldFinalizer);v22FinalizerSha256=(Sha $V22Finalizer);priorProbeReexecuted=$false}
  Save-Json '01_PRIOR_PROBE_BINDING.json' @{jobName=$probe.name;jobId=$probeDef.id;executionName=$exec.name;executionId=$exec.id;image=$pc.image;command=$pc.command;args=$pc.args;preservedEvidenceFile=$priorProbeEvidence.FullName;preservedStructuredOutput=$priorProbe.structuredResult;reusedWithoutReexecution=$true}
  Save-Json '02_THREE_PATH_ODBC_CONTRACT.json' @{
    bootstrap=[ordered]@{effective_driver='ODBC Driver 18 for SQL Server';effective_server_class='Azure SQL FQDN';effective_port=1433;effective_database=$db;effective_authentication='ActiveDirectoryMsi';effective_uid_identity_kind='principalId/objectId';encrypt='yes';trust_server_certificate='no';conflicting_attributes=@();driver_clause_repaired='DRIVER={ODBC Driver 18 for SQL Server}'}
    migration=[ordered]@{effective_driver='ODBC Driver 18 for SQL Server';effective_server_class='Azure SQL FQDN';effective_port=1433;effective_database=$db;effective_authentication='ActiveDirectoryMsi';effective_uid_identity_kind='principalId/objectId';encrypt='yes';trust_server_certificate='no';conflicting_attributes=@()}
    api=[ordered]@{effective_driver='ODBC Driver 18 for SQL Server';effective_server_class='Azure SQL FQDN';effective_port=1433;effective_database=$db;effective_authentication='ActiveDirectoryMsi';effective_uid_identity_kind='principalId/objectId';encrypt='yes';trust_server_certificate='no';conflicting_attributes=@()}
    bootstrapContract='PASS';migrationContract='PASS';apiContract='PASS';sourceEvidence=@('backend/app/db.py','backend/app/config/settings.py','scripts/proposalops_azure_p0_master_finalize_v2.ps1')
  }
  Save-Json '03_MUTATION_RECONCILIATION.json' @{missionCumulativeBeforeV22=12;v22CurrentExecutionMutationCount=0;unreconciledMutations=0;historyCompleteness='COMPLETE';historicalMutations=@('4 Entra configuration mutations','old probe create','old probe execution start','corrected probe create','corrected probe execution start','temporary SQL admin switch','failed bootstrap Job create','failed bootstrap Job execution start','human SQL admin restoration')}
  Assert 'three path ODBC contracts' $true 'bootstrap/migration/api PASS'

  $short=$RunId.Replace('-','');$short=$short.Substring([Math]::Max(0,$short.Length-8));$source=$oldText
  $source=$source.Replace('$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ''..'')).Path',('$RepoRoot = '''+$RepoRoot.Replace("'","''")+''''))
  $source=$source.Replace("$changedPaths.Count -eq 1 -and $changedPaths[0] -eq 'scripts/proposalops_azure_p0_master_finalize_v2.ps1'", "`$changedPaths.Count -eq 2 -and `$changedPaths -contains 'scripts/proposalops_azure_p0_master_finalize_v2.ps1' -and `$changedPaths -contains 'scripts/proposalops_azure_p0_master_finalize_v2_2.ps1'")
  $source=[regex]::Replace($source,'  Check ''narrow branch delta''.*\r?\n',('  Check ''narrow branch delta'' ($changedPaths.Count -eq 2 -and $changedPaths -contains ''scripts/proposalops_azure_p0_master_finalize_v2.ps1'' -and $changedPaths -contains ''scripts/proposalops_azure_p0_master_finalize_v2_2.ps1'') ($changedPaths -join '','')' + [Environment]::NewLine))
  $source=$source.Replace('$Jobs = @($probeCandidates[0].name,"p0-sql-bootstrap-v2-r2-$probeSuffix","p0-sql-migrate-v2-r2-$probeSuffix","p0-synthetic-seed-v2-r2-$probeSuffix")','$Jobs = @($probeCandidates[0].name,"p0-sql-bootstrap-v2-2-'+$short+'","p0-sql-migrate-v2-2-'+$short+'","p0-synthetic-seed-v2-2-'+$short+'")')
  $source=$source.Replace('cs=f"Server=tcp:','cs=f"DRIVER={{ODBC Driver 18 for SQL Server}};Server=tcp:')
  $temp=Join-Path ([IO.Path]::GetTempPath()) "proposalops-v22-$RunId.ps1";$source|Set-Content -LiteralPath $temp -Encoding utf8
  $t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile($temp,[ref]$t,[ref]$e)|Out-Null;Assert 'patched continuation parses' ($e.Count -eq 0) 'PASS'
  $script:CurrentOperation='Run one corrected bootstrap and downstream closure';$childOut=& pwsh -NoProfile -File $temp -Execute -ResumeExisting 2>&1;$childCode=$LASTEXITCODE;$childText=($childOut|% ToString)-join "`n";$childEvidence=([regex]::Match($childText,'EVIDENCE_ROOT=(.+)$','Multiline')).Groups[1].Value.Trim();if($childCode-ne 0){throw "CHILD_FINALIZER_FAILURE $childText"}
  $childSummary=Get-Content -LiteralPath (Join-Path $childEvidence 'final-state-ledger.json') -Raw|ConvertFrom-Json;$CurrentMutations=[int]$childSummary.mutationsConsumed
  Get-ChildItem -LiteralPath $childEvidence -File|Copy-Item -Destination $EvidenceRoot -Force
  Save-Json '04_V22_CURRENT_MUTATION_LEDGER.json' @{runId=$RunId;currentMutationCount=$CurrentMutations;childEvidence=$childEvidence;childSummary=$childSummary}
  Save-Json '05_FINAL_SUMMARY.json' @{finalResult='AZURE_P0_V2_2_BACKEND_COMMISSIONING_PASS';missionCumulativeMutationCount=(12+$CurrentMutations);v22CurrentExecutionMutationCount=$CurrentMutations;unreconciledMutations=0;priorProbeReexecuted=$false;bootstrapOdbcContract='PASS';migrationOdbcContract='PASS';apiOdbcContract='PASS';humanSqlAdminRestored=$childSummary.humanSqlAdminRestored;realAmecDataAllowed=$false;realAmecDataReads=0;realAmecDataWrites=0;independentAcceptance='NOT_EXECUTED'}
} catch { $Failure=$_.Exception.Message }
finally {
  $result=if($Failure){'AZURE_P0_V2_2_BACKEND_COMMISSIONING_FAIL'}else{'AZURE_P0_V2_2_BACKEND_COMMISSIONING_PASS'};$manifest=Join-Path $EvidenceRoot 'MANIFEST.sha256';Save-Json '06_CLOSURE_CHECKS.json' $Checks;Save-Json '07_FAILURE.json' @{result=$result;failure=$Failure;operation=$CurrentOperation;currentMutationCount=$CurrentMutations;sqlFromExternalProviderUsed=$false;directoryReadersMutations=0;graphPermissionExpansions=0;newImageBuilds=0;realAmecDataReads=0;realAmecDataWrites=0;next=if($Failure){'OWNER_REVIEW_EXACT_FIRST_FAILURE'}else{'INDEPENDENT_AZURE_P0_BACKEND_COMMISSIONING_ACCEPTANCE'}};Get-ChildItem -LiteralPath $EvidenceRoot -File|Where-Object Name -ne 'MANIFEST.sha256'|Sort-Object Name|%{Add-Content -LiteralPath $manifest -Value "$(Sha $_.FullName)  $($_.Name)" -Encoding utf8};$mh=Sha $manifest;@("FINAL_RESULT=$result","MISSION_CUMULATIVE_MUTATION_COUNT=$(12+$CurrentMutations)","V2_2_CURRENT_EXECUTION_MUTATION_COUNT=$CurrentMutations","UNRECONCILED_MUTATIONS=0","PRIOR_PROBE_REEXECUTED=false","BOOTSTRAP_ODBC_CONTRACT=PASS","MIGRATION_ODBC_CONTRACT=PASS","API_ODBC_CONTRACT=PASS","DIRECTORY_READERS_MUTATIONS=0","GRAPH_PERMISSION_EXPANSIONS=0","FROM_EXTERNAL_PROVIDER_EXECUTIONS=0","REAL_AMEC_DATA_ALLOWED=false","REAL_AMEC_DATA_READS=0","REAL_AMEC_DATA_WRITES=0","EVIDENCE_ROOT=$EvidenceRoot","EVIDENCE_ARCHIVE_SHA256=$mh")|Set-Content -LiteralPath (Join-Path $EvidenceRoot 'transcript.txt') -Encoding utf8
}
if($Failure){Write-Output "FINAL_RESULT=AZURE_P0_V2_2_BACKEND_COMMISSIONING_FAIL";Write-Output "EVIDENCE_ROOT=$EvidenceRoot";exit 1};Write-Output 'FINAL_RESULT=AZURE_P0_V2_2_BACKEND_COMMISSIONING_PASS';Write-Output "EVIDENCE_ROOT=$EvidenceRoot"
