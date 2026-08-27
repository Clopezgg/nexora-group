from pathlib import Path

path = Path('frontend/e2e/critical-journey.spec.ts')
text = path.read_text(encoding='utf-8')
replacements = {
    "await page.getByLabel('Cuenta contrapartida').selectOption({ label: 'Aportes E2E' })":
        "await page.getByLabel('Cuenta contable de origen').selectOption({ label: '3100 · Aportes E2E' })",
    "await page.getByRole('button', { name: 'Registrar', exact: true }).click()":
        "await page.getByRole('button', { name: 'Registrar remesa', exact: true }).click()",
}
for old, new in replacements.items():
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'Expected one match for {old!r}, found {count}')
    text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
