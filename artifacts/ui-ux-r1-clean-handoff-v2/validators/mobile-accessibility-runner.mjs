import { execFileSync } from 'node:child_process';
import path from 'node:path';

const repo = process.argv[2] || process.cwd();
execFileSync('npx', ['playwright', 'test', 'browser-e2e/mobile-accessibility-clean-handoff.spec.ts', '--config=playwright.config.ts'], { cwd: path.join(repo, 'frontend'), stdio: 'inherit', env: { ...process.env, PLAYWRIGHT_BASE_URL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:5174' } });
