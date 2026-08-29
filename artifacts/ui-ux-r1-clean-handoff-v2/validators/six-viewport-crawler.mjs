import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const repo = process.argv[2] || process.cwd();
const sourceSpec = path.join(repo, 'frontend/browser-e2e/ui-conformance.spec.ts');
const outputRoot = path.join(repo, 'artifacts/ui-ux-r1-clean-handoff-v2/17-full-ui-crawl');
const viewports = 'const viewports = { v390: { width: 390, height: 844 }, v834: { width: 834, height: 1112 }, v1024: { width: 1024, height: 900 }, v1280: { width: 1280, height: 900 }, v1440: { width: 1440, height: 1000 }, v1920: { width: 1920, height: 1080 } };';
const auditRoot = 'const auditRoot = path.join(repoRoot, "artifacts", "ui-ux-r1-clean-handoff-v2", "17-full-ui-crawl");';
if (!fs.existsSync(sourceSpec)) throw new Error(`missing frozen stock spec: ${sourceSpec}`);
const rewritten = fs.readFileSync(sourceSpec, 'utf8').replace(/const viewports = \{[^;]+\};/, viewports).replace('const auditRoot = path.join(repoRoot, "artifacts", "ui-conformance");', auditRoot);
const tempSpec = path.join(repo, 'frontend/browser-e2e/ui-conformance-six.v2.generated.spec.ts');
fs.writeFileSync(tempSpec, rewritten);
try { execFileSync('npx', ['playwright', 'test', 'browser-e2e/ui-conformance-six.v2.generated.spec.ts', '--config=playwright.config.ts'], { cwd: path.join(repo, 'frontend'), stdio: 'inherit', env: { ...process.env, PLAYWRIGHT_BASE_URL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:5174' } }); } finally { fs.rmSync(tempSpec, { force: true }); }
if (!fs.existsSync(path.join(outputRoot, 'runtime-results.json'))) throw new Error('six-viewport runtime result was not produced');
