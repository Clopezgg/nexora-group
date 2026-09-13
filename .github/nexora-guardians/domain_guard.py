#!/usr/bin/env python3

import re
import subprocess
import sys
from pathlib import Path


if len(sys.argv) != 3:
    raise SystemExit("usage: domain_guard.py BASE_SHA HEAD_SHA")

BASE, HEAD = sys.argv[1:]


def git(*args: str, allow_fail=False) -> str:
    p = subprocess.run(
        ("git",) + args,
        text=True,
        capture_output=True,
    )
    if p.returncode and not allow_fail:
        raise RuntimeError(p.stderr)
    return p.stdout


changed = [
    p
    for p in git("diff", "--name-only", BASE, HEAD).splitlines()
    if p
]

errors: list[str] = []
warnings: list[str] = []


def current(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def base_content(path: str) -> str:
    return git("show", f"{BASE}:{path}", allow_fail=True)


def added_lines(path: str) -> list[str]:
    diff = git(
        "diff",
        "--unified=0",
        BASE,
        HEAD,
        "--",
        path,
        allow_fail=True,
    )

    result = []
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            result.append(line[1:])
    return result


# ------------------------------------------------------------
# A. CENTRAL POSTING ENGINE
# ------------------------------------------------------------

for path in changed:
    if not path.startswith("backend/app/"):
        continue

    allowed = (
        path == "backend/app/services/posting_service.py"
        or path.startswith("backend/app/models/")
        or path.startswith("backend/tests/")
    )

    if allowed:
        continue

    for line in added_lines(path):
        if re.search(r"\bAccountingDocument\s*\(", line):
            errors.append(
                f"{path}: construcción directa de AccountingDocument fuera "
                "del Posting Engine."
            )

        if re.search(r"\bJournalLine\s*\(", line):
            errors.append(
                f"{path}: construcción directa de JournalLine fuera "
                "del Posting Engine."
            )


# ------------------------------------------------------------
# B. POSTING SERVICE INVARIANTS
# ------------------------------------------------------------

posting = "backend/app/services/posting_service.py"

if posting in changed:
    text = current(posting)

    mandatory = {
        "_validate_balance(lines)": "validación de doble partida",
        "effective_date or business_today()": "effective_date fiscal",
        "_assert_fiscal_period_allows_posting": "control de período fiscal",
        ".with_for_update": "locking de concurrencia",
        'original.status = "REVERSED"': "reversal del documento original",
        "assert_document_is_mutable_or_raise": "inmutabilidad del documento",
    }

    for token, label in mandatory.items():
        if token not in text:
            errors.append(
                f"{posting}: desapareció la invariante '{label}' ({token})."
            )


# ------------------------------------------------------------
# C. RBAC REGRESSION GUARD
# ------------------------------------------------------------

for path in changed:
    if not path.startswith("backend/app/api/routes/"):
        continue

    before = base_content(path)
    after = current(path)

    # Si antes existía el guard y fue eliminado, es un P0.
    if "require_permission" in before and "require_permission" not in after:
        errors.append(
            f"{path}: se eliminó require_permission de un route module."
        )

    # Un nuevo módulo de rutas mutables debe tener autorización explícita.
    if not before:
        mutating = re.search(
            r"@router\.(post|put|patch|delete)\s*\(",
            after,
        )

        safe_new_modules = (
            path.endswith("/auth.py")
            or path.endswith("/health.py")
        )

        if (
            mutating
            and "require_permission" not in after
            and not safe_new_modules
        ):
            errors.append(
                f"{path}: nuevo módulo con endpoints mutables sin "
                "require_permission."
            )


# ------------------------------------------------------------
# D. DESTRUCTIVE MIGRATION GUARD
# ------------------------------------------------------------

for path in changed:
    if not path.startswith("backend/alembic/versions/"):
        continue

    for line in added_lines(path):
        destructive = any(
            token in line
            for token in (
                "op.drop_table(",
                "op.drop_column(",
                'op.execute("DROP ',
                "op.execute('DROP ",
            )
        )

        if destructive and "NEXORA_ALLOW_DESTRUCTIVE_MIGRATION" not in line:
            errors.append(
                f"{path}: operación destructiva sin marcador "
                "NEXORA_ALLOW_DESTRUCTIVE_MIGRATION: {line.strip()}"
            )


# ------------------------------------------------------------
# E. WORKFLOW SECURITY
# ------------------------------------------------------------

for path in changed:
    if not path.startswith(".github/workflows/"):
        continue

    text = current(path)

    if re.search(r"(?m)^\s*permissions:\s*write-all\s*$", text):
        errors.append(
            f"{path}: permissions: write-all está prohibido."
        )

    if "pull_request_target:" in text:
        errors.append(
            f"{path}: pull_request_target requiere auditoría manual; "
            "prohibido por defecto en NEXORA."
        )

    for line in text.splitlines():
        if re.search(r"(curl|wget).*\|\s*(sudo\s+)?(ba)?sh\b", line):
            errors.append(
                f"{path}: descarga ejecutada directamente por shell: "
                f"{line.strip()}"
            )


# ------------------------------------------------------------
# F. ACCOUNTING DESTRUCTIVE MUTATION HEURISTIC
# ------------------------------------------------------------

sensitive = (
    "accounting",
    "treasury",
    "/ap.",
    "/ar.",
    "posting",
    "closing",
)

for path in changed:
    if not path.endswith(".py"):
        continue

    low = path.lower()

    if not any(x in low for x in sensitive):
        continue

    for line in added_lines(path):
        if ".delete(" in line or "delete(" in line:
            warnings.append(
                f"{path}: revisar operación delete en dominio financiero: "
                f"{line.strip()}"
            )


# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

print("=== NEXORA DOMAIN GUARDIAN ===")
print(f"Changed files: {len(changed)}")

if warnings:
    print("\nWARNINGS:")
    for w in warnings:
        print(f"  ! {w}")

if errors:
    print("\nBLOCKING FINDINGS:")
    for e in errors:
        print(f"  X {e}")

    print(f"\nRESULT: FAILED ({len(errors)} blocking findings)")
    raise SystemExit(1)

print("\nRESULT: PASS")
