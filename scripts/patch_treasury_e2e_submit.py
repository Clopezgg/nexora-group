from pathlib import Path

path = Path('frontend/e2e/critical-journey.spec.ts')
text = path.read_text(encoding='utf-8')
old = "await page.getByRole('button', { name: 'Registrar remesa', exact: true }).click()"
new = "await page.getByLabel('Registrar remesa').getByRole('button', { name: 'Registrar remesa', exact: true }).click()"
count = text.count(old)
if count != 1:
    raise RuntimeError(f'Expected one match, found {count}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
