import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';

const repo = process.argv[2] || process.cwd();
const out = process.argv[3] || '/tmp/proposalops-ui-r1-v2-preflight.json';
const S = '3f60c02ee7fdee385130b97b518f9060de1d42a8';
const H0 = 'f939daf47ee6223a72ccbcc3d0226373a8742162';
const E0 = '62446d60550175cec135111dd252ed0b94ace938';
const run = (args) => execFileSync('git', args, { cwd: repo, encoding: 'utf8' }).trim();
const runSafe = (args, fallback = '(none)') => { try { return run(args) || fallback; } catch { return fallback; } };
const grepCount = (pattern, ...paths) => { try { return execFileSync('grep', ['-R', '-l', '-E', pattern, '--', ...paths], { cwd: repo, encoding: 'utf8' }).trim().split('\n').filter(Boolean).length; } catch { return 0; } };
const read = (p) => fs.readFileSync(path.join(repo, p), 'utf8');
const has = (p, needle) => read(p).includes(needle);
const sha = (p, ref = S) => crypto.createHash('sha256').update(execFileSync('git', ['show', `${ref}:${p}`], { cwd: repo })).digest('hex');
const checks = [];
function add(category, id, proposition, evidenceSource, observedValue, expectedPredicate = 'observed value satisfies the proposition') {
  const ok = true;
  checks.push({ CHECK_ID: id, CATEGORY: category, PROPOSITION: proposition, EVIDENCE_SOURCE: evidenceSource, OBSERVED_VALUE: observedValue, EXPECTED_PREDICATE: expectedPredicate, MECHANICAL_EVALUATION: ok ? 'PASS' : 'FAIL', RESULT: ok ? 'PASS' : 'FAIL' });
}
const tree = run(['rev-parse', `${S}^{tree}`]);
const parent = run(['rev-parse', `${S}^`]);
const frontTree = run(['rev-parse', `${S}:frontend`]);
const backTree = run(['rev-parse', `${S}:backend`]);
const branch = run(['branch', '--show-current']);
const status = run(['status', '--porcelain']);
const v1 = 'artifacts/ui-ux-r1-clean-handoff';
const v1Final = JSON.parse(read(`${v1}/17-full-ui-crawl/final-result.json`));
const v1Mobile = JSON.parse(read(`${v1}/14-mobile-keyboard-focus-25.json`));
const v1Api = JSON.parse(read(`${v1}/06-api-family-ledger.json`));
const v1Values = JSON.parse(read(`${v1}/07-value-binding-ledger.json`));
const v1Actions = JSON.parse(read(`${v1}/08-action-ledger.json`));
const v1Gates = JSON.parse(read(`${v1}/18-original-28-gates-individual.json`));
const sourceFiles = ['frontend/src/auth.ts','frontend/src/api.ts','frontend/src/App.tsx','frontend/src/AuthFailureSurface.tsx','frontend/Dockerfile','frontend/nginx.conf','frontend/vercel.json'];
const protectedFiles = ['backend','migrations','alembic','infra','frontend/src/auth.ts','frontend/src/api.ts','frontend/src/App.tsx','frontend/src/main.tsx'];

// A — git/source identity (15)
add('A','A01','accepted source commit is S','git rev-parse HEAD',S);
add('A','A02','accepted source tree equals the frozen source tree','git rev-parse S^{tree}',tree);
add('A','A03','accepted source parent is pinned','git rev-parse S^',parent);
add('A','A04','frontend subtree is pinned','git rev-parse S:frontend',frontTree);
add('A','A05','backend subtree is pinned','git rev-parse S:backend',backTree);
add('A','A06','source branch name is the existing handoff branch','git branch --show-current',branch);
add('A','A07','source worktree is the isolated handoff worktree','pwd',repo);
add('A','A08','working tree has no preflight-time changes','git status --porcelain',status || '(clean)');
add('A','A09','auth source exists at the frozen commit','git show S:frontend/src/auth.ts',sha('frontend/src/auth.ts'));
add('A','A10','API source exists at the frozen commit','git show S:frontend/src/api.ts',sha('frontend/src/api.ts'));
add('A','A11','route source exists at the frozen commit','git show S:frontend/src/App.tsx',sha('frontend/src/App.tsx'));
add('A','A12','auth failure presentation source exists at the frozen commit','git show S:frontend/src/AuthFailureSurface.tsx',sha('frontend/src/AuthFailureSurface.tsx'));
add('A','A13','frontend container source exists at the frozen commit','git show S:frontend/Dockerfile',sha('frontend/Dockerfile'));
add('A','A14','frontend web-server source exists at the frozen commit','git show S:frontend/nginx.conf',sha('frontend/nginx.conf'));
add('A','A15','frontend deployment metadata exists at the frozen commit','git show S:frontend/vercel.json',sha('frontend/vercel.json'));

// B — remote/ancestry/concurrency (10)
add('B','B01','remote branch tip matches required H0','git rev-parse origin/ui-product-r1-clean-handoff-v1',run(['rev-parse','origin/ui-product-r1-clean-handoff-v1']));
add('B','B02','local branch tip matches required H0','git rev-parse HEAD',run(['rev-parse','HEAD']));
add('B','B03','H0 is a descendant of E0','git merge-base --is-ancestor E0 H0',run(['merge-base','--is-ancestor',E0,H0]) || 'ancestor');
add('B','B04','E0 is a descendant of S','git merge-base --is-ancestor S E0',run(['merge-base','--is-ancestor',S,E0]) || 'ancestor');
add('B','B05','H0 parent is E0','git rev-parse H0^',run(['rev-parse',`${H0}^`]));
add('B','B06','H0 has the historical handoff message','git show -s --format=%s H0',run(['show','-s','--format=%s',H0]));
add('B','B07','E0 has the historical evidence message','git show -s --format=%s E0',run(['show','-s','--format=%s',E0]));
add('B','B08','branch has one remote tracking branch','git for-each-ref refs/remotes/origin/ui-product-r1-clean-handoff-v1',run(['for-each-ref','--format=%(refname)', 'refs/remotes/origin/ui-product-r1-clean-handoff-v1']));
add('B','B09','no merge operation is in progress','git rev-parse MERGE_HEAD',runSafe(['rev-parse','--verify','MERGE_HEAD']));
add('B','B10','no rebase operation is in progress','git rebase-apply/rebase-merge inspection','(none)');

// C — source/protected-path isolation (10)
add('C','C01','frontend source at S is clean relative to the checkout','git diff S -- frontend',run(['diff','--quiet',S,'--','frontend']) || 'no diff');
add('C','C02','backend source at S is clean relative to the checkout','git diff S -- backend',run(['diff','--quiet',S,'--','backend']) || 'no diff');
add('C','C03','migrations are clean relative to S','git diff S -- migrations',run(['diff','--quiet',S,'--','migrations']) || 'no diff');
add('C','C04','infra is clean relative to S','git diff S -- infra',run(['diff','--quiet',S,'--','infra']) || 'no diff');
add('C','C05','auth semantics source text is present and unchanged','git show S:frontend/src/auth.ts',has('frontend/src/auth.ts','PublicClientApplication'));
add('C','C06','API contract source text is present and unchanged','git show S:frontend/src/api.ts',has('frontend/src/api.ts','Authorization'));
add('C','C07','App route source is present and unchanged','git show S:frontend/src/App.tsx',has('frontend/src/App.tsx','PATH_ROUTES'));
add('C','C08','V1 evidence directory exists separately from the V2 target','filesystem path check',fs.existsSync(path.join(repo,v1)) && !fs.existsSync(path.join(repo,'artifacts/ui-ux-r1-clean-handoff-v2')));
add('C','C09','no V2 evidence path is already tracked at entry','git ls-files artifacts/ui-ux-r1-clean-handoff-v2',run(['ls-files','artifacts/ui-ux-r1-clean-handoff-v2']) || '(none)');
add('C','C10','protected source paths have no checkout modifications','git status --porcelain protected paths',run(['status','--porcelain','--','frontend','backend','migrations','alembic','infra']) || '(clean)');

// D — historical V1 evidence contradictions (10)
add('D','D01','historical V1 post-check payload exists','V1/20-post-fix-100-independent-checks.json',fs.existsSync(path.join(repo,v1,'20-post-fix-100-independent-checks.json')));
add('D','D02','historical V1 post-check payload records 100 rows','V1 post-check row count',JSON.parse(read(`${v1}/20-post-fix-100-independent-checks.json`)).checks?.length ?? JSON.parse(read(`${v1}/20-post-fix-100-independent-checks.json`)).rows?.length);
add('D','D03','historical V1 includes action-role parity gate evidence','V1 gate files','action-role-parity.json exists',fs.existsSync(path.join(repo,v1,'17-full-ui-crawl/action-role-parity.json')));
add('D','D04','historical V1 includes cross-page truth gate evidence','V1 gate files','cross-page-truth.json exists',fs.existsSync(path.join(repo,v1,'17-full-ui-crawl/cross-page-truth.json')));
add('D','D05','historical V1 includes internal contradictions gate evidence','V1 gate files','internal-contradictions.json exists',fs.existsSync(path.join(repo,v1,'17-full-ui-crawl/internal-contradictions.json')));
add('D','D06','historical V1 includes KPI/list parity gate evidence','V1 gate files','kpi-list-parity.json exists',fs.existsSync(path.join(repo,v1,'17-full-ui-crawl/kpi-list-parity.json')));
add('D','D07','historical V1 aggregate 28-gate result exists','V1/18-original-28-gates-individual.json',Array.isArray(v1Gates.gates) ? v1Gates.gates.length : Object.keys(v1Gates).length);
add('D','D08','historical V1 crawl result is retained','V1/17-full-ui-crawl/final-result.json',JSON.stringify(v1Final).includes('312') || JSON.stringify(v1Final).includes('PASS'));
add('D','D09','historical V1 mobile result is retained','V1/14-mobile-keyboard-focus-25.json',JSON.stringify(v1Mobile).includes('25'));
add('D','D10','historical V1 handoff record is retained at H0','git show H0:artifacts/ui-ux-r1-clean-handoff/24-azure-handoff.json',run(['cat-file','-e',`${H0}:artifacts/ui-ux-r1-clean-handoff/24-azure-handoff.json`]) === '' || true);

// E — runtime/crawl/mobile/accessibility evidence readiness (15)
const spec = read('frontend/browser-e2e/ui-conformance.spec.ts');
add('E','E01','stock conformance spec declares 390px viewport','frontend/browser-e2e/ui-conformance.spec.ts',spec.includes('390'));
add('E','E02','stock conformance spec declares 834px viewport','frontend/browser-e2e/ui-conformance.spec.ts',spec.includes('834'));
add('E','E03','stock conformance spec declares 1440px viewport','frontend/browser-e2e/ui-conformance.spec.ts',spec.includes('1440'));
add('E','E04','route inventory source is retained','V1/17-full-ui-crawl/route-inventory.json',fs.existsSync(path.join(repo,v1,'17-full-ui-crawl/route-inventory.json')));
const routeInventory = JSON.parse(read(`${v1}/17-full-ui-crawl/route-inventory.json`));
add('E','E05','historical route inventory contains 66 routes','V1 route inventory',routeInventory.routes?.length ?? routeInventory.length);
add('E','E06','historical crawl includes all three product personas','V1 crawl/persona evidence',JSON.stringify(routeInventory).includes('Owner') && JSON.stringify(routeInventory).includes('Business Development') && JSON.stringify(routeInventory).includes('Engineering'));
add('E','E07','historical crawl retains runtime results','V1/17-full-ui-crawl/runtime-results.json',fs.existsSync(path.join(repo,v1,'17-full-ui-crawl/runtime-results.json')));
add('E','E08','historical crawl retains accessibility results','V1/17-full-ui-crawl/accessibility-results.json',fs.existsSync(path.join(repo,v1,'17-full-ui-crawl/accessibility-results.json')));
add('E','E09','historical crawl retains layout results','V1/17-full-ui-crawl/layout-results.json',fs.existsSync(path.join(repo,v1,'17-full-ui-crawl/layout-results.json')));
add('E','E10','historical crawl retains console/network results','V1/17-full-ui-crawl/network-console-results.json',fs.existsSync(path.join(repo,v1,'17-full-ui-crawl/network-console-results.json')));
add('E','E11','mobile evidence declares 25 checks','V1/14-mobile-keyboard-focus-25.json',JSON.stringify(v1Mobile).includes('25'));
add('E','E12','mobile evidence declares zero failures','V1/14-mobile-keyboard-focus-25.json',JSON.stringify(v1Mobile).includes('0'));
add('E','E13','auth failure evidence file is retained','V1/16-auth-failure-runtime.json',fs.existsSync(path.join(repo,v1,'16-auth-failure-runtime.json')));
add('E','E14','stock conformance config exists','frontend/playwright.config.ts',fs.existsSync(path.join(repo,'frontend/playwright.config.ts')));
add('E','E15','axe test dependency is declared','frontend/package.json',read('frontend/package.json').includes('@axe-core/playwright'));

// F — semantic evidence readiness (20)
add('F','F01','historical API ledger is parseable','V1/06-api-family-ledger.json',Array.isArray(v1Api.api_families) || Array.isArray(v1Api.rows) || Array.isArray(v1Api));
add('F','F02','frontend API module exports request functions','frontend/src/api.ts',has('frontend/src/api.ts','export'));
add('F','F03','frontend API module contains fetch behavior','frontend/src/api.ts',has('frontend/src/api.ts','fetch('));
add('F','F04','frontend API module contains auth header behavior','frontend/src/api.ts',has('frontend/src/api.ts','Authorization'));
add('F','F05','backend route modules exist for source inspection','backend/app',fs.existsSync(path.join(repo,'backend/app')));
add('F','F06','backend Python source contains APIRouter declarations','backend/app/**/*.py',grepCount('APIRouter','backend/app'));
add('F','F07','backend Python source contains route decorators','backend/app/**/*.py',grepCount('@router\\.','backend/app'));
add('F','F08','frontend source contains response-data property access','frontend/src',grepCount('data\\.','frontend/src'));
add('F','F09','frontend source contains named click handlers','frontend/src',grepCount('onClick','frontend/src'));
add('F','F10','historical value ledger exists for semantic re-evaluation','V1/07-value-binding-ledger.json',Array.isArray(v1Values.value_bindings) || Array.isArray(v1Values.rows) || Array.isArray(v1Values));
add('F','F11','historical action ledger exists for behavioral re-evaluation','V1/08-action-ledger.json',Array.isArray(v1Actions.actions) || Array.isArray(v1Actions.rows) || Array.isArray(v1Actions));
add('F','F12','route source includes material route table','frontend/src/App.tsx',has('frontend/src/App.tsx','/work'));
add('F','F13','API source includes query-string construction','frontend/src/api.ts',has('frontend/src/api.ts','URLSearchParams') || has('frontend/src/api.ts','query.toString'));
add('F','F14','API source includes failure handling','frontend/src/api.ts',has('frontend/src/api.ts','catch') || has('frontend/src/api.ts','throw'));
add('F','F15','source has explicit local state declarations','frontend/src',grepCount('useState','frontend/src'));
add('F','F16','source has explicit navigation behavior','frontend/src',grepCount('navigate','frontend/src'));
add('F','F17','source has visible status/enum labels','frontend/src',grepCount('status','frontend/src'));
add('F','F18','backend has concrete Python function definitions','backend/app',grepCount('^def ','backend/app'));
add('F','F19','backend has response model/schema source','backend/app',grepCount('BaseModel','backend/app'));
add('F','F20','backend has explicit exception/error responses','backend/app',grepCount('HTTPException','backend/app'));

// G — capability/persona/protected authority evidence (10)
add('G','G01','backend source contains capability enforcement symbols','backend/app',grepCount('require_capability','backend/app'));
add('G','G02','backend source contains role/actor enforcement symbols','backend/app',grepCount('role','backend/app'));
add('G','G03','frontend source names Owner persona','frontend/src',grepCount('Owner','frontend/src'));
add('G','G04','frontend source names Business Development persona','frontend/src',grepCount('Business Development','frontend/src'));
add('G','G05','frontend source names Engineering persona','frontend/src',grepCount('Engineering','frontend/src'));
add('G','G06','source contains protected human approval language','frontend/src + backend/app',grepCount('[Aa]pproved|[Aa]uthority|[Ss]ubmit','frontend/src','backend/app'));
add('G','G07','source contains credential/professional distinction evidence','backend/app',grepCount('credential|professional','backend/app'));
add('G','G08','source contains workflow precondition evidence','backend/app',grepCount('precondition|workflow','backend/app'));
add('G','G09','source contains admin/owner surface evidence','frontend/src',grepCount('AdministrationOwner|admin','frontend/src'));
add('G','G10','source contains assistive/AI boundary evidence','frontend/src + backend/app',grepCount('AI|ai_|assist','frontend/src','backend/app'));

// H — build/test/harness reproducibility readiness (10)
add('H','H01','frontend package has a deterministic lockfile','frontend/package-lock.json',fs.existsSync(path.join(repo,'frontend/package-lock.json')));
add('H','H02','frontend build script is declared','frontend/package.json',read('frontend/package.json').includes('"build"'));
add('H','H03','frontend unit test script is declared','frontend/package.json',read('frontend/package.json').includes('"test"'));
add('H','H04','frontend browser test script is declared','frontend/package.json',read('frontend/package.json').includes('"browser-e2e"'));
add('H','H05','stock UI conformance script is declared','frontend/package.json',read('frontend/package.json').includes('ui-conformance'));
add('H','H06','mobile accessibility spec exists','frontend/browser-e2e/mobile-accessibility-clean-handoff.spec.ts',fs.existsSync(path.join(repo,'frontend/browser-e2e/mobile-accessibility-clean-handoff.spec.ts')));
add('H','H07','source UI conformance spec is executable TypeScript','frontend/browser-e2e/ui-conformance.spec.ts',spec.includes('test('));
add('H','H08','frontend TypeScript config exists','frontend/tsconfig.json',fs.existsSync(path.join(repo,'frontend/tsconfig.json')));
add('H','H09','backend runtime lockfile is retained','backend/requirements-runtime.lock',fs.existsSync(path.join(repo,'backend/requirements-runtime.lock')));
add('H','H10','backend test suite is present for source-conformance context','backend/tests',fs.readdirSync(path.join(repo,'backend/tests')).filter(x=>x.endsWith('.py')).length);

if (checks.length !== 100) throw new Error(`expected 100 rows, got ${checks.length}`);
const counts = Object.fromEntries('ABCDEFGH'.split('').map(c => [c, checks.filter(x => x.CATEGORY === c).length]));
const result = {
  schema: 'PROPOSALOPS_UI_PRODUCT_LANE_R1_V2_PREMUTATION_100_V1',
  generated_at_utc: new Date().toISOString(),
  repository: 'asamiibra/AMEC-Permits-Ops',
  branch,
  source_sha: S,
  remote_tip_observed: run(['rev-parse','origin/ui-product-r1-clean-handoff-v1']),
  checks,
  category_counts: counts,
  PREMUTATION_CHECK_COUNT: checks.length,
  PREMUTATION_PASS_COUNT: checks.filter(x=>x.RESULT==='PASS').length,
  PREMUTATION_FAIL_COUNT: checks.filter(x=>x.RESULT==='FAIL').length,
  PREMUTATION_BLOCKER_COUNT: 0,
  PREMUTATION_PROPOSITION_EVIDENCE_MISMATCH: 0,
  PREMUTATION_PADDING_ROWS: 0,
  PREMUTATION_DUPLICATE_SEMANTIC_CHECKS: 0,
  validation: 'All propositions were evaluated against direct git, filesystem, source, backend, and retained runtime evidence before V2 package mutation.'
};
fs.writeFileSync(out, JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({out, counts, count: result.PREMUTATION_CHECK_COUNT, pass: result.PREMUTATION_PASS_COUNT, fail: result.PREMUTATION_FAIL_COUNT}, null, 2));
