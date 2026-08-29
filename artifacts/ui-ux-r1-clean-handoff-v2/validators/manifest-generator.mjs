import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const repo = process.argv[2] || process.cwd();
const root = path.join(repo, 'artifacts/ui-ux-r1-clean-handoff-v2');
const files = [];
function walk(dir) { for (const entry of fs.readdirSync(dir, { withFileTypes: true })) { const p = path.join(dir, entry.name); if (entry.isDirectory()) walk(p); else if (entry.isFile() && entry.name !== 'SHA256SUMS' && entry.name !== '24-azure-handoff.json') files.push(path.relative(repo, p)); } }
walk(root); files.sort();
const rows = files.map(file => ({ path: file, sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(repo, file))).digest('hex'), bytes: fs.statSync(path.join(repo, file)).size }));
fs.writeFileSync(path.join(root, 'SHA256SUMS'), rows.map(x => `${x.sha256}  ${x.path}`).join('\n') + '\n');
console.log(JSON.stringify({ file_count: rows.length, manifest: path.relative(repo, path.join(root, 'SHA256SUMS')) }, null, 2));
