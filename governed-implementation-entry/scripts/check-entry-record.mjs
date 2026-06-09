#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const file = process.argv[2];

if (!file) {
  console.error("Usage: node scripts/check-entry-record.mjs <markdown-file>");
  process.exit(2);
}

const text = readFileSync(resolve(file), "utf8");
const requiredFields = [
  "Current layer",
  "Target",
  "Scope",
  "Contract evidence",
  "Readiness gate",
  "Packetization",
  "Verification command",
  "Review / Next state file",
  "Stop conditions",
];
const invalidValue = /^(?:\s*|tbd|todo|missing|n\/a|\?)$/i;
const errors = [];

if (!/Implementation Entry Record:/i.test(text)) {
  errors.push("Missing 'Implementation Entry Record:' heading.");
}

for (const field of requiredFields) {
  const pattern = new RegExp(`^-\\s*${escapeRegExp(field)}\\s*:\\s*(.*)$`, "im");
  const match = text.match(pattern);

  if (!match) {
    errors.push(`Missing field: ${field}`);
    continue;
  }

  if (invalidValue.test(match[1])) {
    errors.push(`Empty or placeholder value: ${field}`);
  }
}

const readiness = text.match(/-\s*Readiness gate\s*:\s*(.*)$/im)?.[1] ?? "";
if (readiness && !/\b(?:pass|fail)\b/i.test(readiness)) {
  errors.push("Readiness gate must include pass or fail.");
}

const packetization = text.match(/-\s*Packetization\s*:\s*(.*)$/im)?.[1] ?? "";
if (packetization && !/\b(?:ready|not-needed|missing)\b/i.test(packetization)) {
  errors.push("Packetization must include ready, not-needed, or missing.");
}

if (errors.length) {
  console.error(errors.map((error) => `- ${error}`).join("\n"));
  process.exit(1);
}

console.log(`Implementation Entry Record check passed: ${file}`);

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
