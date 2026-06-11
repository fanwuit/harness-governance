#!/usr/bin/env node
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(__dirname, "..");
const defaultRepoRoot = path.resolve(skillRoot, "..");
const templateDir = path.join(skillRoot, "templates", "change-packet");
const requiredFiles = ["proposal.md", "design.md", "tasks.md", "contracts.md", "verification.md"];

const { id, repoRoot, force } = parseArgs(process.argv.slice(2));

if (!id) {
  usage();
  process.exit(2);
}

if (!/^[a-z0-9][a-z0-9._-]*$/i.test(id) || id.toLowerCase() === "archive") {
  console.error("Change id must be a safe file name, for example: public-contract-fixture");
  process.exit(2);
}

const changesRoot = path.join(repoRoot, "docs", "changes");
const packetDir = path.join(changesRoot, id);
assertInside(repoRoot, packetDir);

if (existsSync(packetDir) && !force) {
  console.error(`Change packet already exists: ${path.relative(repoRoot, packetDir)}`);
  console.error("Use --force to fill missing template files without overwriting existing files.");
  process.exit(1);
}

mkdirSync(packetDir, { recursive: true });

for (const file of requiredFiles) {
  const source = path.join(templateDir, file);
  const target = path.join(packetDir, file);

  if (existsSync(target) && force) {
    continue;
  }

  const text = readFileSync(source, "utf8")
    .replaceAll("{{CHANGE_ID}}", id)
    .replaceAll("{{TODAY}}", new Date().toISOString().slice(0, 10));
  writeFileSync(target, text, "utf8");
}

console.log(`Initialized change packet: ${path.relative(repoRoot, packetDir)}`);

function parseArgs(args) {
  let parsedId = "";
  let parsedRepoRoot = defaultRepoRoot;
  let parsedForce = false;

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--repo") {
      parsedRepoRoot = path.resolve(args[index + 1] ?? "");
      index += 1;
    } else if (arg === "--force") {
      parsedForce = true;
    } else if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    } else if (!parsedId) {
      parsedId = arg;
    } else {
      console.error(`Unknown argument: ${arg}`);
      usage();
      process.exit(2);
    }
  }

  return {
    id: parsedId,
    repoRoot: parsedRepoRoot,
    force: parsedForce,
  };
}

function assertInside(root, target) {
  const relative = path.relative(path.resolve(root), path.resolve(target));
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    console.error(`Refusing to write outside repo: ${target}`);
    process.exit(2);
  }
}

function usage() {
  console.error("Usage: node harness-engineering/scripts/init-change-packet.mjs <change-id> [--repo <path>] [--force]");
}
