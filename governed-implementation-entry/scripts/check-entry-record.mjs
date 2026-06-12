#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const file = process.argv[2];

if (!file) {
  console.error("Usage: node scripts/check-entry-record.mjs <markdown-file>");
  process.exit(2);
}

const text = readFileSync(resolve(file), "utf8");
const errors = [];

const entryTypes = [
  {
    heading: "Implementation Entry Record",
    requiredFields: [
      "Current layer",
      "Target",
      "Scope",
      "Contract evidence",
      "Readiness gate",
      "Packetization",
      "Verification command",
      "Review / Next state file",
      "Stop conditions",
    ],
    validate: validateImplementationEntry,
  },
  {
    heading: "Trivial Safe Change Entry",
    requiredFields: [
      "Target",
      "Scope",
      "Why trivial",
      "Existing contract or reason not needed",
      "Verification",
      "Stop conditions",
    ],
    validate: () => [],
  },
];

const matchingType = entryTypes.find((entryType) => hasHeading(entryType.heading));

if (!matchingType) {
  errors.push("Missing 'Implementation Entry Record:' or 'Trivial Safe Change Entry:' heading.");
} else {
  for (const field of matchingType.requiredFields) {
    const value = fieldValue(field);

    if (value === null) {
      errors.push(`Missing field: ${field}`);
      continue;
    }

    if (isInvalidValue(value)) {
      errors.push(`Empty or placeholder value: ${field}`);
    }
  }

  errors.push(...matchingType.validate());
}

if (errors.length) {
  console.error(errors.map((error) => `- ${error}`).join("\n"));
  process.exit(1);
}

console.log(`${matchingType.heading} check passed: ${file}`);

function hasHeading(heading) {
  return new RegExp(`${escapeRegExp(heading)}:`, "i").test(text);
}

function fieldValue(field) {
  const pattern = new RegExp(`^-\\s*${escapeRegExp(field)}\\s*:\\s*(.*)$`, "im");
  const match = text.match(pattern);
  return match ? match[1] : null;
}

function isInvalidValue(value) {
  return /^(?:\s*|tbd|todo|missing|n\/a|\?)$/i.test(value);
}

function validateImplementationEntry() {
  const validationErrors = [];
  const readiness = fieldValue("Readiness gate") ?? "";
  if (readiness && !/\b(?:pass|fail)\b/i.test(readiness)) {
    validationErrors.push("Readiness gate must include pass or fail.");
  }

  const packetization = fieldValue("Packetization") ?? "";
  if (packetization && !/\b(?:ready|not-needed|missing)\b/i.test(packetization)) {
    validationErrors.push("Packetization must include ready, not-needed, or missing.");
  }

  return validationErrors;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
