import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
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
    total: 2,
    ready: 1,
    active: 1,
    blocked: 0,
    done: 0,
    other: 0,
  });
  assert.equal(status.queueSummary.total, 2);
  assert.equal(status.taskPackets.length, 1);
  assert.equal(status.taskPackets[0].done, 2);
  assert.equal(status.taskPackets[0].total, 3);
  assert.equal(status.archivedPackets.length, 1);
  assert.deepEqual(status.archiveSummary, {
    packets: 1,
    total: 2,
    done: 2,
    pending: 0,
    active: 0,
  });
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
  assert.match(text, /Done archive:/);
  assert.match(text, /\[2\/2\] docs\/changes\/archive\/2026-06-09-define-status-schema\/tasks.md/);
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

test('CLI init creates reusable project config', async () => {
  const tempRepo = await mkdtemp(path.join(os.tmpdir(), 'harness-status-init-'));
  try {
    const { stdout } = await execFileAsync(process.execPath, [scriptPath, '--repo', tempRepo, '--init']);
    const config = JSON.parse(await readFile(path.join(tempRepo, '.harness', 'harness-status.config.json'), 'utf8'));

    assert.match(stdout, /Created .harness\/harness-status.config.json/);
    assert.equal(config.schemaVersion, 1);
    assert.equal(config.queue, 'NEXT.md');
    assert.equal(config.archive, 'docs/changes/archive');
    assert.equal(config.statusJson, '.harness/status.json');
  } finally {
    await rm(tempRepo, { recursive: true, force: true });
  }
});

test('project config can move queue, changes root, and status outputs', async () => {
  const tempRepo = await mkdtemp(path.join(os.tmpdir(), 'harness-status-config-'));
  try {
    await mkdir(path.join(tempRepo, '.harness'), { recursive: true });
    await mkdir(path.join(tempRepo, 'work', 'changes', 'custom'), { recursive: true });
    await writeFile(path.join(tempRepo, 'QUEUE.md'), '[ready] Custom queue item\nLayer: contract\nChange: work/changes/custom/\n', 'utf8');
    await writeFile(path.join(tempRepo, 'work', 'changes', 'custom', 'tasks.md'), '- [x] Done\n- [ ] Pending\n', 'utf8');
    await writeFile(
      path.join(tempRepo, '.harness', 'harness-status.config.json'),
      `${JSON.stringify({
        schemaVersion: 1,
        queue: 'QUEUE.md',
        changes: 'work/changes',
        archive: 'work/changes/archive',
        statusMd: '.harness/custom-status.md',
        statusJson: '.harness/custom-status.json',
      }, null, 2)}\n`,
      'utf8',
    );

    await execFileAsync(process.execPath, [scriptPath, '--repo', tempRepo, '--write-md', '--write-json']);
    const markdown = await readFile(path.join(tempRepo, '.harness', 'custom-status.md'), 'utf8');
    const json = JSON.parse(await readFile(path.join(tempRepo, '.harness', 'custom-status.json'), 'utf8'));

    assert.match(markdown, /Custom queue item/);
    assert.equal(json.config.queue, 'QUEUE.md');
    assert.equal(json.config.changes, 'work/changes');
    assert.equal(json.config.archive, 'work/changes/archive');
    assert.equal(json.taskPackets[0].done, 1);
    assert.equal(json.taskPackets[0].total, 2);
  } finally {
    await rm(tempRepo, { recursive: true, force: true });
  }
});

test('legacy done queue items are preserved and warned for migration', async () => {
  const tempRepo = await mkdtemp(path.join(os.tmpdir(), 'harness-status-legacy-'));
  try {
    await writeFile(
      path.join(tempRepo, 'NEXT.md'),
      [
        '[done] Completed before archive existed',
        'Layer: contract',
        'Change: docs/changes/old-work/',
        '',
        '[ready] Continue current work',
        'Layer: verification',
        '',
        '[blocked] Waiting for credential',
        'Layer: implementation',
        'Stop: needs token',
        '',
      ].join('\n'),
      'utf8',
    );

    const status = await buildStatus({ repo: tempRepo });

    assert.equal(status.readySummary.total, 1);
    assert.equal(status.queueSummary.total, 3);
    assert.equal(status.legacyDoneItems.length, 1);
    assert.equal(status.legacyDoneItems[0].title, 'Completed before archive existed');
    assert.equal(status.nonSchedulerQueueItems.length, 2);
    assert.ok(status.warnings.some((warning) => warning.includes('completed item(s)')));
    assert.ok(status.warnings.some((warning) => warning.includes('non-scheduler item(s)')));
  } finally {
    await rm(tempRepo, { recursive: true, force: true });
  }
});

test('numbered scheduler queue items match documented NEXT examples', async () => {
  const tempRepo = await mkdtemp(path.join(os.tmpdir(), 'harness-status-numbered-'));
  try {
    await writeFile(
      path.join(tempRepo, 'NEXT.md'),
      [
        '## Active Queue',
        '1. [ready] Contract check',
        '   Layer: contract',
        '2) [active] Verification pass',
        '   Layer: verification',
        '',
      ].join('\n'),
      'utf8',
    );

    const status = await buildStatus({ repo: tempRepo });

    assert.equal(status.readySummary.total, 2);
    assert.equal(status.readySummary.ready, 1);
    assert.equal(status.readySummary.active, 1);
    assert.equal(status.readyItems[0].title, 'Contract check');
    assert.equal(status.readyItems[1].layer, 'verification');
  } finally {
    await rm(tempRepo, { recursive: true, force: true });
  }
});
