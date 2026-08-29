import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';

const repo = process.argv[2] || process.cwd();
const root = path.join(repo, 'artifacts/ui-ux-r1-clean-handoff-v2');
const handoff = JSON.parse(fs.readFileSync(path.join(root, '24-azure-handoff.json'), 'utf8'));
const tip = execFileSync('git', ['rev-parse', 'origin/ui-product-r1-clean-handoff-v1'], { cwd: repo, encoding: 'utf8' }).trim();
const checks = [
  ['remote tip is H2', tip === handoff.UI_HANDOFF_RECORD_COMMIT],
  ['handoff source is frozen S', handoff.ACCEPTED_UI_SOURCE_SHA === '3f60c02ee7fdee385130b97b518f9060de1d42a8'],
  ['E2 is recorded', /^[0-9a-f]{40}$/.test(handoff.UI_EVIDENCE_PAYLOAD_COMMIT)],
  ['manifest exists', fs.existsSync(path.join(repo, handoff.PAYLOAD_MANIFEST_PATH))],
  ['source result exists', fs.existsSync(path.join(repo, handoff.SOURCE_RESULT_PATH))],
  ['pre checks pass', handoff.PREMUTATION_100_VALID === true],
  ['post checks pass', handoff.POST_EVIDENCE_100_VALID === true],
  ['28 gates pass', handoff.ORIGINAL_28_GATES === 'PASS'],
  ['624 crawl scenarios pass', handoff.ACTUAL_VIEWPORT_SCENARIOS === 624],
  ['unresolved total is zero', handoff.UNRESOLVED_TOTAL === 0],
];
if (checks.some(([, ok]) => !ok)) throw new Error(JSON.stringify(checks));
console.log(JSON.stringify({ FINAL_HANDOFF_VERIFIER: 'PASS', checks: checks.length }, null, 2));
