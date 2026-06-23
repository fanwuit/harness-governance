#!/usr/bin/env python3
"""Demo subagent: outputs structured JSON simulating a real subagent result."""

import json
import sys

role = sys.argv[1] if len(sys.argv) > 1 else "implementer"
prompt = sys.argv[2] if len(sys.argv) > 2 else ""

result = {
    "role": role,
    "verdict": "success",
    "summary": f"Demo {role} subagent executed successfully",
    "findings": [],
    "filesChanged": 0,
    "contractBlocked": False,
    "verificationPassed": True,
    "trace": [
        {"step": "analyze", "status": "done"},
        {"step": "execute", "status": "done"},
        {"step": "verify", "status": "done"},
    ],
}

if role == "implementer":
    result["filesChanged"] = 2
    result["findings"] = [
        {"file": "src/feature.py", "action": "modified"},
        {"file": "tests/test_feature.py", "action": "created"},
    ]
elif role == "verifier":
    result["findings"] = [
        {"check": "implementation review", "status": "passed"},
        {"check": "contract compliance", "status": "passed"},
    ]
elif role == "planner":
    result["filesChanged"] = 1
    result["findings"] = [
        {"task": "design API", "status": "ready"},
        {"task": "write tests", "status": "pending"},
    ]

print(json.dumps(result, indent=2))
