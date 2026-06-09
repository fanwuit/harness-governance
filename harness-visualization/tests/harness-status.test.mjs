import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { buildStatus, formatText } from '../scripts/harness-status.mjs';

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const sampleRepo = path.join(__dirname, 'fixtures', 'sample-repo');
const scriptPath = path.join(__dirname, '..', 'scripts', 'harness-status.mjs');

test('buildStatus summarizes harness layer, queue, packets, runner, and verification', async () => {
  const status = await buildStatus({ repo: sampleRepo });

  assert.equal(status.currentLayer, 'implementation');
  assert.deepEqual(status.readySummary, {
    total: 4,
    ready: 1,
    active: 1,
    blocked: 1,
    done: 1,
    other: 0,
  });
  assert.equal(status.taskPackets.length, 1);
  assert.equal(status.taskPackets[0].done, 2);
  assert.equal(status.taskPackets[0].total, 3);
  assert.equal(status.runner.lastMarker, 'AUTONOMOUS_READY_DONE');
  assert.equal(status.runner.lastRound, 4);
  assert.equal(status.verification.stale, false);
  assert.equal(status.warnings.length, 0);
});

test('formatText keeps the dashboard readable in terminals', async () => {
  const status = await buildStatus({ repo: sampleRepo });
  const text = formatText(status);

  assert.match(text, /Current layer: implementation/);
  assert.match(text, /\[active\] Parse runner records/);
  assert.match(text, /\[2\/3\] docs\/changes\/harness-visualization\/tasks.md/);
  assert.match(text, /Last marker: AUTONOMOUS_READY_DONE/);
});

test('CLI emits JSON for agent consumption', async () => {
  const { stdout } = await execFileAsync(process.execPath, [scriptPath, '--repo', sampleRepo, '--format', 'json']);
  const status = JSON.parse(stdout);

  assert.equal(status.currentLayer, 'implementation');
  assert.equal(status.readySummary.ready, 1);
  assert.equal(status.runner.lastMarker, 'AUTONOMOUS_READY_DONE');
});

test('write flags create status artifacts without mutating queues', async () => {
  const tempRepo = await mkdtemp(path.join(os.tmpdir(), 'harness-status-'));
  try {
    await execFileAsync(process.execPath, [
      scriptPath,
      '--repo',
      tempRepo,
      '--write-md',
      '--write-json',
      '--format',
      'json',
    ]);

    const markdown = await readFile(path.join(tempRepo, '.harness', 'status.md'), 'utf8');
    const json = JSON.parse(await readFile(path.join(tempRepo, '.harness', 'status.json'), 'utf8'));
    assert.match(markdown, /Current layer: unknown/);
    assert.equal(json.currentLayer, 'unknown');
    assert.ok(json.warnings.some((warning) => warning.includes('Queue file not found')));
  } finally {
    await rm(tempRepo, { recursive: true, force: true });
  }
});
