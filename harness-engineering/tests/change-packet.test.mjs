import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, '..', '..');
const templatesDir = path.join(repoRoot, 'harness-engineering', 'templates', 'change-packet');
const checkScript = path.join(repoRoot, 'harness-engineering', 'scripts', 'check-change-packet.mjs');
const initScript = path.join(repoRoot, 'harness-engineering', 'scripts', 'init-change-packet.mjs');

const requiredFiles = ['proposal.md', 'design.md', 'tasks.md', 'contracts.md', 'verification.md'];

async function makeTempRepo() {
  return mkdtemp(path.join(os.tmpdir(), 'change-packet-'));
}

async function writePacket(root, relativePacket, overrides = {}) {
  const packetDir = path.join(root, relativePacket);
  await mkdir(packetDir, { recursive: true });
  const files = {
    'proposal.md': '# Proposal\n\nStatus: active\n\n## Goal\nCreate packet checks.\n',
    'design.md': '# Design\n\n## Boundaries\nUse native harness packets only.\n',
    'tasks.md': '# Tasks\n\n- [x] Add templates\n- [ ] Run verification\n',
    'contracts.md': [
      '# Contracts',
      '',
      '## Current behavior',
      'No packet checker exists.',
      '',
      '## Proposed behavior / contract delta',
      'Packet checker validates native docs/changes packets.',
      '',
      '## Contract artifacts',
      '- check script: harness-engineering/scripts/check-change-packet.mjs',
      '',
      '## Acceptance checks',
      '- npm run check:packets',
      '',
      '## Failure cases',
      '- Missing packet files fail.',
      '',
    ].join('\n'),
    'verification.md': [
      '# Verification',
      '',
      '## Commands',
      '- npm run check:packets',
      '',
      '## Results',
      '- pass',
      '',
    ].join('\n'),
    ...overrides,
  };

  await Promise.all(
    Object.entries(files).map(([file, content]) => writeFile(path.join(packetDir, file), content, 'utf8')),
  );
  return packetDir;
}

async function runCheck(packetPath, repoRootArg) {
  const args = repoRootArg ? [checkScript, packetPath, '--repo', repoRootArg] : [checkScript, packetPath];
  return execFileAsync(process.execPath, args);
}

test('change packet templates exist and contain required sections', async () => {
  for (const file of requiredFiles) {
    const text = await readFile(path.join(templatesDir, file), 'utf8');
    assert.match(text, new RegExp(file.replace('.md', ''), 'i'));
  }

  const contracts = await readFile(path.join(templatesDir, 'contracts.md'), 'utf8');
  assert.match(contracts, /Current behavior/);
  assert.match(contracts, /Proposed behavior \/ contract delta/);
  assert.match(contracts, /Acceptance checks/);
  assert.match(contracts, /Failure cases/);
  assert.match(contracts, /文档说明不能替代可执行/);
});

test('init-change-packet creates a native packet from templates', async () => {
  const tempRepo = await makeTempRepo();

  await execFileAsync(process.execPath, [initScript, 'packet-checker', '--repo', tempRepo]);

  for (const file of requiredFiles) {
    const text = await readFile(path.join(tempRepo, 'docs', 'changes', 'packet-checker', file), 'utf8');
    assert.doesNotMatch(text, /\{\{CHANGE_ID\}\}/);
    assert.match(text, /packet-checker/);
  }
});

test('check-change-packet rejects an initialized packet until contract and verification evidence are filled', async () => {
  const tempRepo = await makeTempRepo();
  await execFileAsync(process.execPath, [initScript, 'draft-packet', '--repo', tempRepo]);

  await assert.rejects(
    runCheck('docs/changes/draft-packet', tempRepo),
    /contracts\.md must declare|verification\.md must record/,
  );
});

test('check-change-packet accepts a complete packet', async () => {
  const tempRepo = await makeTempRepo();
  await writePacket(tempRepo, 'docs/changes/native-packet');

  const { stdout } = await runCheck('docs/changes/native-packet', tempRepo);

  assert.match(stdout, /Change packet check passed/);
});

test('check-change-packet rejects missing files, missing checkbox, invalid status, missing contract, and missing verification', async () => {
  const tempRepo = await makeTempRepo();
  const packetDir = await writePacket(tempRepo, 'docs/changes/broken', {
    'proposal.md': '# Proposal\n\nStatus: pending\n',
    'tasks.md': '# Tasks\n\nNo checklist here.\n',
    'contracts.md': '# Contracts\n\n## Current behavior\nUnknown.\n',
    'verification.md': '# Verification\n\nNo evidence yet.\n',
  });
  await rm(path.join(packetDir, 'design.md'));

  await assert.rejects(
    runCheck('docs/changes/broken', tempRepo),
    /missing design\.md|tasks\.md must contain at least one checkbox|invalid status|contracts\.md must declare|verification\.md must record/i,
  );
});

test('check-change-packet rejects archived packets without stable conclusion backlinks', async () => {
  const tempRepo = await makeTempRepo();
  await writePacket(tempRepo, 'docs/changes/archive/2026-06-11-native-packet', {
    'proposal.md': '# Proposal\n\nStatus: archived\n',
  });

  await assert.rejects(
    runCheck('docs/changes/archive/2026-06-11-native-packet', tempRepo),
    /Archived packet must link stable conclusions/,
  );
});

test('README describes OpenSpec-like discipline without promising an OpenSpec adapter', async () => {
  const readme = await readFile(path.join(repoRoot, 'README.md'), 'utf8');

  assert.match(readme, /OpenSpec-like artifact discipline|OpenSpec-like artifact/i);
  assert.doesNotMatch(readme, /OpenSpec adapter/);
  assert.doesNotMatch(readme, /openspec\/changes/);
});
