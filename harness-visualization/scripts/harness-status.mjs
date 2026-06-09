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
const DEFAULT_CONFIG_PATH = '.harness/harness-status.config.json';
const DEFAULT_PROJECT_CONFIG = Object.freeze({
  queue: 'NEXT.md',
  checkpoint: '.harness/run-checkpoint.md',
  invocationLog: '.harness/codex-exec-invocations.ndjson',
  changes: 'docs/changes',
  archive: 'docs/changes/archive',
  statusMd: '.harness/status.md',
  statusJson: '.harness/status.json',
});

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
    config: DEFAULT_CONFIG_PATH,
    format: 'text',
    writeMd: false,
    writeJson: false,
    init: false,
    force: false,
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
    } else if (arg === '--changes') {
      options.changes = next;
      index += 1;
    } else if (arg === '--archive') {
      options.archive = next;
      index += 1;
    } else if (arg === '--status-md') {
      options.statusMd = next;
      index += 1;
    } else if (arg === '--status-json') {
      options.statusJson = next;
      index += 1;
    } else if (arg === '--config') {
      options.config = next;
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
    } else if (arg === '--init') {
      options.init = true;
    } else if (arg === '--force') {
      options.force = true;
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

function definedOnly(values) {
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== undefined));
}

async function readJsonConfig(filePath) {
  const content = await readText(filePath);
  if (!content) return {};
  try {
    return JSON.parse(content);
  } catch (error) {
    throw new Error(`Could not parse harness status config at ${filePath}: ${error.message}`);
  }
}

async function resolveStatusOptions(options = {}) {
  const repoPath = path.resolve(options.repo || process.cwd());
  const configPath = options.config || DEFAULT_CONFIG_PATH;
  const configFile = path.resolve(repoPath, configPath);
  const fileConfig = await readJsonConfig(configFile);
  const cliConfig = definedOnly({
    queue: options.queue,
    checkpoint: options.checkpoint,
    invocationLog: options.invocationLog,
    changes: options.changes,
    archive: options.archive,
    statusMd: options.statusMd,
    statusJson: options.statusJson,
  });

  return {
    repoPath,
    configPath,
    ...DEFAULT_PROJECT_CONFIG,
    ...fileConfig,
    ...cliConfig,
  };
}

async function initProjectConfig(options = {}) {
  const repoPath = path.resolve(options.repo || process.cwd());
  const configPath = options.config || DEFAULT_CONFIG_PATH;
  const configFile = path.resolve(repoPath, configPath);
  const existing = await readText(configFile);
  if (existing && !options.force) {
    return { repoPath, configPath, created: false, reason: 'exists' };
  }

  const content = {
    schemaVersion: 1,
    ...DEFAULT_PROJECT_CONFIG,
  };
  await mkdir(path.dirname(configFile), { recursive: true });
  await writeFile(configFile, `${JSON.stringify(content, null, 2)}\n`, 'utf8');
  return { repoPath, configPath, created: true };
}

function parseQueueMarkdown(content, queuePath = 'NEXT.md') {
  if (!content) return [];

  const items = [];
  let current = null;
  const lines = content.split(/\r?\n/);

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const itemMatch = line.match(/^\s*(?:(?:[-*]|\d+[.)])\s*)?\[([^\]]+)\]\s+(.+?)\s*$/);
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
    const fieldMatch = line.match(/^\s*(?:[-*]\s*)?([A-Za-z][A-Za-z /-]*):\s*(.+?)\s*$/);
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

function summarizeQueue(items) {
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

function isSchedulerStatus(status) {
  return status === 'ready' || status === 'active';
}

function splitQueueItems(items) {
  const schedulerItems = items.filter((item) => isSchedulerStatus(item.status));
  const legacyDoneItems = items.filter((item) => item.status === 'done');
  const nonSchedulerQueueItems = items.filter((item) => !isSchedulerStatus(item.status));
  return { schedulerItems, legacyDoneItems, nonSchedulerQueueItems };
}

function inferCurrentLayer(items) {
  const active = items.find((item) => item.status === 'active' && item.layer);
  if (active) return active.layer;
  const ready = items.find((item) => item.status === 'ready' && item.layer);
  if (ready) return ready.layer;
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

function isPathInside(childPath, parentPath) {
  const relative = path.relative(parentPath, childPath);
  return relative === '' || Boolean(relative && !relative.startsWith('..') && !path.isAbsolute(relative));
}

async function discoverChangeDirs(repoPath, schedulerItems, changesRootPath, archiveRootPath) {
  const found = new Map();
  const archiveRoot = path.resolve(repoPath, archiveRootPath);
  for (const item of schedulerItems) {
    if (!item.change) continue;
    const absolute = path.resolve(repoPath, item.change);
    if (isPathInside(absolute, archiveRoot)) continue;
    found.set(absolute, item.change);
  }

  const changesRoot = path.resolve(repoPath, changesRootPath);
  if (await pathExists(changesRoot)) {
    const entries = await readdir(changesRoot, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const absolute = path.join(changesRoot, entry.name);
      if (isPathInside(absolute, archiveRoot)) continue;
      found.set(absolute, path.relative(repoPath, absolute).replace(/\\/g, '/'));
    }
  }

  return [...found.entries()].map(([absolute, relative]) => ({ absolute, relative }));
}

async function readTaskPackets(repoPath, schedulerItems, changesRootPath, archiveRootPath, warnings) {
  const packets = [];
  const dirs = await discoverChangeDirs(repoPath, schedulerItems, changesRootPath, archiveRootPath);

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

async function discoverArchivedDirs(repoPath, archiveRootPath) {
  const archiveRoot = path.resolve(repoPath, archiveRootPath);
  if (!(await pathExists(archiveRoot))) return [];

  const entries = await readdir(archiveRoot, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => {
      const absolute = path.join(archiveRoot, entry.name);
      return {
        absolute,
        relative: path.relative(repoPath, absolute).replace(/\\/g, '/'),
      };
    });
}

async function readArchivedPackets(repoPath, archiveRootPath, warnings) {
  const packets = [];
  const dirs = await discoverArchivedDirs(repoPath, archiveRootPath);

  for (const dir of dirs) {
    const tasksPath = path.join(dir.absolute, 'tasks.md');
    const content = await readText(tasksPath);
    if (!content) {
      warnings.push(`Archived packet has no tasks.md: ${dir.relative}`);
      continue;
    }
    const packet = parseTaskMarkdown(content, path.relative(repoPath, tasksPath).replace(/\\/g, '/'));
    packet.changePath = dir.relative;
    packet.archived = true;
    packets.push(packet);
  }

  return packets;
}

function summarizePackets(packets) {
  return packets.reduce(
    (summary, packet) => ({
      packets: summary.packets + 1,
      total: summary.total + packet.total,
      done: summary.done + packet.done,
      pending: summary.pending + packet.pending,
      active: summary.active + packet.active,
    }),
    { packets: 0, total: 0, done: 0, pending: 0, active: 0 },
  );
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
  const resolved = await resolveStatusOptions(options);
  const { repoPath, queue, checkpoint, invocationLog, changes, archive } = resolved;
  const warnings = [];

  const queuePath = path.join(repoPath, queue);
  const queueContent = await readText(queuePath);
  if (!queueContent) warnings.push(`Queue file not found: ${queue}`);
  const queueItems = parseQueueMarkdown(queueContent, queue);
  const { schedulerItems, legacyDoneItems, nonSchedulerQueueItems } = splitQueueItems(queueItems);

  if (legacyDoneItems.length > 0) {
    warnings.push(
      `Queue contains ${legacyDoneItems.length} completed item(s); move done history to ${archive}. Preserved in legacyDoneItems.`,
    );
  }
  const legacyNonDoneItems = nonSchedulerQueueItems.filter((item) => item.status !== 'done');
  if (legacyNonDoneItems.length > 0) {
    warnings.push(
      `Queue contains ${legacyNonDoneItems.length} non-scheduler item(s); limit ${queue} to ready/active items and move blocked/not-now state elsewhere.`,
    );
  }

  const currentLayer = inferCurrentLayer(schedulerItems);
  const taskPackets = await readTaskPackets(repoPath, schedulerItems, changes, archive, warnings);
  const archivedPackets = await readArchivedPackets(repoPath, archive, warnings);
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
    config: {
      path: resolved.configPath,
      queue,
      checkpoint,
      invocationLog,
      changes,
      archive,
      statusMd: resolved.statusMd,
      statusJson: resolved.statusJson,
    },
    currentLayer,
    layerTimeline: buildLayerTimeline(currentLayer),
    queueSummary: summarizeQueue(queueItems),
    readySummary: summarizeQueue(schedulerItems),
    archiveSummary: summarizePackets(archivedPackets),
    queueItems,
    readyItems: schedulerItems,
    legacyDoneItems,
    nonSchedulerQueueItems,
    taskPackets,
    archivedPackets,
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
    '## Scheduler Queue',
    '',
    `Scheduler total: ${status.readySummary.total}; ready: ${status.readySummary.ready}; active: ${status.readySummary.active}; full queue total: ${status.queueSummary.total}`,
    '',
  ];

  if (status.readyItems.length === 0) {
    lines.push('- No scheduler items found.');
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

  lines.push('', '## Done Archive', '');
  if (status.archivedPackets.length === 0) {
    lines.push('- No archived packets found.');
  } else {
    lines.push(`- Packets: ${status.archiveSummary.packets}; tasks: ${status.archiveSummary.done}/${status.archiveSummary.total}`);
    for (const packet of status.archivedPackets) {
      lines.push(`- [${packet.done}/${packet.total}] ${packet.tasksPath}`);
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

  if (status.nonSchedulerQueueItems.length > 0) {
    lines.push('', '## Legacy Queue Records', '');
    for (const item of status.nonSchedulerQueueItems) {
      const details = [
        item.layer ? `Layer: ${item.layer}` : null,
        item.change ? `Change: ${item.change}` : null,
        item.packetization ? `Packetization: ${item.packetization}` : null,
      ].filter(Boolean).join('; ');
      lines.push(`- [${item.status}] ${item.title}${details ? ` (${details})` : ''}`);
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
    `Scheduler queue: total=${status.readySummary.total} ready=${status.readySummary.ready} active=${status.readySummary.active} fullQueue=${status.queueSummary.total}`,
    '',
    'Scheduler items:',
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

  lines.push('', 'Done archive:');
  if (status.archivedPackets.length === 0) {
    lines.push('- none');
  } else {
    lines.push(`- packets=${status.archiveSummary.packets} tasks=${status.archiveSummary.done}/${status.archiveSummary.total}`);
    for (const packet of status.archivedPackets) {
      lines.push(`- [${packet.done}/${packet.total}] ${packet.tasksPath}`);
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

  if (status.nonSchedulerQueueItems.length > 0) {
    lines.push('', 'Legacy queue records:');
    for (const item of status.nonSchedulerQueueItems) {
      const details = [
        item.layer ? `layer=${item.layer}` : null,
        item.change ? `change=${item.change}` : null,
        item.packetization ? `packetization=${item.packetization}` : null,
      ].filter(Boolean).join(' ');
      lines.push(`- [${item.status}] ${item.title}${details ? ` (${details})` : ''}`);
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
  --init                     Create .harness/harness-status.config.json with default paths.
  --force                    With --init, overwrite an existing config.
  --config <path>            Config file relative to repo. Defaults to .harness/harness-status.config.json.
  --queue <path>             Queue file relative to repo. Defaults to NEXT.md.
  --checkpoint <path>        Checkpoint file relative to repo. Defaults to .harness/run-checkpoint.md.
  --invocation-log <path>    Invocation ndjson relative to repo. Defaults to .harness/codex-exec-invocations.ndjson.
  --changes <path>           Change packet root relative to repo. Defaults to docs/changes.
  --archive <path>           Done packet archive root relative to repo. Defaults to docs/changes/archive.
  --status-md <path>         Markdown output path relative to repo. Defaults to .harness/status.md.
  --status-json <path>       JSON output path relative to repo. Defaults to .harness/status.json.
  --format <text|json|markdown>
  --json                     Alias for --format json.
  --write-md                 Write markdown status in the target repo.
  --write-json               Write JSON status in the target repo.
  --help                     Show help.`);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }
  if (options.init) {
    const result = await initProjectConfig(options);
    const action = result.created ? 'Created' : 'Skipped existing';
    console.log(`${action} ${result.configPath} in ${result.repoPath}`);
    return;
  }

  const status = await buildStatus(options);
  const markdown = formatMarkdown(status);

  if (options.writeMd || options.writeJson) {
    if (options.writeMd) {
      const statusMdPath = path.resolve(status.repo, status.config.statusMd);
      await mkdir(path.dirname(statusMdPath), { recursive: true });
      await writeFile(statusMdPath, markdown, 'utf8');
    }
    if (options.writeJson) {
      const statusJsonPath = path.resolve(status.repo, status.config.statusJson);
      await mkdir(path.dirname(statusJsonPath), { recursive: true });
      await writeFile(statusJsonPath, `${JSON.stringify(status, null, 2)}\n`, 'utf8');
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
