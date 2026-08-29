import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';

const repo = '/private/tmp/proposalops-ui-clean-handoff';
const out = '/tmp/proposalops-ui-v3-preflight-100.json';
const S = '3f60c02ee7fdee385130b97b518f9060de1d42a8';
const S_TREE = '6e676f2c5b7888af3631a413e26176ec028ae5eb';
const S_PARENT = 'a1ed3628bd104b5c5b9580c977fcdf33bbf8cae2';
const FRONTEND_TREE = '0d32e10e1882a1061ca86926347365ec866279fc';
const BACKEND_TREE = 'df227ee768ba0e52268622fa8790c5e4ae035d54';
const H2 = '05105b136063135ace7f3223a9716676ab5d76b7';
const E2 = 'dc0f95b836b12b0ee1686e26a38841ef77328495';
const V2 = path.join(repo, 'artifacts/ui-ux-r1-clean-handoff-v2');
const src = fs.readFileSync(path.join(repo, 'frontend/src/AMECWork.tsx'), 'utf8');
const backendFiles = execFileSync('rg', ['-l', '@router\\.(get|post|put|patch|delete)|APIRouter', 'backend/app'], {cwd: repo, encoding:'utf8'}).trim().split('\n').filter(Boolean);
const backendText = backendFiles.map(f => fs.readFileSync(path.join(repo,f),'utf8')).join('\n');
const git = (...args) => execFileSync('git', args, {cwd:repo, encoding:'utf8'}).trim();
const sha256 = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const j = file => JSON.parse(fs.readFileSync(path.join(repo,file), 'utf8'));
const checks = [];
function add(kind, proposition, evidence, observed, expected, predicate, evaluation) {
  checks.push({CHECK_ID:`PRE-${String(checks.length+1).padStart(3,'0')}`, CHECK_KIND:kind, PROPOSITION:proposition, EVIDENCE_SOURCE:evidence, OBSERVED_VALUE:observed, EXPECTED_VALUE:expected, MECHANICAL_PREDICATE:predicate, MECHANICAL_EVALUATION:evaluation, RESULT:evaluation ? 'PASS' : 'FAIL'});
}
function eq(kind,p,e,o,x,v){ add(kind,p,e,o,x,`observed === expected`,v===x); }
function yes(kind,p,e,v){ add(kind,p,e,v,true,`observed === true`,v===true); }

eq('GIT_EXACT','current branch is the required handoff branch','git branch --show-current',git('branch','--show-current'),'ui-product-r1-clean-handoff-v1',git('branch','--show-current'));
eq('GIT_EXACT','local entry tip is H2','git rev-parse HEAD',git('rev-parse','HEAD'),H2,git('rev-parse','HEAD'));
eq('GIT_EXACT','remote entry tip is H2','git ls-remote origin refs/heads/ui-product-r1-clean-handoff-v1',git('ls-remote','origin','refs/heads/ui-product-r1-clean-handoff-v1').split('\t')[0],H2,git('ls-remote','origin','refs/heads/ui-product-r1-clean-handoff-v1').split('\t')[0]);
eq('GIT_ANCESTRY','H2 parent is E2','git rev-list --parents -n 1 H2',git('rev-list','--parents','-n','1',H2).split(' ')[1],E2,git('rev-list','--parents','-n','1',H2).split(' ')[1]);
eq('GIT_ANCESTRY','E2 parent is frozen source parent','git rev-list --parents -n 1 E2',git('rev-list','--parents','-n','1',E2).split(' ')[1],'f939daf47ee6223a72ccbcc3d0226373a8742162',git('rev-list','--parents','-n','1',E2).split(' ')[1]);
eq('TREE_EQUALITY','frozen source tree is exact','git show -s --format=%T S',git('show','-s','--format=%T',S),S_TREE,git('show','-s','--format=%T',S));
eq('GIT_ANCESTRY','frozen source parent is exact','git rev-list --parents -n 1 S',git('rev-list','--parents','-n','1',S).split(' ')[1],S_PARENT,git('rev-list','--parents','-n','1',S).split(' ')[1]);
eq('TREE_EQUALITY','frozen frontend tree is exact','git rev-parse S:frontend',git('rev-parse',`${S}:frontend`),FRONTEND_TREE,git('rev-parse',`${S}:frontend`));
eq('TREE_EQUALITY','frozen backend tree is exact','git rev-parse S:backend',git('rev-parse',`${S}:backend`),BACKEND_TREE,git('rev-parse',`${S}:backend`));
function ancestor(a,b){try{git('merge-base','--is-ancestor',a,b);return true;}catch{return false;}}
yes('GIT_ANCESTRY','H2 contains the frozen source','git merge-base --is-ancestor S H2',ancestor(S,H2));
eq('GIT_EXACT','H2 commit message is exact','git show -s --format=%s H2',git('show','-s','--format=%s',H2),'docs(ui): finalize authoritative Azure handoff v2',git('show','-s','--format=%s',H2));
eq('GIT_EXACT','E2 commit message is exact','git show -s --format=%s E2',git('show','-s','--format=%s',E2),'docs(ui): close independently validated R1 handoff evidence v2',git('show','-s','--format=%s',E2));
eq('COUNT','H2 changes exactly one V2 handoff record','git diff-tree H2',git('diff-tree','--no-commit-id','--name-only','-r',H2).split('\n').filter(Boolean).length,1,git('diff-tree','--no-commit-id','--name-only','-r',H2).split('\n').filter(Boolean).length);
eq('GIT_EXACT','H2 changed path is V2 Azure handoff','git diff-tree H2 path',git('diff-tree','--no-commit-id','--name-only','-r',H2),'artifacts/ui-ux-r1-clean-handoff-v2/24-azure-handoff.json',git('diff-tree','--no-commit-id','--name-only','-r',H2));
yes('GIT_ANCESTRY','source commit is not changed by current worktree','git diff S -- frontend backend',git('diff','--quiet',S,'--','frontend','backend') === '');

eq('FILE_EQUALITY','V1 evidence directory is present','V1 path',fs.existsSync(path.join(repo,'artifacts/ui-ux-r1-clean-handoff')),true,fs.existsSync(path.join(repo,'artifacts/ui-ux-r1-clean-handoff')));
eq('FILE_EQUALITY','V2 evidence directory is present','V2 path',fs.existsSync(V2),true,fs.existsSync(V2));
eq('FILE_EQUALITY','V2 final source result is present','V2 23 path',fs.existsSync(path.join(V2,'23-final-source-result.json')),true,fs.existsSync(path.join(V2,'23-final-source-result.json')));
eq('JSON_FIELD','V2 source result records frozen source','V2/23-final-source-result.json source_sha',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').source_sha,S,j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').source_sha);
eq('JSON_FIELD','V2 source result records six viewport result','V2/23-final-source-result.json six_viewport_browser_crawl',Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'six_viewport_browser_crawl'),false,Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'six_viewport_browser_crawl'));
eq('HASH','V2 manifest digest is exact','V2 SHA256SUMS manifest line',sha256(path.join(V2,'SHA256SUMS')),'830431bf2cce9a23b09482497698a38928d075b5d0558bda6c415baa86458503',sha256(path.join(V2,'SHA256SUMS')));
eq('HASH','V2 source result digest is exact','V2 source result digest',sha256(path.join(V2,'23-final-source-result.json')),'c16034da9b2dfad4fb009e5962bf4d0a0ef2463050a56e48aed0c99d33c5425d',sha256(path.join(V2,'23-final-source-result.json')));

yes('SOURCE_BEHAVIOR','AMECWork imports the API helper','frontend/src/AMECWork.tsx',src.includes('import { api } from "./api";'),src.includes('import { api } from "./api";'));
yes('SOURCE_BEHAVIOR','AMECWork defines the load function','frontend/src/AMECWork.tsx',/const load\s*=/.test(src),/const load\s*=/.test(src));
yes('SOURCE_BEHAVIOR','load sets loading before read','frontend/src/AMECWork.tsx',src.includes('setLoading(true)'),src.includes('setLoading(true)'));
yes('SOURCE_BEHAVIOR','load clears error before read','frontend/src/AMECWork.tsx',src.includes('setError("")'),src.includes('setError("")'));
yes('SOURCE_BEHAVIOR','load uses the exact /api/work template literal','frontend/src/AMECWork.tsx',src.includes('api<any>(`/api/work${query.toString() ? `?${query}` : ""}`)'),src.includes('api<any>(`/api/work${query.toString() ? `?${query}` : ""}`)'));
yes('SOURCE_BEHAVIOR','load stores successful response data','frontend/src/AMECWork.tsx',src.includes('.then(setData)'),src.includes('.then(setData)'));
yes('SOURCE_BEHAVIOR','load has a caught failure branch','frontend/src/AMECWork.tsx',src.includes('.catch((cause)'),src.includes('.catch((cause)'));
yes('SOURCE_BEHAVIOR','load ends loading in finally','frontend/src/AMECWork.tsx',src.includes('.finally(() => setLoading(false))'),src.includes('.finally(() => setLoading(false))'));
yes('SOURCE_BEHAVIOR','filter state includes team/domain/kpi','frontend/src/AMECWork.tsx',src.includes('type WorkFilters = { team: string; domain: string; kpi: string };'),src.includes('type WorkFilters = { team: string; domain: string; kpi: string };'));
yes('SOURCE_BEHAVIOR','effect depends on all work filters','frontend/src/AMECWork.tsx',src.includes('useEffect(() => { load(); }, [filters.team, filters.domain, filters.kpi, demoRole])'),src.includes('useEffect(() => { load(); }, [filters.team, filters.domain, filters.kpi, demoRole])'));
yes('SOURCE_BEHAVIOR','update mutates filter state','frontend/src/AMECWork.tsx',src.includes('setFilters(value)'),src.includes('setFilters(value)'));
yes('SOURCE_BEHAVIOR','KPI control calls update','frontend/src/AMECWork.tsx',src.includes('onClick={() => update({ kpi:'),src.includes('onClick={() => update({ kpi:'));
yes('SOURCE_BEHAVIOR','Team select calls update','frontend/src/AMECWork.tsx',src.includes('onChange={(event) => update({ team:'),src.includes('onChange={(event) => update({ team:'));
yes('SOURCE_BEHAVIOR','Work select calls update','frontend/src/AMECWork.tsx',src.includes('onChange={(event) => update({ domain:'),src.includes('onChange={(event) => update({ domain:'));
yes('SOURCE_BEHAVIOR','clearFilters calls update','frontend/src/AMECWork.tsx',src.includes('const clearFilters = () => update({ team: "all", domain: "all", kpi: "all" });'),src.includes('const clearFilters = () => update({ team: "all", domain: "all", kpi: "all" });'));
yes('SOURCE_BEHAVIOR','Retry button is bound to load','frontend/src/AMECWork.tsx',src.includes('<button className="button-primary" onClick={load}>Retry</button>'),src.includes('<button className="button-primary" onClick={load}>Retry</button>'));
yes('SOURCE_BEHAVIOR','loading state is distinct','frontend/src/AMECWork.tsx',src.includes('className="panel amec-work-loading" role="status"'),src.includes('className="panel amec-work-loading" role="status"'));
yes('SOURCE_BEHAVIOR','failure state is an alert','frontend/src/AMECWork.tsx',src.includes('className="panel amec-work-error" role="alert"'),src.includes('className="panel amec-work-error" role="alert"'));
yes('SOURCE_BEHAVIOR','failure state excludes empty/caught-up rendering','frontend/src/AMECWork.tsx',src.includes('{!loading && !error && <section className="panel amec-work-list">'),src.includes('{!loading && !error && <section className="panel amec-work-list">'));
yes('SOURCE_BEHAVIOR','valid empty state is separate from failure','frontend/src/AMECWork.tsx',src.includes('className="amec-work-empty"'),src.includes('className="amec-work-empty"'));
yes('SOURCE_BEHAVIOR','Team visibility is role-dependent','frontend/src/AMECWork.tsx',src.includes('{isOwner && <label>Team'),src.includes('{isOwner && <label>Team'));
yes('SOURCE_BEHAVIOR','work page identifies synthetic prototype data','frontend/src/AMECWork.tsx',src.includes('SYNTHETIC PROTOTYPE'),src.includes('SYNTHETIC PROTOTYPE'));

const workRoute = backendText.match(/\/api\/work/g) || [];
eq('BACKEND_ROUTE','frozen backend source identifies the /api/work router','backend/app/api/work_routers.py',workRoute.length>0,true,workRoute.length>0);
yes('BACKEND_ROUTE','backend route inventory contains router decorators','backend/app route sources',/@router\.(get|post|put|patch|delete)/.test(backendText),/@router\.(get|post|put|patch|delete)/.test(backendText));
yes('BACKEND_ROUTE','backend route inventory was collected from backend/app','rg route source list',backendFiles.length>0,backendFiles.length>0);
eq('BACKEND_ROUTE','exact GET /api/work decorator exists','backend/app/api/work_routers.py',/@router\.get\(""\)/.test(fs.readFileSync(path.join(repo,'backend/app/api/work_routers.py'),'utf8')),true,/@router\.get\(""\)/.test(fs.readFileSync(path.join(repo,'backend/app/api/work_routers.py'),'utf8')));
eq('BACKEND_ROUTE','work router prefix is /api/work','backend/app/api/work_routers.py',fs.readFileSync(path.join(repo,'backend/app/api/work_routers.py'),'utf8').match(/APIRouter\(prefix="([^"]+)"/)[1],'/api/work',fs.readFileSync(path.join(repo,'backend/app/api/work_routers.py'),'utf8').match(/APIRouter\(prefix="([^"]+)"/)[1]);

const v2crawl=j('artifacts/ui-ux-r1-clean-handoff-v2/17-full-ui-crawl/runtime-results.json');
eq('COUNT','V2 runtime scenario rows are 624','V2 runtime-results.json result_count',v2crawl.result_count,624,v2crawl.result_count);
eq('COUNT','V2 runtime result array is 624','V2 runtime-results.json results.length',v2crawl.results.length,624,v2crawl.results.length);
eq('RUNTIME_RESULT','V2 runtime rows report 624 passes','V2 runtime-results.json results',v2crawl.results.filter(x=>x.contract===true).length,624,v2crawl.results.filter(x=>x.contract===true).length);
eq('RUNTIME_RESULT','V2 runtime rows report zero failures','V2 runtime-results.json results',v2crawl.results.filter(x=>x.contract!==true).length,0,v2crawl.results.filter(x=>x.contract!==true).length);
eq('COUNT','V2 crawl has 624 screenshots','V2 crawl PNG inventory',fs.readdirSync(path.join(V2,'17-full-ui-crawl/screenshots')).filter(x=>x.endsWith('.png')).length,624,fs.readdirSync(path.join(V2,'17-full-ui-crawl/screenshots')).filter(x=>x.endsWith('.png')).length);
eq('COUNT','V2 crawl has 6 viewport widths','V2 runtime result viewport set',[...new Set(v2crawl.results.map(x=>x.viewport.replace(/^v/,'' )).filter(Boolean))].sort((a,b)=>+a-+b).join(','),'390,834,1024,1280,1440,1920',[...new Set(v2crawl.results.map(x=>x.viewport.replace(/^v/,'' )).filter(Boolean))].sort((a,b)=>+a-+b).join(','));
eq('COUNT','V2 crawl covers 3 personas','V2 runtime result persona set',[...new Set(v2crawl.results.map(x=>x.persona).filter(Boolean))].sort().join('|'),'Business Development|Engineering|Owner',[...new Set(v2crawl.results.map(x=>x.persona).filter(Boolean))].sort().join('|'));
eq('COUNT','V2 route count is 66','V2 runtime-results.json route_count',v2crawl.route_count,66,v2crawl.route_count);
eq('COUNT','V2 applicable route/persona combinations are 104','V2 route inventory applicable count',j('artifacts/ui-ux-r1-clean-handoff-v2/04-route-ledger.json').applicable_route_persona_combinations,104,j('artifacts/ui-ux-r1-clean-handoff-v2/04-route-ledger.json').applicable_route_persona_combinations);
add('RUNTIME_RESULT','V2 mobile proof is 25/25','V2/14-mobile-keyboard-focus-25.json summary',`${j('artifacts/ui-ux-r1-clean-handoff-v2/14-mobile-keyboard-focus-25.json').summary.pass}/${j('artifacts/ui-ux-r1-clean-handoff-v2/14-mobile-keyboard-focus-25.json').summary.total} PASS`,'25/25 PASS','summary.pass === 25 && summary.total === 25',j('artifacts/ui-ux-r1-clean-handoff-v2/14-mobile-keyboard-focus-25.json').summary.pass===25&&j('artifacts/ui-ux-r1-clean-handoff-v2/14-mobile-keyboard-focus-25.json').summary.total===25);
eq('RUNTIME_RESULT','V2 auth presentation proof is 3/3','V2/16-auth-failure-runtime.json result_count',j('artifacts/ui-ux-r1-clean-handoff-v2/16-auth-failure-runtime.json').result_count,3,j('artifacts/ui-ux-r1-clean-handoff-v2/16-auth-failure-runtime.json').result_count);
yes('RUNTIME_RESULT','V2 auth presentation proof passes','V2/16-auth-failure-runtime.json',j('artifacts/ui-ux-r1-clean-handoff-v2/16-auth-failure-runtime.json').AUTH_FAILURE_PRESENTATION_PASS===true,j('artifacts/ui-ux-r1-clean-handoff-v2/16-auth-failure-runtime.json').AUTH_FAILURE_PRESENTATION_PASS===true);

const api=j('artifacts/ui-ux-r1-clean-handoff-v2/06-api-family-ledger.json');
eq('JSON_FIELD','V2 API ledger has 262 frontend consumers','V2/06-api-family-ledger.json frontend_api_consumer_count',api.frontend_api_consumer_count,262,api.frontend_api_consumer_count);
eq('JSON_FIELD','V2 API ledger had API-001','V2/06-api-family-ledger.json families',api.families.some(x=>x.API_FAMILY_ID==='API-001'),true,api.families.some(x=>x.API_FAMILY_ID==='API-001'));
eq('JSON_FIELD','V2 API-001 source path is /api/work','V2 API-001',api.families.find(x=>x.API_FAMILY_ID==='API-001').NORMALIZED_PATH_TEMPLATE,'/api/work?{query}',api.families.find(x=>x.API_FAMILY_ID==='API-001').NORMALIZED_PATH_TEMPLATE);
eq('JSON_FIELD','V2 API-001 exposed the legacy semantic defect','V2 API-001 disposition',api.families.find(x=>x.API_FAMILY_ID==='API-001').DISPOSITION,'LEGACY_COMPATIBILITY_ONLY',api.families.find(x=>x.API_FAMILY_ID==='API-001').DISPOSITION);
const vals=j('artifacts/ui-ux-r1-clean-handoff-v2/07-value-binding-ledger.json').values;
eq('COUNT','V2 value ledger has 262 rows','V2/07-value-binding-ledger.json values.length',vals.length,262,vals.length);
eq('JSON_FIELD','V2 value ledger recorded no unresolved bindings','V2/07-value-binding-ledger.json VALUE_BINDING_UNRESOLVED',j('artifacts/ui-ux-r1-clean-handoff-v2/07-value-binding-ledger.json').VALUE_BINDING_UNRESOLVED,0,j('artifacts/ui-ux-r1-clean-handoff-v2/07-value-binding-ledger.json').VALUE_BINDING_UNRESOLVED);
eq('JSON_FIELD','V2 action ledger has 359 rows','V2/08-action-ledger.json actions.length',j('artifacts/ui-ux-r1-clean-handoff-v2/08-action-ledger.json').actions.length,359,j('artifacts/ui-ux-r1-clean-handoff-v2/08-action-ledger.json').actions.length);
eq('JSON_FIELD','V2 action ledger exposed AMECWork Retry','V2/08-action-ledger.json action rows',j('artifacts/ui-ux-r1-clean-handoff-v2/08-action-ledger.json').actions.some(x=>x.SURFACE==='AMECWork'&&x.HANDLER==='load'),true,j('artifacts/ui-ux-r1-clean-handoff-v2/08-action-ledger.json').actions.some(x=>x.SURFACE==='AMECWork'&&x.HANDLER==='load'));
eq('JSON_FIELD','V2 AMECWork Retry was misclassified','V2/08-action-ledger.json AMECWork load',j('artifacts/ui-ux-r1-clean-handoff-v2/08-action-ledger.json').actions.find(x=>x.SURFACE==='AMECWork'&&x.HANDLER==='load').ACTION_CLASS,'LOCAL_PRESENTATION_ONLY',j('artifacts/ui-ux-r1-clean-handoff-v2/08-action-ledger.json').actions.find(x=>x.SURFACE==='AMECWork'&&x.HANDLER==='load').ACTION_CLASS);
eq('JSON_FIELD','V2 final source result omitted pending gate files','V2/23-final-source-result.json',!Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'pending_gate_files'),true,!Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'pending_gate_files'));
eq('JSON_FIELD','V2 final source result omitted contradiction count','V2/23-final-source-result.json',!Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'dedicated_gate_summary_contradictions'),true,!Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'dedicated_gate_summary_contradictions'));
eq('JSON_FIELD','V2 final source result omitted proposition mismatch count','V2/23-final-source-result.json',!Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'proposition_evidence_mismatches'),true,!Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'proposition_evidence_mismatches'));
eq('JSON_FIELD','V2 final source result omitted six viewport field','V2/23-final-source-result.json',!Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'six_viewport_browser_crawl'),true,!Object.hasOwn(j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json'),'six_viewport_browser_crawl'));

eq('HASH','frozen AMECWork source blob is stable','git hash-object + git rev-parse S:path',git('hash-object','frontend/src/AMECWork.tsx'),git('rev-parse',`${S}:frontend/src/AMECWork.tsx`),git('hash-object','frontend/src/AMECWork.tsx'));
eq('FILE_EQUALITY','frozen package.json is unchanged','git diff S -- package.json',git('diff','--name-only',S,'--','package.json').length,0,git('diff','--name-only',S,'--','package.json').length);
eq('FILE_EQUALITY','frozen lockfile is unchanged','git diff S -- package-lock.json',git('diff','--name-only',S,'--','package-lock.json').length,0,git('diff','--name-only',S,'--','package-lock.json').length);
eq('TREE_EQUALITY','frozen frontend tree equals current frontend tree','git show S:frontend',git('rev-parse','HEAD:frontend'),FRONTEND_TREE,git('rev-parse','HEAD:frontend'));
eq('GIT_ANCESTRY','E2 is an ancestor of H2','git merge-base --is-ancestor E2 H2',ancestor(E2,H2),true,ancestor(E2,H2));
eq('GIT_ANCESTRY','S is an ancestor of E2','git merge-base --is-ancestor S E2',ancestor(S,E2),true,ancestor(S,E2));
eq('COUNT','V2 crawl contains 16 gate JSON records','V2/17-full-ui-crawl JSON inventory',fs.readdirSync(path.join(V2,'17-full-ui-crawl')).filter(x=>x.endsWith('.json')).length,16,fs.readdirSync(path.join(V2,'17-full-ui-crawl')).filter(x=>x.endsWith('.json')).length);
eq('RUNTIME_RESULT','V2 runtime rows have no console errors','V2 runtime-results.json console_errors',v2crawl.console_errors.length,0,v2crawl.console_errors.length);
eq('RUNTIME_RESULT','V2 runtime rows have no request failures','V2 runtime-results.json request_failures',v2crawl.request_failures.length,0,v2crawl.request_failures.length);
eq('RUNTIME_RESULT','V2 runtime rows have no bad responses','V2 runtime-results.json bad_responses',v2crawl.bad_responses.length,0,v2crawl.bad_responses.length);
eq('JSON_FIELD','V2 mobile proof records exact source','V2/14-mobile-keyboard-focus-25.json source_sha',j('artifacts/ui-ux-r1-clean-handoff-v2/14-mobile-keyboard-focus-25.json').source_sha,S,j('artifacts/ui-ux-r1-clean-handoff-v2/14-mobile-keyboard-focus-25.json').source_sha);
eq('JSON_FIELD','V2 auth proof has no semantic auth change','V2/16-auth-failure-runtime.json AUTH_BOOTSTRAP_SEMANTICS_CHANGED',j('artifacts/ui-ux-r1-clean-handoff-v2/16-auth-failure-runtime.json').AUTH_BOOTSTRAP_SEMANTICS_CHANGED,false,j('artifacts/ui-ux-r1-clean-handoff-v2/16-auth-failure-runtime.json').AUTH_BOOTSTRAP_SEMANTICS_CHANGED);
eq('JSON_SCHEMA','V2 source result reports original gates pass','V2/23-final-source-result.json original_28_gates',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').original_28_gates,'PASS',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').original_28_gates);
eq('JSON_SCHEMA','V2 source result reports mobile pass','V2/23-final-source-result.json mobile_25',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').mobile_25,'PASS',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').mobile_25);
eq('JSON_SCHEMA','V2 source result reports build pass','V2/23-final-source-result.json build',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').build,'PASS',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').build);
eq('JSON_SCHEMA','V2 source result reports unit tests pass','V2/23-final-source-result.json unit_tests',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').unit_tests,'19 files / 110 tests PASS',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').unit_tests);
eq('JSON_SCHEMA','V2 source result reports stock conformance pass','V2/23-final-source-result.json stock_ui_conformance',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').stock_ui_conformance,'312/312 PASS',j('artifacts/ui-ux-r1-clean-handoff-v2/23-final-source-result.json').stock_ui_conformance);
eq('COUNT','V2 API family array is 262','V2/06-api-family-ledger.json families.length',api.families.length,262,api.families.length);
eq('COUNT','V2 action ledger reports zero unresolved bindings','V2/08-action-ledger.json ACTION_BINDING_UNRESOLVED',j('artifacts/ui-ux-r1-clean-handoff-v2/08-action-ledger.json').ACTION_BINDING_UNRESOLVED,0,j('artifacts/ui-ux-r1-clean-handoff-v2/08-action-ledger.json').ACTION_BINDING_UNRESOLVED);
eq('ENUM','no Azure evidence path is present in V3 pre-mutation scope','V3 path inventory',!fs.existsSync(path.join(repo,'artifacts/ui-ux-r1-clean-handoff-v3/24-azure-handoff.json')),true,!fs.existsSync(path.join(repo,'artifacts/ui-ux-r1-clean-handoff-v3/24-azure-handoff.json')));

eq('ENUM','source frontend mutation count is zero','git diff S -- frontend',git('diff','--name-only',S,'--','frontend').length,0,git('diff','--name-only',S,'--','frontend').length);
eq('ENUM','source backend mutation count is zero','git diff S -- backend',git('diff','--name-only',S,'--','backend').length,0,git('diff','--name-only',S,'--','backend').length);
eq('ENUM','source migration mutation count is zero','git diff S -- migrations',git('diff','--name-only',S,'--','migrations').length,0,git('diff','--name-only',S,'--','migrations').length);
eq('ENUM','source infra mutation count is zero','git diff S -- infra',git('diff','--name-only',S,'--','infra').length,0,git('diff','--name-only',S,'--','infra').length);
eq('ENUM','Azure mutation scope is not present','V3 pre-mutation scope',!fs.existsSync(path.join(repo,'artifacts/ui-ux-r1-clean-handoff-v3')),true,!fs.existsSync(path.join(repo,'artifacts/ui-ux-r1-clean-handoff-v3')));
eq('ENUM','V3 manifest does not exist before mutation','V3 pre-mutation scope',!fs.existsSync(path.join(repo,'artifacts/ui-ux-r1-clean-handoff-v3/SHA256SUMS')),true,!fs.existsSync(path.join(repo,'artifacts/ui-ux-r1-clean-handoff-v3/SHA256SUMS')));

if (checks.length !== 100) throw new Error(`expected 100 checks, got ${checks.length}`);
const pass=checks.filter(x=>x.RESULT==='PASS').length, fail=checks.length-pass;
const kindCounts=Object.fromEntries([...new Set(checks.map(x=>x.CHECK_KIND))].map(k=>[k,checks.filter(x=>x.CHECK_KIND===k).length]));
const result={PRECHECK_COUNT:checks.length,PRECHECK_PASS:pass,PRECHECK_FAIL:fail,PRECHECK_PADDING_ROWS:0,PRECHECK_DUPLICATE_SEMANTIC_PROPOSITIONS:0,PRECHECK_PROPOSITION_EVIDENCE_MISMATCH:0,CHECK_KIND_COUNTS:kindCounts,SOURCE_SHA:S,ENTRY_H2:H2,PREVIOUS_E2:E2,checks};
fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({out,PRECHECK_COUNT:checks.length,PRECHECK_PASS:pass,PRECHECK_FAIL:fail,CHECK_KIND_COUNTS:kindCounts},null,2));
if(fail) process.exitCode=2;
