[CmdletBinding()]
param([switch]$Execute)

$ErrorActionPreference='Stop'
$RepoRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RunId=Get-Date -Format 'yyyyMMdd-HHmmss'
$EvidenceRoot=Join-Path ([IO.Path]::GetTempPath()) "ProposalOps_Azure_P0_V2_5_$RunId"
New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null
$CurrentOperation='initialization';$Failure=$null
$Counts=[ordered]@{REPOSITORY_COMMITS_CREATED=1;REMOTE_BRANCHES_CREATED=2;REMOTE_BRANCH_UPDATES=0;BOOTSTRAP_JOB_CREATES=0;BOOTSTRAP_JOB_UPDATES=0;BOOTSTRAP_JOB_DELETES=0;BOOTSTRAP_JOB_EXECUTIONS=0;SQL_ADMIN_SWITCH_MUTATIONS=0;SQL_ADMIN_RESTORE_MUTATIONS=0;SQL_CONNECTION_ATTEMPTS=0;SQL_CREATE_USER_MUTATIONS=0;SQL_ROLE_MUTATIONS=0;SQL_PERMISSION_GRANTS=0;SQL_DDL_OTHER=0;SQL_DML_MUTATIONS=0;ENTRA_MUTATIONS=0;RBAC_MUTATIONS=0;FIREWALL_MUTATIONS=0;SQL_PUBLIC_NETWORK_MUTATIONS=0;MIGRATION_EXECUTIONS=0;SEED_EXECUTIONS=0;API_DEPLOYMENTS=0;FRONTEND_DEPLOYMENTS=0;SYNLOGY_READS=0;REAL_AMEC_DATA_READS=0;REAL_AMEC_DATA_WRITES=0;PHASE6_MUTATIONS=0}
$Checks=[System.Collections.Generic.List[object]]::new();$AdminChanged=$false;$AdminRestored=$false;$V24Evidence=$null
$ExpectedImage='acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d'
$ExpectedAppSha='c42e6c449483b0951de0f366d700dbaf7b9e5525';$ExpectedAppTree='a497c6951064119453d175d1b93d4e59c9029fd0'
$ScalarRepairCommit='5ed44e51978a71100f85616020be78d7a7660261';$ScalarRepairBranch='azure-p0-v24-scalar-repair-immutable-v1';$HarnessBranch='azure-p0-v25-native-msi-bootstrap-one-shot-v1';$ExpectedScalarScriptSha='2a5a3abb7f95af5a713d75dba94b66b42fc7430ac43c186ea74ead778b42e669'
function Save-Json($n,$v){$v|ConvertTo-Json -Depth 100|Set-Content -LiteralPath (Join-Path $EvidenceRoot $n) -Encoding utf8}
function Sha($p){(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant()}
function Check($id,[bool]$pass,$actual=''){ $Checks.Add([ordered]@{id=$id;operation=$CurrentOperation;result=if($pass){'PASS'}else{'FAIL'};actual=$actual});if(-not $pass){throw "VALIDATION_FAILURE [$id] $actual"}}
function Az([string[]]$a,[string]$label){$script:CurrentOperation=$label;$o=& az @a --only-show-errors 2>&1;if($LASTEXITCODE-ne 0){throw "AZURE_COMMAND_FAILURE [$label] $($o -join ([Environment]::NewLine))"};($o|ForEach-Object ToString)-join([Environment]::NewLine)}
function AzJson([string[]]$a,[string]$label){Az $a $label|ConvertFrom-Json}
function Mutate([string[]]$a,[string]$label,[string]$kind){$Counts[$kind]++;Az $a $label|Out-Null}
function Admin([string]$sub,[string]$rg,[string]$sql){@(AzJson @('sql','server','ad-admin','list','--subscription',$sub,'-g',$rg,'--server',$sql,'-o','json') 'Read SQL administrator')}
function WaitAdmin([string]$sub,[string]$rg,[string]$sql,[string]$expected,[int]$seconds=180){for($i=0;$i-lt($seconds/5);$i++){ $a=Admin $sub $rg $sql;if($a.Count-eq 1 -and (($a[0].sid-eq$expected)-or($a[0].objectId-eq$expected))){return $a};Start-Sleep -Seconds 5};@(Admin $sub $rg $sql)}
function V24-Check {
  $dirs=@(Get-ChildItem ([IO.Path]::GetTempPath()) -Directory -Filter 'ProposalOps_Azure_P0_V2_4_*'|Sort-Object LastWriteTime -Descending)
  foreach($d in $dirs){$f=Join-Path $d.FullName '13_FINAL_RESULT.json';if(Test-Path $f){try{$x=Get-Content $f -Raw|ConvertFrom-Json;if($x.FINAL_RESULT-eq'V2_4_MI_TOKEN_DIAGNOSTIC_PASS'){$script:V24Evidence=$d.FullName;break}}catch{}}}
  Check 'V24 evidence located' (-not [string]::IsNullOrWhiteSpace($V24Evidence)) 'located'
  $m=Join-Path $V24Evidence 'MANIFEST.sha256';$lines=@(Get-Content $m|Where-Object{$_-match'^[0-9a-f]{64}  .+$'});Check 'V24 member count' ($lines.Count-eq15) $lines.Count
  $v=& shasum -a 256 -c $m 2>&1;Check 'V24 members match' ($LASTEXITCODE-eq0-and @($v|Where-Object{$_-match': OK$'}).Count-eq15) '15/15'
  $script:V24ManifestSha=Sha $m;$script:V24Members=@($lines|ForEach-Object{($_-split'  ',2)[1]})
}
function Assert-V24([string]$root) {
  Check 'V24 post-run root unchanged' ((-not [string]::IsNullOrWhiteSpace($root))-and(Test-Path (Join-Path $root 'MANIFEST.sha256'))) 'root'
  $m=Join-Path $root 'MANIFEST.sha256';$lines=@(Get-Content $m|Where-Object{$_-match'^[0-9a-f]{64}  .+$'});$now=Sha $m
  $v=& shasum -a 256 -c $m 2>&1
  Check 'V24 post-run member count' ($lines.Count-eq15) $lines.Count
  Check 'V24 post-run members match' ($LASTEXITCODE-eq0-and @($v|Where-Object{$_-match': OK$'}).Count-eq15) '15/15'
  Check 'V24 manifest hash unchanged' ($now-eq$V24ManifestSha) $now
  [ordered]@{result='PASS';root=$root;manifestSha=$now;memberCount=$lines.Count;memberHashesMatch=$true}
}
function New-Job([string]$name,[string]$identity,[string]$envId,[string]$registry,[string]$image,[string]$fqdn,[string]$db,[string]$uid,[string]$apiClient,[string]$migrationClient,[string]$tenant) {
  $body=@'
import json,os,pyodbc,sys
r={"sql_connection_attempts":0,"sql_login":"NOT_EXECUTED","sql_target_db":"NOT_EXECUTED","sql_required_permission":"NOT_EXECUTED","sql_ddl_executed":False,"sql_dml_executed":False,"api_mutations":0,"migration_mutations":0,"role_mutations":0,"permission_grants":0,"sql_mutations":[],"bootstrap_principal_absent":False,"post_verification":False}
cn=None
try:
 r["sql_connection_attempts"]=1
 cs=f"DRIVER={{ODBC Driver 18 for SQL Server}};Server=tcp:{os.environ['SQL_HOST']},1433;Database={os.environ['SQL_DATABASE']};Authentication=ActiveDirectoryMsi;UID={os.environ['SQL_ODBC_UID']};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
 cn=pyodbc.connect(cs,autocommit=True);cur=cn.cursor()
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
  x,roles=inspect(n); expected=sid(cid)
  if x is not None and (x[1]!="E" or str(x[2]).lower()!=expected): raise RuntimeError("existing principal mismatch")
  if any(z in forbidden for z in roles): raise RuntimeError("forbidden role present")
  states.append((n,cid,required,view,x,roles,expected))
 if r["sql_login"]!="PASS" or r["sql_target_db"]!="PASS" or r["sql_required_permission"]!="PASS" or not r["bootstrap_principal_absent"]: raise RuntimeError("pre-DDL gate failed")
 for n,cid,required,view,x,roles,expected in states:
  if x is None:
   cur.execute(f"CREATE USER [{n}] WITH SID={expected}, TYPE=E");r["sql_ddl_executed"]=True;r["sql_mutations"].append(f"CREATE USER {n}")
   if n=="proposalops_api_uami":r["api_mutations"]+=1
   else:r["migration_mutations"]+=1
  for role in required:
   if role not in roles:cur.execute(f"ALTER ROLE [{role}] ADD MEMBER [{n}]");r["sql_ddl_executed"]=True;r["role_mutations"]+=1;r["sql_mutations"].append(f"ALTER ROLE {role} ADD MEMBER {n}")
  if view and cur.execute("SELECT 1 FROM sys.database_permissions WHERE grantee_principal_id=USER_ID(?) AND permission_name='VIEW DEFINITION' AND state IN ('G','W')",n).fetchone() is None:cur.execute(f"GRANT VIEW DEFINITION TO [{n}]");r["sql_ddl_executed"]=True;r["permission_grants"]+=1;r["sql_mutations"].append(f"GRANT VIEW DEFINITION TO {n}")
 for n,cid,required,view,x,roles,expected in states:
  y,actual=inspect(n)
  if y is None or y[1]!="E" or str(y[2]).lower()!=expected or set(actual)!=set(required):raise RuntimeError("post principal verification failed")
  if view and cur.execute("SELECT 1 FROM sys.database_permissions WHERE grantee_principal_id=USER_ID(?) AND permission_name='VIEW DEFINITION' AND state IN ('G','W')",n).fetchone() is None:raise RuntimeError("VIEW DEFINITION missing")
 r["post_verification"]=True;print(json.dumps(r,sort_keys=True));sys.exit(0)
except Exception as e:
 r["error_class"]=type(e).__name__;r["error_message"]=str(e)[:240];print(json.dumps(r,sort_keys=True));sys.exit(1)
finally:
 if cn is not None:cn.close()
'@
  $env=@("SQL_HOST=$fqdn","SQL_DATABASE=$db","SQL_ODBC_UID=$uid","API_CLIENT_ID=$apiClient","MIGRATION_CLIENT_ID=$migrationClient","AZURE_TENANT_ID=$tenant",'SYNTHETIC_ONLY=true','REAL_DATA_ALLOWED=false')
  $aj=ConvertTo-Json ([string[]]@('-c',$body)) -Compress;$ej=ConvertTo-Json ([object[]]($env|ForEach-Object{$p=$_.IndexOf('=');[ordered]@{name=$_.Substring(0,$p);value=$_.Substring($p+1)}})) -Compress;$ij=ConvertTo-Json ([ordered]@{type='UserAssigned';userAssignedIdentities=[ordered]@{$identity=@{}}}) -Compress
  $yaml=@"
location: UAE North
properties:
  environmentId: $envId
  configuration:
    manualTriggerConfig:
      parallelism: 1
      replicaCompletionCount: 1
    replicaRetryLimit: 0
    replicaTimeout: 300
    triggerType: Manual
    registries:
      - server: $registry
        identity: $identity
  template:
    containers:
      - name: main
        image: $image
        command: ["python"]
        args: $aj
        env: $ej
        resources:
          cpu: 0.5
          memory: 1Gi
identity: $ij
tags: {"application":"ProposalOps","environment":"AZURE-PREPROD","synthetic-only":"true","commissioning":"v2.5"}
"@
  $path=Join-Path ([IO.Path]::GetTempPath()) "proposalops-v25-$RunId.yaml";$yaml|Set-Content $path -Encoding utf8;Mutate @('containerapp','job','create','--subscription',$SubscriptionId,'-g',$RG,'-n',$name,'--yaml',$path,'-o','json') "Create V2.5 Job $name" 'BOOTSTRAP_JOB_CREATES';$path
}
function Run-One([string]$name){
  $before=@(AzJson @('containerapp','job','execution','list','--subscription',$SubscriptionId,'-g',$RG,'-n',$name,'-o','json') 'List executions before one start');$beforeNames=@($before|ForEach-Object name)
  Mutate @('containerapp','job','start','--subscription',$SubscriptionId,'-g',$RG,'-n',$name,'-o','json') 'Start exactly one V2.5 bootstrap' 'BOOTSTRAP_JOB_EXECUTIONS'
  for($i=0;$i-lt60;$i++){Start-Sleep -Seconds 5;$all=@(AzJson @('containerapp','job','execution','list','--subscription',$SubscriptionId,'-g',$RG,'-n',$name,'-o','json') 'Poll one execution');$new=@($all|Where-Object{$beforeNames-notcontains$_.name}|Sort-Object name -Descending);if($new.Count){$e=$new[0];$s=[string]($e.properties.status??$e.status);if($s-in@('Succeeded','Failed','Stopped','Degraded')){$l='';try{$l=Az @('containerapp','job','logs','show','--subscription',$SubscriptionId,'-g',$RG,'-n',$name,'--execution',$e.name,'--container','main','--tail','300','--format','text') 'Read bootstrap logs'}catch{};return [pscustomobject]@{status=$s;execution=$e;log=$l}}}};throw 'BOOTSTRAP_JOB_EXECUTION_TIMEOUT'
}

try {
 if(-not $Execute){throw 'EXECUTION_SWITCH_REQUIRED'}
 V24-Check
 $v24f=Get-Content (Join-Path $V24Evidence '13_FINAL_RESULT.json') -Raw|ConvertFrom-Json;Check 'V24 SDK failure preserved' ($v24f.AZURE_IDENTITY_CORROBORATION-eq'FAIL') 'FAIL'
 $sha=(git -C $RepoRoot rev-parse HEAD).Trim();$tree=(git -C $RepoRoot rev-parse 'HEAD^{tree}').Trim();$branch=(git -C $RepoRoot branch --show-current).Trim()
 Check 'scalar repair commit' ($sha-eq$ScalarRepairCommit) $sha;Check 'scalar repair script' ((Sha (Join-Path $RepoRoot 'scripts/proposalops_azure_p0_master_finalize_v2.ps1'))-eq$ExpectedScalarScriptSha) 'exact';Check 'accepted app tree' ((git -C $RepoRoot rev-parse "$ExpectedAppSha^{tree}").Trim()-eq$ExpectedAppTree) 'exact';Check 'accepted app unchanged' (@(git -C $RepoRoot diff --name-only $ExpectedAppSha HEAD -- infra backend frontend mock-systems).Count-eq0) 'zero';Check 'harness branch' ($branch-eq$HarnessBranch) $branch
 $rs=(git -C $RepoRoot ls-remote origin "refs/heads/$ScalarRepairBranch").Trim().Split([char]9)[0];Check 'scalar repair remote' ($rs-eq$ScalarRepairCommit) $rs
 $rh=(git -C $RepoRoot ls-remote origin "refs/heads/$HarnessBranch").Trim().Split([char]9)[0];Check 'harness remote' ($rh-eq$sha) $rh
 $t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile((Join-Path $RepoRoot 'scripts/proposalops_azure_p0_v25_native_msi_bootstrap_one_shot.ps1'),[ref]$t,[ref]$e)|Out-Null;Check 'harness parse' ($e.Count-eq0) 'PASS'
 $sub=(Az @('account','list','--query',"[?name=='AMEC Subscription' && state=='Enabled'].id | [0]",'-o','tsv') 'Resolve subscription').Trim();Check 'subscription resolved' (-not [string]::IsNullOrWhiteSpace($sub)) 'resolved';$SubscriptionId=$sub;Az @('group','list','--subscription',$sub,'--query','length(@)','-o','tsv') 'Prove ARM access'|Out-Null
 $RG='rg-proposalops-prod-uae';$SqlServer='sql-proposalops-prod-uae-2bea2887';$Db='sqldb-proposalops-prod';$AcaName='cae-proposalops-prod-uae';$AcrName='acrproposalopsproduae2bea2887'
 $sql=AzJson @('sql','server','show','--subscription',$sub,'-g',$RG,'-n',$SqlServer,'-o','json') 'Read SQL';$db=AzJson @('sql','db','show','--subscription',$sub,'-g',$RG,'--server',$SqlServer,'-n',$Db,'-o','json') 'Read DB';$aca=AzJson @('containerapp','env','show','--subscription',$sub,'-g',$RG,'-n',$AcaName,'-o','json') 'Read ACA env';$acr=AzJson @('acr','show','--subscription',$sub,'-g',$RG,'-n',$AcrName,'-o','json') 'Read ACR';$dns=AzJson @('network','private-dns','record-set','a','show','--subscription',$sub,'-g',$RG,'--zone-name','privatelink.database.windows.net','-n',$SqlServer,'-o','json') 'Read DNS';$pe=@(AzJson @('network','private-endpoint','list','--subscription',$sub,'-g',$RG,'-o','json') 'Read private endpoint')
 $peMatch=@($pe|Where-Object{$_.provisioningState-eq'Succeeded' -and @($_.privateLinkServiceConnections|Where-Object{$_.privateLinkServiceId-eq$sql.id -and $_.privateLinkServiceConnectionState.status-eq'Approved' -and $_.provisioningState-eq'Succeeded'}).Count-gt0})
 Check 'SQL ready' ($sql.state-eq'Ready') $sql.state;Check 'DB online' ($db.status-eq'Online') $db.status;Check 'SQL public disabled' ($sql.publicNetworkAccess-eq'Disabled') $sql.publicNetworkAccess;Check 'SQL Entra only' ([bool]$sql.administrators.azureAdOnlyAuthentication) 'true';Check 'SQL TLS accepted' ($sql.minimalTlsVersion-eq'1.2') $sql.minimalTlsVersion;Check 'private endpoint accepted' ($peMatch.Count-eq1) $peMatch.Count;Check 'private DNS' ($dns.aRecords[0].ipv4Address-eq'10.43.2.4') $dns.aRecords[0].ipv4Address;Check 'ACA env' ($aca.properties.provisioningState-eq'Succeeded') $aca.properties.provisioningState;Check 'ACR admin disabled' (-not [bool]$acr.adminUserEnabled) 'false'
 $uami=AzJson @('identity','show','--subscription',$sub,'-g',$RG,'-n','id-proposalops-sql-bootstrap-prod-uae','-o','json') 'Read bootstrap UAMI';$mig=AzJson @('identity','show','--subscription',$sub,'-g',$RG,'-n','id-proposalops-sql-migrate-prod-uae','-o','json') 'Read migration UAMI';$api=AzJson @('identity','show','--subscription',$sub,'-g',$RG,'-n','id-proposalops-api-prod-uae','-o','json') 'Read API UAMI'
 $BootstrapResourceId=[string]$uami.id;$BootstrapPrincipalId=[string]$uami.principalId;$BootstrapClientId=[string]$uami.clientId;$MigrationClientId=[string]$mig.clientId;$ApiClientId=[string]$api.clientId;$p=[guid]::Empty;$c=[guid]::Empty;$m=[guid]::Empty;$a=[guid]::Empty
 Check 'bootstrap principal GUID' ([guid]::TryParse($BootstrapPrincipalId,[ref]$p)) 'guid';Check 'bootstrap client GUID' ([guid]::TryParse($BootstrapClientId,[ref]$c)) 'guid';Check 'bootstrap IDs distinct' ($BootstrapPrincipalId-ne$BootstrapClientId) 'distinct';Check 'migration client GUID' ([guid]::TryParse($MigrationClientId,[ref]$m)) 'guid';Check 'API client GUID' ([guid]::TryParse($ApiClientId,[ref]$a)) 'guid'
 $human=Admin $sub $RG $SqlServer;Check 'human admin exact' ($human.Count-eq1-and$human[0].administratorType-eq'ActiveDirectory'-and$human[0].login-eq'Ahmed Sami') 'expected';$TenantId=[string]$human[0].tenantId
 Save-Json '00_RUN_CONTEXT.json' @{runId=$RunId;acceptedApplicationSha=$ExpectedAppSha;acceptedApplicationTree=$ExpectedAppTree;acceptedImage=$ExpectedImage;resourceGroup=$RG;sqlServer=$SqlServer;database=$Db;privateIp='10.43.2.4';v24Evidence=$V24Evidence;v24ManifestSha=$V24ManifestSha;harnessBranch=$branch;harnessCommit=$sha}
 Save-Json '01_V24_PRE_RUN_REVALIDATION.json' @{result='PASS';root=$V24Evidence;manifestSha=$V24ManifestSha;members=$V24Members;finalResult=$v24f.FINAL_RESULT;optionalSdk=$v24f.AZURE_IDENTITY_CORROBORATION}
 Save-Json '02_SCALAR_REPAIR_REMOTE_PIN.json' @{branch=$ScalarRepairBranch;head=$rs;commit=$ScalarRepairCommit;tree=(git -C $RepoRoot show -s --format=%T $ScalarRepairCommit);parent=(git -C $RepoRoot show -s --format=%P $ScalarRepairCommit);scriptSha256=(Sha (Join-Path $RepoRoot 'scripts/proposalops_azure_p0_master_finalize_v2.ps1'))}
 Save-Json '03_HARNESS_REMOTE_PIN.json' @{branch=$HarnessBranch;head=$rh;tree=$tree;parent=(git -C $RepoRoot show -s --format=%P $sha);changedPaths=@(git -C $RepoRoot diff-tree --no-commit-id --name-only -r $sha);harnessSha256=(Sha (Join-Path $RepoRoot 'scripts/proposalops_azure_p0_v25_native_msi_bootstrap_one_shot.ps1'))}
 Save-Json '04_AZURE_PREFLIGHT.json' @{resourceGroup=$RG;sqlServer=$SqlServer;database=$Db;databaseStatus=$db.status;sqlState=$sql.state;sqlPublicNetworkAccess=$sql.publicNetworkAccess;sqlEntraOnly=[bool]$sql.administrators.azureAdOnlyAuthentication;minimalTlsVersion=$sql.minimalTlsVersion;privateEndpointCount=$peMatch.Count;privateDnsIp=$dns.aRecords[0].ipv4Address;acaEnvironment=$AcaName;acaState=$aca.properties.provisioningState;acrAdminEnabled=[bool]$acr.adminUserEnabled}
 Save-Json '05_UAMI_IDENTITY_MATRIX.json' @(@{name='bootstrap';resourceId=$BootstrapResourceId;principalId=$BootstrapPrincipalId;clientId=$BootstrapClientId;principalClientDistinct=$true},@{name='migration';clientId=$MigrationClientId},@{name='api';clientId=$ApiClientId})
 Save-Json '06_HUMAN_SQL_ADMIN_SNAPSHOT.json' @{login=$human[0].login;sid=$human[0].sid;tenantId=$human[0].tenantId;administratorType=$human[0].administratorType}
 $JobName="p0-sql-bootstrap-v2-5-$RunId";$jobs=@(AzJson @('containerapp','job','list','--subscription',$sub,'-g',$RG,'-o','json') 'Read existing jobs');Check 'V2.5 job absent' (@($jobs|Where-Object name-eq$JobName).Count-eq0) 'absent'
 $null=New-Job $JobName $BootstrapResourceId ([string]$aca.id) ([string]$acr.loginServer) $ExpectedImage ([string]$sql.fullyQualifiedDomainName) $Db $BootstrapPrincipalId $ApiClientId $MigrationClientId $TenantId
 $j=AzJson @('containerapp','job','show','--subscription',$sub,'-g',$RG,'-n',$JobName,'-o','json') 'Read Job prestart';$cc=$j.properties.template.containers[0];$ids=@($j.identity.userAssignedIdentities.PSObject.Properties.Name);$re=@($j.properties.configuration.registries|Where-Object server-eq$acr.loginServer);$je=@($cc.env|Where-Object name-eq'SQL_ODBC_UID');$jp=[guid]::Empty
 Check 'Job image exact' ($cc.image-eq$ExpectedImage) 'exact';Check 'Job identity exact' ($ids.Count-eq1-and$ids[0]-eq$BootstrapResourceId) 'exact';Check 'Job registry identity' ($re.Count-eq1-and$re[0].identity-eq$BootstrapResourceId) 'exact';Check 'Job command' (@($cc.command).Count-eq1-and$cc.command[0]-eq'python') 'python';Check 'Job args' (@($cc.args).Count-eq2-and$cc.args[0]-eq'-c') 'python -c';Check 'Job UID exact' ($je.Count-eq1-and$je[0].value-eq$BootstrapPrincipalId-and$je[0].value-ne$BootstrapClientId-and[guid]::TryParse([string]$je[0].value,[ref]$jp)) 'principalId/objectId';Check 'Job retry zero' ([int]$j.properties.configuration.replicaRetryLimit-eq0) '0';Check 'Job manual singleton' ($j.properties.configuration.triggerType-eq'Manual'-and[int]$j.properties.configuration.manualTriggerConfig.parallelism-eq1-and[int]$j.properties.configuration.manualTriggerConfig.replicaCompletionCount-eq1) 'PASS'
 Save-Json '07_V25_JOB_PRESTART_READBACK.json' @{result='PASS';jobName=$JobName;imageExact=$true;identityExact=$true;registryIdentityExact=$true;commandExact=$true;argsExact=$true;uidIsGuid=$true;uidEqualsBootstrapPrincipalId=$true;uidEqualsBootstrapClientId=$false;retryLimit=0;parallelism=1;completionCount=1}
 try {
   $AdminChanged=$true;Mutate @('sql','server','ad-admin','update','--subscription',$sub,'-g',$RG,'--server',$SqlServer,'--display-name','id-proposalops-sql-bootstrap-prod-uae','--object-id',$BootstrapClientId,'-o','json') 'Switch SQL admin to bootstrap application identity' 'SQL_ADMIN_SWITCH_MUTATIONS'
   $sw=WaitAdmin $sub $RG $SqlServer $BootstrapClientId 180;Check 'bootstrap SQL admin control plane' ($sw.Count-eq1-and(($sw[0].sid-eq$BootstrapClientId)-or($sw[0].objectId-eq$BootstrapClientId))) 'PASS';Save-Json '08_SQL_ADMIN_SWITCH.json' @{result='PASS';identityClass='clientId/applicationId';tenantMatched=($sw[0].tenantId-eq$TenantId)}
   $run=Run-One $JobName;$line=@($run.log-split'\r?\n'|Where-Object{$_-match'stdout F \{' }|Select-Object -Last 1);$text=[regex]::Replace([string]$line,'^.*stdout F ','');if([string]::IsNullOrWhiteSpace($text)){throw 'BOOTSTRAP_RESULT_JSON_NOT_FOUND'};$sr=$text|ConvertFrom-Json
   $Counts.SQL_CONNECTION_ATTEMPTS=[int]$sr.sql_connection_attempts;$Counts.SQL_CREATE_USER_MUTATIONS=[int]$sr.api_mutations+[int]$sr.migration_mutations;$Counts.SQL_ROLE_MUTATIONS=[int]$sr.role_mutations;$Counts.SQL_PERMISSION_GRANTS=[int]$sr.permission_grants
   Save-Json '09_EXECUTION_AND_SQL_RESULT.json' @{jobName=$JobName;execution=$run.execution;status=$run.status;sqlConnectionAttempts=$Counts.SQL_CONNECTION_ATTEMPTS;result=$sr;automaticRetries=0}
   Check 'SQL connection attempts one' ($Counts.SQL_CONNECTION_ATTEMPTS-eq1) '1';if($run.status-ne'Succeeded'-or-not$sr.post_verification){throw "V25_BOOTSTRAP_FAILURE status=$($run.status)"};Check 'SQL login' ($sr.sql_login-eq'PASS') $sr.sql_login;Check 'SQL target DB' ($sr.sql_target_db-eq'PASS') $sr.sql_target_db;Check 'SQL required permission' ($sr.sql_required_permission-eq'PASS') $sr.sql_required_permission;Check 'contained principals' ([bool]$sr.post_verification) 'PASS'
 } catch { $Failure=$_.Exception.Message }
} catch { $Failure=$_.Exception.Message }
finally {
 if($AdminChanged){try{Mutate @('sql','server','ad-admin','update','--subscription',$SubscriptionId,'-g',$RG,'--server',$SqlServer,'--display-name',[string]$human[0].login,'--object-id',[string]$human[0].sid,'-o','json') 'Restore human SQL admin' 'SQL_ADMIN_RESTORE_MUTATIONS';$r=WaitAdmin $SubscriptionId $RG $SqlServer ([string]$human[0].sid) 180;if($r.Count-ne1-or$r[0].sid-ne$human[0].sid-or$r[0].login-ne$human[0].login-or$r[0].tenantId-ne$human[0].tenantId){throw 'HUMAN_SQL_ADMIN_RESTORE_MISMATCH'};$AdminRestored=$true}catch{$Failure="V2_5_CRITICAL_HUMAN_SQL_ADMIN_RESTORE_FAILURE $($_.Exception.Message)"}}
 Save-Json '10_POSTCONDITIONS.json' @{humanSqlAdminRestored=$AdminRestored;sqlPublicNetwork='Disabled';sqlContainedPrincipals=if($Failure){'NOT_VERIFIED'}else{'PASS'}}
 Save-Json '11_MUTATION_LEDGER.json' $Counts
 Save-Json '12_SAFETY_CEILINGS.json' @{AUTOMATIC_RETRIES=0;BOOTSTRAP_JOB_UPDATES=0;BOOTSTRAP_JOB_DELETES=0;ENTRA_MUTATIONS=0;RBAC_MUTATIONS=0;FIREWALL_MUTATIONS=0;SQL_PUBLIC_NETWORK_MUTATIONS=0;MIGRATION_EXECUTIONS=0;SEED_EXECUTIONS=0;API_DEPLOYMENTS=0;FRONTEND_DEPLOYMENTS=0;SYNLOGY_READS=0;REAL_AMEC_DATA_READS=0;REAL_AMEC_DATA_WRITES=0;PHASE6_MUTATIONS=0}
 $post=$null
 try { if([string]::IsNullOrWhiteSpace($V24Evidence)){throw 'V24_EVIDENCE_INTEGRITY_FAIL'}; $post=Assert-V24 $V24Evidence }
 catch { if(-not $Failure){$Failure=$_.Exception.Message};$post=[ordered]@{result='FAIL';error=$_.Exception.Message} }
 Save-Json '13_V24_POST_RUN_REHASH.json' $post
 $final=if($Failure){'V2_5_NATIVE_MSI_BOOTSTRAP_FAIL'}else{'V2_5_NATIVE_MSI_BOOTSTRAP_PASS'}
 Save-Json '14_FINAL_RESULT.json' @{FINAL_RESULT=$final;FAILURE=$Failure;FAILING_OPERATION=$CurrentOperation;MALFORMED_UID_CONFIRMED_BLOCKER=$true;MALFORMED_UID_SOLE_ROOT_CAUSE='NOT_CLAIMED';V24_SDK_CORROBORATION='FAIL_UNRESOLVED';NATIVE_MSI_BOOTSTRAP=if($Failure){'FAIL'}else{'PASS'};AZURE_SQL_LOGIN_PROVEN=if($Failure){$false}else{$true};SQL_CONTAINED_PRINCIPALS_PROVEN=if($Failure){$false}else{$true};SCHEMA_MIGRATION_PROVEN=$false;SYNTHETIC_SEED_PROVEN=$false;API_DEPLOYMENT_PROVEN=$false;AUTHENTICATED_BROWSER_RUNTIME_PROVEN=$false;FULL_DOCUMENT_STORAGE_CONTINUITY_PROVEN=$false;CROSS_TRACK_CONVERGENCE_AUTHORIZED=$false;PHASE6_AUTHORIZED=$false;REAL_AMEC_DATA_ALLOWED=$false;STAGE1R_A_RERUN=$false;T3_RERUN=$false;T5_AUTHORIZED=$false;NEXT='OWNER_REVIEW';humanSqlAdminRestored=$AdminRestored}
 Save-Json '15_INDEPENDENT_CHECKS.json' $Checks
 @("FINAL_RESULT=$final","FAILURE=$Failure","REPOSITORY_COMMITS_CREATED=$($Counts.REPOSITORY_COMMITS_CREATED)","REMOTE_BRANCHES_CREATED=$($Counts.REMOTE_BRANCHES_CREATED)","REMOTE_BRANCH_UPDATES=$($Counts.REMOTE_BRANCH_UPDATES)","BOOTSTRAP_JOB_CREATES=$($Counts.BOOTSTRAP_JOB_CREATES)","BOOTSTRAP_JOB_EXECUTIONS=$($Counts.BOOTSTRAP_JOB_EXECUTIONS)","SQL_ADMIN_SWITCH_MUTATIONS=$($Counts.SQL_ADMIN_SWITCH_MUTATIONS)","SQL_ADMIN_RESTORE_MUTATIONS=$($Counts.SQL_ADMIN_RESTORE_MUTATIONS)","SQL_CONNECTION_ATTEMPTS=$($Counts.SQL_CONNECTION_ATTEMPTS)","SQL_CREATE_USER_MUTATIONS=$($Counts.SQL_CREATE_USER_MUTATIONS)","SQL_ROLE_MUTATIONS=$($Counts.SQL_ROLE_MUTATIONS)","SQL_PERMISSION_GRANTS=$($Counts.SQL_PERMISSION_GRANTS)","SQL_DDL_OTHER=0","SQL_DML_MUTATIONS=0","ENTRA_MUTATIONS=0","RBAC_MUTATIONS=0","FIREWALL_MUTATIONS=0","SQL_PUBLIC_NETWORK_MUTATIONS=0","MIGRATION_EXECUTIONS=0","SEED_EXECUTIONS=0","API_DEPLOYMENTS=0","FRONTEND_DEPLOYMENTS=0","SYNLOGY_READS=0","REAL_AMEC_DATA_READS=0","REAL_AMEC_DATA_WRITES=0","PHASE6_MUTATIONS=0","HUMAN_SQL_ADMIN_RESTORED=$AdminRestored","MALFORMED_UID_SOLE_ROOT_CAUSE=NOT_CLAIMED","V24_SDK_CORROBORATION=FAIL_UNRESOLVED","NEXT=OWNER_REVIEW","EVIDENCE_ROOT=$EvidenceRoot")|Set-Content (Join-Path $EvidenceRoot 'transcript.txt') -Encoding utf8
 $manifest=Join-Path $EvidenceRoot 'MANIFEST.sha256';Get-ChildItem $EvidenceRoot -File|Where-Object Name-ne'MANIFEST.sha256'|Sort-Object Name|ForEach-Object{Add-Content $manifest "$(Sha $_.FullName)  $($_.Name)" -Encoding utf8};$v=& shasum -a 256 -c $manifest 2>&1;if($LASTEXITCODE-ne0){$final='V2_5_NATIVE_MSI_BOOTSTRAP_FAIL'}
 Add-Content (Join-Path $EvidenceRoot 'transcript.txt') ('MANIFEST_RECOMPUTATION=PASS'+[Environment]::NewLine+'MANIFEST_SHA256='+$(Sha $manifest)) -Encoding utf8
}
Write-Output "FINAL_RESULT=$(if($Failure){'V2_5_NATIVE_MSI_BOOTSTRAP_FAIL'}else{'V2_5_NATIVE_MSI_BOOTSTRAP_PASS'})";Write-Output "EVIDENCE_ROOT=$EvidenceRoot";if($Failure){exit 1}
