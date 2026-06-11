#!/usr/bin/env node
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const defaultRepoRoot = path.resolve(__dirname, "..", "..");
const requiredFiles = ["proposal.md", "design.md", "tasks.md", "contracts.md", "verification.md"];
const allowedStatuses = new Set(["draft", "ready", "active", "blocked", "done", "archived"]);

const { targets, repoRoot } = parseArgs(process.argv.slice(2));
const packetDirs = targets.length ? targets.map((target) => resolvePacket(target, repoRoot)) : discoverPackets(repoRoot);
const errors = [];

for (const packetDir of packetDirs) {
  checkPacket(packetDir, repoRoot, errors);
}

if (errors.length) {
  console.error("Change packet check failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

if (packetDirs.length === 0) {
  console.log("Change packet check passed: no change packets found.");
} else {
  console.log(`Change packet check passed: ${packetDirs.length} packet(s).`);
}

function checkPacket(packetDir, repoRootValue, allErrors) {
  const label = normalize(path.relative(repoRootValue, packetDir) || packetDir);
  const texts = new Map();

  if (!existsSync(packetDir)) {
    allErrors.push(`${label} does not exist.`);
    return;
  }

  if (!statSync(packetDir).isDirectory()) {
    allErrors.push(`${label} is not a directory.`);
    return;
  }

  for (const file of requiredFiles) {
    const filePath = path.join(packetDir, file);
    if (!existsSync(filePath)) {
      allErrors.push(`${label} missing ${file}.`);
      continue;
    }
    texts.set(file, readFileSync(filePath, "utf8"));
  }

  const tasks = texts.get("tasks.md") ?? "";
  if (tasks && !/^\s*-\s+\[[ xX]\]\s+\S/m.test(tasks)) {
    allErrors.push(`${label}/tasks.md must contain at least one checkbox checklist item.`);
  }

  for (const [file, text] of texts.entries()) {
    const statusMatches = text.matchAll(/^Status\s*:\s*([A-Za-z-]+)\s*$/gim);
    for (const match of statusMatches) {
      const status = match[1].toLowerCase();
      if (!allowedStatuses.has(status)) {
        allErrors.push(`${label}/${file} has invalid status '${match[1]}'. Use draft/ready/active/blocked/done/archived.`);
      }
    }
  }

  const contracts = texts.get("contracts.md") ?? "";
  if (contracts && !hasContractArtifact(contracts) && !hasBlockedReason(contracts)) {
    allErrors.push(`${label}/contracts.md must declare a contract artifact or an explicit blocked reason.`);
  }

  const verification = texts.get("verification.md") ?? "";
  if (verification && !hasVerificationEvidence(verification)) {
    allErrors.push(`${label}/verification.md must record verification commands, results, or an unable-to-verify reason.`);
  }

  const combined = [...texts.values()].join("\n");
  if (isArchivedPacket(packetDir, combined, repoRootValue) && !hasArchiveBacklink(combined)) {
    allErrors.push(`${label}: Archived packet must link stable conclusions back to ADR, README, contract, verification, queue, or project index.`);
  }
}

function hasContractArtifact(text) {
  return text.split(/\r?\n/).some((line) => {
    const trimmed = line.trim();
    return /^-\s*(?:artifact|path|schema|example|fixture|probe|check script|acceptance test|documentation invariant)\s*:\s*\S/i.test(trimmed);
  });
}

function hasBlockedReason(text) {
  return /\bblocked reason\s*:\s*\S/i.test(text) || /\bblocked\b[\s\S]{0,120}\b(?:because|reason|missing evidence|无法|缺少|等待|原因)\b/i.test(text);
}

function hasVerificationEvidence(text) {
  const lines = text.split(/\r?\n/).map((line) => line.trim());
  return lines.some((line) => /^-\s*(?:npm|node|python|pytest|cargo|go test|mvn|gradle|dotnet)\b/i.test(line))
    || lines.some((line) => /^-\s*(?:pass|passed|fail|failed|skipped|blocked)\b/i.test(line))
    || lines.some((line) => /^-\s*(?:reason|risk|follow-up|blocked)\s*:\s*\S/i.test(line) && /unable to verify/i.test(text));
}

function isArchivedPacket(packetDir, combined, repoRootValue) {
  const relative = normalize(path.relative(repoRootValue, packetDir));
  return relative.startsWith("docs/changes/archive/") || /^Status\s*:\s*archived\s*$/gim.test(combined);
}

function hasArchiveBacklink(text) {
  return /\b(?:ADR|README|contract|contracts|schema|fixture|probe|verification|NEXT\.md|TODO\.md|backlog|queue|index|项目索引|队列|验证|契约)\b/i.test(text)
    && /\b(?:link|linked|backlink|synced|copied|updated|回链|同步|写回|归档回)\b/i.test(text);
}

function discoverPackets(repoRootValue) {
  const changesRoot = path.join(repoRootValue, "docs", "changes");
  if (!existsSync(changesRoot)) {
    return [];
  }

  const packets = [];
  for (const entry of readdirSync(changesRoot, { withFileTypes: true })) {
    if (entry.isDirectory() && entry.name !== "archive") {
      packets.push(path.join(changesRoot, entry.name));
    }
  }

  const archiveRoot = path.join(changesRoot, "archive");
  if (existsSync(archiveRoot)) {
    for (const entry of readdirSync(archiveRoot, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        packets.push(path.join(archiveRoot, entry.name));
      }
    }
  }

  return packets;
}

function resolvePacket(target, repoRootValue) {
  const direct = path.resolve(target);
  if (existsSync(direct)) {
    return direct;
  }

  const repoRelative = path.resolve(repoRootValue, target);
  if (existsSync(repoRelative)) {
    return repoRelative;
  }

  return path.resolve(repoRootValue, "docs", "changes", target);
}

function parseArgs(args) {
  const parsedTargets = [];
  let parsedRepoRoot = defaultRepoRoot;

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--repo") {
      parsedRepoRoot = path.resolve(args[index + 1] ?? "");
      index += 1;
    } else if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    } else {
      parsedTargets.push(arg);
    }
  }

  return {
    targets: parsedTargets,
    repoRoot: parsedRepoRoot,
  };
}

function normalize(value) {
  return value.replaceAll(path.sep, "/");
}

function usage() {
  console.error("Usage: node harness-engineering/scripts/check-change-packet.mjs [packet-path-or-id ...] [--repo <path>]");
}
