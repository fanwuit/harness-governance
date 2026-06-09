#!/usr/bin/env node
import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const LAYERS = [
  'intake-orientation',
  'idea',
  'fact-discovery',
  'brainstorming',
  'brief',
  'architecture',
  'adr',
  'contract',
  'readiness',
  'implementation',
  'verification',
  'review-next',
];

const MARKER_PATTERN = /\bAUTONOMOUS_(?:READY_DONE|CONTEXT_HANDOFF|BLOCKED|BOUNDARY_REACHED|FAILED)\b/;

function normalizeStatus(value) {
  return String(value || '').trim().toLowerCase().replace(/\s+/g, '-');
}

function normalizeFieldName(value) {
  return String(value || '').trim().toLowerCase().replace(/[\s/-]+/g, '');
}

async function readText(filePath) {
  try {
    return await readFile(filePath, 'utf8');
  } catch (error) {
    if (error && error.code === 'ENOENT') return null;
    throw error;
  }
}

function parseArgs(argv) {
  const options = {
    repo: process.cwd(),
    queue: 'NEXT.md',
    checkpoint: '.harness/run-checkpoint.md',
    invocationLog: '.harness/codex-exec-invocations.ndjson',
    format: 'text',
    writeMd: false,
    writeJson: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === '--repo') {
      options.repo = next;
      index += 1;
    } else if (arg === '--queue') {
      options.queue = next;
      index += 1;
    } else if (arg === '--checkpoint') {
      options.checkpoint = next;
      index += 1;
    } else if (arg === '--invocation-log') {
      options.invocationLog = next;
      index += 1;
    } else if (arg === '--format') {
      options.format = next;
      index += 1;
    } else if (arg === '--json') {
      options.format = 'json';
    } else if (arg === '--write-md') {
      options.writeMd = true;
    } else if (arg === '--write-json') {
      options.writeJson = true;
    } else if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!['text', 'json', 'markdown'].includes(options.format)) {
    throw new Error('--format must be text, json, or markdown');
  }

  return options;
}

function parseQueueMarkdown(content, queuePath = 'NEXT.md') {
  if (!content) return [];

  const items = [];
  let current = null;
  const lines = content.split(/\r?\n/);

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const itemMatch = line.match(/^\s*(?:[-*]\s*)?\[([^\]]+)\]\s+(.+?)\s*$/);
    if (itemMatch) {
      current = {
        status: normalizeStatus(itemMatch[1]),
        title: itemMatch[2].trim(),
        line: index + 1,
        queuePath,
        fields: {},
      };
      items.push(current);
      continue;
    }

    if (!current) continue;
    const fieldMatch = line.match(/^\s*([A-Za-z][A-Za-z /-]*):\s*(.+?)\s*$/);
    if (!fieldMatch) continue;

    const key = normalizeFieldName(fieldMatch[1]);
    current.fields[key] = fieldMatch[2].trim();
  }

  return items.map((item) => ({
    ...item,
    layer: item.fields.layer || null,
    change: item.fields.change || null,
    packetization: item.fields.packetization || null,
    evidence: item.fields.evidence || null,
    target: item.fields.target || null,
    contract: item.fields.contract || null,
  }));
}

function summarizeReady(items) {
  const summary = { total: items.length, ready: 0, active: 0, blocked: 0, done: 0, other: 0 };
  for (const item of items) {
    if (Object.prototype.hasOwnProperty.call(summary, item.status)) {
      summary[item.status] += 1;
    } else {
      summary.other += 1;
    }
  }
  return summary;
}

function inferCurrentLayer(items) {
  const active = items.find((item) => item.status === 'active' && item.layer);
  if (active) return active.layer;
  const ready = items.find((item) => item.status === 'ready' && item.layer);
  if (ready) return ready.layer;
  const blocked = items.find((item) => item.status === 'blocked' && item.layer);
  if (blocked) return blocked.layer;
  const any = items.find((item) => item.layer);
  return any ? any.layer : 'unknown';
}

function buildLayerTimeline(currentLayer) {
  const currentIndex = LAYERS.indexOf(currentLayer);
  return LAYERS.map((label, index) => {
    let status = 'unknown';
    if (currentIndex >= 0) {
      status = index < currentIndex ? 'done' : index === currentIndex ? 'current' : 'pending';
    }
    return { label, status };
  });
}

function parseTaskMarkdown(content, tasksPath) {
  const items = [];
  const lines = content.split(/\r?\n/);

  for (let index = 0; index < lines.length; index += 1) {
    const match = lines[index].match(/^\s*[-*]\s+\[([ xX~\-])\]\s+(.+?)\s*$/);
    if (!match) continue;
    const marker = match[1];
    items.push({
      text: match[2].trim(),
      checked: marker.toLowerCase() === 'x',
      active: marker === '~' || marker === '-',
      line: index + 1,
    });
  }

  const done = items.filter((item) => item.checked).length;
  const active = items.filter((item) => item.active).length;
  return {
    tasksPath,
    total: items.length,
    done,
    pending: items.length - done,
    active,
    items,
  };
}

async function pathExists(dirPath) {
  try {
    await stat(dirPath);
    return true;
  } catch (error) {
    if (error && error.code === 'ENOENT') return false;
    throw error;
  }
}

async function discoverChangeDirs(repoPath, readyItems) {
  const found = new Map();
  for (const item of readyItems) {
    if (!item.change) continue;
    const absolute = path.resolve(repoPath, item.change);
    found.set(absolute, item.change);
  }

  const changesRoot = path.join(repoPath, 'docs', 'changes');
  if (await pathExists(changesRoot)) {
    const entries = await readdir(changesRoot, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const absolute = path.join(changesRoot, entry.name);
      found.set(absolute, path.relative(repoPath, absolute).replace(/\\/g, '/'));
    }
  }

  return [...found.entries()].map(([absolute, relative]) => ({ absolute, relative }));
}

async function readTaskPackets(repoPath, readyItems, warnings) {
  const packets = [];
  const dirs = await discoverChangeDirs(repoPath, readyItems);

  for (const dir of dirs) {
    const tasksPath = path.join(dir.absolute, 'tasks.md');
    const content = await readText(tasksPath);
    if (!content) {
      warnings.push(`Change packet has no tasks.md: ${dir.relative}`);
      continue;
    }
    const packet = parseTaskMarkdown(content, path.relative(repoPath, tasksPath).replace(/\\/g, '/'));
    packet.changePath = dir.relative;
    packets.push(packet);
  }

  return packets;
}

function parseCheckpoint(content, checkpointPath) {
  if (!content) return { checkpointPath, found: false };

  const result = {
    checkpointPath,
    found: true,
    startedAt: null,
    queueItem: null,
    result: null,
    stopReason: null,
    verificationLines: [],
  };

  let section = '';
  for (const line of content.split(/\r?\n/)) {
    const sectionMatch = line.match(/^##\s+(.+?)\s*$/);
    if (sectionMatch) {
      section = sectionMatch[1].trim().toLowerCase();
      continue;
    }
    const fieldMatch = line.match(/^\s*-\s*([^:]+):\s*(.+?)\s*$/);
    if (fieldMatch) {
      const key = fieldMatch[1].trim().toLowerCase();
      const value = fieldMatch[2].trim();
      if (key === 'started') result.startedAt = value;
      if (key === 'queue item') result.queueItem = value;
      if (key === 'result') result.result = value;
      if (section === 'stop reason') result.stopReason = `${key}: ${value}`;
    }
    if (section === 'verification' && line.trim().startsWith('-')) {
      result.verificationLines.push(line.trim().replace(/^-\s*/, ''));
    }
  }

  return result;
}

function parseInvocationLog(content, warnings) {
  if (!content) return [];

  const records = [];
  const lines = content.split(/\r?\n/).filter((line) => line.trim());
  for (let index = 0; index < lines.length; index += 1) {
    try {
      records.push(JSON.parse(lines[index]));
    } catch (error) {
      warnings.push(`Could not parse invocation log line ${index + 1}: ${error.message}`);
    }
  }
  return records;
}

async function readLastMarker(repoPath, invocations) {
  const last = invocations.at(-1);
  if (last && last.marker) return last.marker;

  const messagePath = path.join(repoPath, '.harness', 'last-codex-message.md');
  const message = await readText(messagePath);
  if (!message) return null;
  const match = message.match(MARKER_PATTERN);
  return match ? match[0] : null;
}

function summarizeVerification(checkpoint, invocations) {
  const last = invocations.at(-1);
  const sourceLines = checkpoint.verificationLines || [];
  const summary = last?.verificationSummary || last?.verification || sourceLines.join('; ') || null;
  const text = String(summary || '').toLowerCase();
  const hasPass = /\bpass(?:ed)?\b|->\s*pass\b/.test(text);
  const hasFail = /\bfail(?:ed)?\b|->\s*fail\b/.test(text);
  return {
    summary,
    stale: !summary || hasFail || !hasPass,
    failed: hasFail,
    source: last?.verificationSummary || last?.verification ? 'invocation-log' : sourceLines.length ? 'checkpoint' : 'missing',
  };
}

export async function buildStatus(options = {}) {
  const repoPath = path.resolve(options.repo || process.cwd());
  const queue = options.queue || 'NEXT.md';
  const checkpoint = options.checkpoint || '.harness/run-checkpoint.md';
  const invocationLog = options.invocationLog || '.harness/codex-exec-invocations.ndjson';
  const warnings = [];

  const queuePath = path.join(repoPath, queue);
  const queueContent = await readText(queuePath);
  if (!queueContent) warnings.push(`Queue file not found: ${queue}`);
  const readyItems = parseQueueMarkdown(queueContent, queue);

  const currentLayer = inferCurrentLayer(readyItems);
  const taskPackets = await readTaskPackets(repoPath, readyItems, warnings);
  const checkpointData = parseCheckpoint(await readText(path.join(repoPath, checkpoint)), checkpoint);
  if (!checkpointData.found) warnings.push(`Checkpoint not found: ${checkpoint}`);

  const invocations = parseInvocationLog(await readText(path.join(repoPath, invocationLog)), warnings);
  if (invocations.length === 0) warnings.push(`Invocation log not found or empty: ${invocationLog}`);

  const lastInvocation = invocations.at(-1) || null;
  const lastMarker = await readLastMarker(repoPath, invocations);
  const verification = summarizeVerification(checkpointData, invocations);
  if (verification.stale) warnings.push('Verification is missing, failed, or stale.');

  return {
    repo: repoPath,
    generatedAt: new Date().toISOString(),
    currentLayer,
    layerTimeline: buildLayerTimeline(currentLayer),
    readySummary: summarizeReady(readyItems),
    readyItems,
    taskPackets,
    runner: {
      checkpoint: checkpointData,
      invocationLog,
      invocationCount: invocations.length,
      lastInvocation,
      lastMarker,
      lastRound: lastInvocation?.round || null,
      lastExitCode: Number.isInteger(lastInvocation?.exitCode) ? lastInvocation.exitCode : null,
    },
    verification,
    warnings,
  };
}

export function formatMarkdown(status) {
  const timeline = status.layerTimeline
    .map((layer) => {
      if (layer.status === 'current') return `[${layer.label}]`;
      if (layer.status === 'done') return `${layer.label}`;
      return `(${layer.label})`;
    })
    .join(' -> ');

  const lines = [
    '# Harness Status',
    '',
    `Generated: ${status.generatedAt}`,
    `Repo: ${status.repo}`,
    '',
    `Harness: ${timeline}`,
    `Current layer: ${status.currentLayer}`,
    '',
    '## Ready Queue',
    '',
    `Total: ${status.readySummary.total}; ready: ${status.readySummary.ready}; active: ${status.readySummary.active}; blocked: ${status.readySummary.blocked}; done: ${status.readySummary.done}; other: ${status.readySummary.other}`,
    '',
  ];

  if (status.readyItems.length === 0) {
    lines.push('- No queue items found.');
  } else {
    for (const item of status.readyItems) {
      const details = [
        item.layer ? `Layer: ${item.layer}` : null,
        item.change ? `Change: ${item.change}` : null,
        item.packetization ? `Packetization: ${item.packetization}` : null,
      ].filter(Boolean).join('; ');
      lines.push(`- [${item.status}] ${item.title}${details ? ` (${details})` : ''}`);
    }
  }

  lines.push('', '## Task Packets', '');
  if (status.taskPackets.length === 0) {
    lines.push('- No task packets found.');
  } else {
    for (const packet of status.taskPackets) {
      lines.push(`- [${packet.done}/${packet.total}] ${packet.tasksPath}`);
    }
  }

  lines.push('', '## Runner', '');
  lines.push(`- Last marker: ${status.runner.lastMarker || 'unknown'}`);
  lines.push(`- Last round: ${status.runner.lastRound || 'unknown'}`);
  lines.push(`- Last exit code: ${status.runner.lastExitCode ?? 'unknown'}`);
  lines.push(`- Checkpoint result: ${status.runner.checkpoint.result || 'unknown'}`);
  lines.push(`- Stop reason: ${status.runner.checkpoint.stopReason || 'none'}`);

  lines.push('', '## Verification', '');
  lines.push(`- Source: ${status.verification.source}`);
  lines.push(`- Stale: ${status.verification.stale ? 'yes' : 'no'}`);
  lines.push(`- Summary: ${status.verification.summary || 'missing'}`);

  lines.push('', '## Warnings', '');
  if (status.warnings.length === 0) {
    lines.push('- none');
  } else {
    for (const warning of status.warnings) lines.push(`- ${warning}`);
  }

  return `${lines.join('\n')}\n`;
}

export function formatText(status) {
  const lines = [
    `Harness status for ${status.repo}`,
    `Current layer: ${status.currentLayer}`,
    `Ready queue: total=${status.readySummary.total} ready=${status.readySummary.ready} active=${status.readySummary.active} blocked=${status.readySummary.blocked} done=${status.readySummary.done} other=${status.readySummary.other}`,
    '',
    'Ready items:',
  ];

  if (status.readyItems.length === 0) {
    lines.push('- none');
  } else {
    for (const item of status.readyItems) {
      const details = [
        item.layer ? `layer=${item.layer}` : null,
        item.change ? `change=${item.change}` : null,
        item.packetization ? `packetization=${item.packetization}` : null,
      ].filter(Boolean).join(' ');
      lines.push(`- [${item.status}] ${item.title}${details ? ` (${details})` : ''}`);
    }
  }

  lines.push('', 'Task packets:');
  if (status.taskPackets.length === 0) {
    lines.push('- none');
  } else {
    for (const packet of status.taskPackets) {
      lines.push(`- [${packet.done}/${packet.total}] ${packet.tasksPath}`);
    }
  }

  lines.push('', `Last marker: ${status.runner.lastMarker || 'unknown'}`);
  lines.push(`Last round: ${status.runner.lastRound || 'unknown'}`);
  lines.push(`Verification: ${status.verification.stale ? 'stale' : 'fresh'} (${status.verification.summary || 'missing'})`);

  if (status.warnings.length > 0) {
    lines.push('', 'Warnings:');
    for (const warning of status.warnings) lines.push(`- ${warning}`);
  }

  return `${lines.join('\n')}\n`;
}

function printHelp() {
  console.log(`Usage: node harness-status.mjs [options]

Options:
  --repo <path>              Project repository to inspect. Defaults to cwd.
  --queue <path>             Queue file relative to repo. Defaults to NEXT.md.
  --checkpoint <path>        Checkpoint file relative to repo. Defaults to .harness/run-checkpoint.md.
  --invocation-log <path>    Invocation ndjson relative to repo. Defaults to .harness/codex-exec-invocations.ndjson.
  --format <text|json|markdown>
  --json                     Alias for --format json.
  --write-md                 Write .harness/status.md in the target repo.
  --write-json               Write .harness/status.json in the target repo.
  --help                     Show help.`);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }

  const status = await buildStatus(options);
  const markdown = formatMarkdown(status);

  if (options.writeMd || options.writeJson) {
    const harnessDir = path.join(status.repo, '.harness');
    await mkdir(harnessDir, { recursive: true });
    if (options.writeMd) await writeFile(path.join(harnessDir, 'status.md'), markdown, 'utf8');
    if (options.writeJson) {
      await writeFile(path.join(harnessDir, 'status.json'), `${JSON.stringify(status, null, 2)}\n`, 'utf8');
    }
  }

  if (options.format === 'json') {
    console.log(JSON.stringify(status, null, 2));
  } else if (options.format === 'markdown') {
    process.stdout.write(markdown);
  } else {
    process.stdout.write(formatText(status));
  }
}

const currentFile = pathToFileURL(fileURLToPath(import.meta.url)).href;
if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === currentFile) {
  main().catch((error) => {
    console.error(error.stack || error.message);
    process.exitCode = 1;
  });
}
