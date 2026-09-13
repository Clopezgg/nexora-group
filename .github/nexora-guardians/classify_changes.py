#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


if len(sys.argv) != 3:
    raise SystemExit("usage: classify_changes.py BASE_SHA HEAD_SHA")

base, head = sys.argv[1:]

raw = run("git", "diff", "--name-only", base, head)
files = [x for x in raw.splitlines() if x]

financial_patterns = (
    "backend/app/services/posting",
    "backend/app/services/resource_posting",
    "backend/app/services/financial",
    "backend/app/services/treasury",
    "backend/app/services/closing",
    "backend/app/api/routes/accounting",
    "backend/app/api/routes/ap",
    "backend/app/api/routes/ar",
    "backend/app/api/routes/assets",
    "backend/app/api/routes/fiscal",
    "backend/app/models/accounting",
    "backend/app/models/fiscal",
    "backend/app/schemas/accounting",
    "docs/ACCOUNTING.md",
)

auth_patterns = (
    "backend/app/api/routes/",
    "backend/app/services/permission_service.py",
    "backend/app/core/security",
    "backend/app/api/dependencies",
)

migration_patterns = (
    "backend/alembic/",
    "backend/app/models/",
)

api_patterns = (
    "backend/app/api/",
    "backend/app/schemas/",
    "backend/app/main.py",
)

infra_patterns = (
    "infra/",
    ".github/workflows/",
    "backend/Dockerfile",
    "docker-compose",
)

frontend_patterns = (
    "frontend/",
)


def contains(patterns):
    return any(
        any(f.startswith(p) or p in f for p in patterns)
        for f in files
    )


financial = contains(financial_patterns)
auth = contains(auth_patterns)
migration = contains(migration_patterns)
api = contains(api_patterns)
infra = contains(infra_patterns)
frontend = contains(frontend_patterns)

certification_patterns = (
    ".github/nexora-guardians/",
    ".github/workflows/nexora-ultra-gates.yml",
    ".github/workflows/nexora-deep-testing.yml",
    "backend/tests/test_financial_properties.py",
    "docs/NEXORA_CERTIFICATION.md",
)

certification = contains(certification_patterns)

# Changes to the certification machinery itself are RISK 4.
# A broken guardian must never certify its own installation without
# executing the strongest available verification suite.
critical = financial or auth or migration or certification

if critical:
    risk = 4
elif api or infra:
    risk = 3
elif frontend or any(f.startswith("backend/") for f in files):
    risk = 2
else:
    risk = 1

if len(files) >= 25:
    risk = max(risk, 4)
elif len(files) >= 10:
    risk = max(risk, 3)

out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a", encoding="utf-8") as fp:
        fp.write(f"financial={str(financial).lower()}\n")
        fp.write(f"auth={str(auth).lower()}\n")
        fp.write(f"migration={str(migration).lower()}\n")
        fp.write(f"api={str(api).lower()}\n")
        fp.write(f"infra={str(infra).lower()}\n")
        fp.write(f"frontend={str(frontend).lower()}\n")
        fp.write(f"critical={str(critical).lower()}\n")
        fp.write(f"risk_level={risk}\n")
        fp.write(f"file_count={len(files)}\n")

summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    with open(summary, "a", encoding="utf-8") as fp:
        fp.write("# NEXORA Risk Classification\n\n")
        fp.write(f"**Risk level:** `{risk}/4`\n\n")
        fp.write(f"**Files changed:** `{len(files)}`\n\n")
        fp.write("| Domain | Triggered |\n|---|---:|\n")
        for key, value in (
            ("Financial", financial),
            ("Authorization/RBAC", auth),
            ("Database/Migration", migration),
            ("API", api),
            ("Infrastructure", infra),
            ("Frontend", frontend),
        ):
            fp.write(f"| {key} | {'YES' if value else 'no'} |\n")

        fp.write("\n## Changed files\n\n")
        for f in files:
            fp.write(f"- `{f}`\n")

print(f"NEXORA_RISK={risk}")
print(f"FILES={len(files)}")
print("FINANCIAL=", financial)
print("AUTH=", auth)
print("MIGRATION=", migration)
print("API=", api)
print("INFRA=", infra)
