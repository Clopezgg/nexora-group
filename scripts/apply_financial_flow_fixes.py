from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one exact match, found {count}: {old[:120]!r}")
    write(path, text.replace(old, new, 1))


def regex_once(path: str, pattern: str, replacement: str) -> None:
    text = read(path)
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{path}: expected one regex match, found {count}: {pattern[:120]!r}")
    write(path, updated)


# ---------------------------------------------------------------------------
# Backend API contracts
# ---------------------------------------------------------------------------
replace_once(
    "backend/app/schemas/treasury.py",
    '''class RemittanceCreateRequest(CamelModel):\n    company_id: uuid.UUID\n    treasury_account_id: uuid.UUID\n    counter_account_id: uuid.UUID\n    sender: str\n''',
    '''class RemittanceCreateRequest(CamelModel):\n    company_id: uuid.UUID\n    treasury_account_id: uuid.UUID\n    counter_account_id: uuid.UUID\n    origin_type: Literal["CAPITAL_CONTRIBUTION", "FINANCING", "OTHER_INCOME"] = "CAPITAL_CONTRIBUTION"\n    sender: str\n''',
)
replace_once(
    "backend/app/schemas/treasury.py",
    '''class GeneralExpenseCreateRequest(CamelModel):\n    company_id: uuid.UUID\n    treasury_account_id: uuid.UUID\n    expense_account_id: uuid.UUID\n    category: str\n''',
    '''class GeneralExpenseCreateRequest(CamelModel):\n    company_id: uuid.UUID\n    treasury_account_id: uuid.UUID\n    expense_account_id: uuid.UUID\n    scope: Literal["GENERAL", "PROJECT"] = "GENERAL"\n    project_id: uuid.UUID | None = None\n    category: str\n''',
)

# ---------------------------------------------------------------------------
# Backend routes: pass and audit the new financial dimensions
# ---------------------------------------------------------------------------
replace_once(
    "backend/app/api/routes/treasury.py",
    '''            treasury_account_id=payload.treasury_account_id,\n            counter_account_id=payload.counter_account_id,\n            sender=payload.sender,\n''',
    '''            treasury_account_id=payload.treasury_account_id,\n            counter_account_id=payload.counter_account_id,\n            origin_type=payload.origin_type,\n            sender=payload.sender,\n''',
)
replace_once(
    "backend/app/api/routes/treasury.py",
    '''            after={"baseAmount": str(remittance.base_amount), "sender": remittance.sender},\n''',
    '''            after={\n                "baseAmount": str(remittance.base_amount),\n                "sender": remittance.sender,\n                "originType": payload.origin_type,\n            },\n''',
)
replace_once(
    "backend/app/api/routes/treasury.py",
    '''            treasury_account_id=payload.treasury_account_id,\n            expense_account_id=payload.expense_account_id,\n            category=payload.category,\n''',
    '''            treasury_account_id=payload.treasury_account_id,\n            expense_account_id=payload.expense_account_id,\n            scope=payload.scope,\n            project_id=payload.project_id,\n            category=payload.category,\n''',
)
replace_once(
    "backend/app/api/routes/treasury.py",
    '''            after={"amount": str(expense.amount), "category": expense.category},\n''',
    '''            after={\n                "amount": str(expense.amount),\n                "category": expense.category,\n                "scope": payload.scope,\n                "projectId": str(payload.project_id) if payload.project_id else None,\n            },\n''',
)

# ---------------------------------------------------------------------------
# Treasury service invariants
# ---------------------------------------------------------------------------
replace_once(
    "backend/app/services/treasury_service.py",
    '''from app.services.financial_validation_service import (\n    assert_account_belongs_to_company,\n    assert_project_belongs_to_company,\n    assert_user_belongs_to_company,\n)\n''',
    '''from app.services.financial_validation_service import (\n    assert_account_belongs_to_company,\n    assert_operation_scope,\n    assert_project_belongs_to_company,\n    assert_user_belongs_to_company,\n)\n''',
)
replace_once(
    "backend/app/services/treasury_service.py",
    '''    treasury_account_id: uuid.UUID,\n    counter_account_id: uuid.UUID,\n    sender: str,\n''',
    '''    treasury_account_id: uuid.UUID,\n    counter_account_id: uuid.UUID,\n    origin_type: str = "CAPITAL_CONTRIBUTION",\n    sender: str,\n''',
)
replace_once(
    "backend/app/services/treasury_service.py",
    '''    if counter_account_id == treasury_account.gl_account_id:\n        raise InvalidFinancialReferenceError(\n            "counter_account_id no puede ser la misma cuenta GL de la cuenta de tesorería "\n            "(anularía el movimiento neto de la remesa)"\n        )\n\n    base_amount = (original_amount * fx_rate).quantize(Decimal("0.01"))\n''',
    '''    if counter_account_id == treasury_account.gl_account_id:\n        raise InvalidFinancialReferenceError(\n            "counter_account_id no puede ser la misma cuenta GL de la cuenta de tesorería "\n            "(anularía el movimiento neto de la remesa)"\n        )\n\n    counter_account = db.get(Account, counter_account_id)\n    if counter_account is None:\n        raise InvalidFinancialReferenceError("counter_account_id no existe")\n    if not counter_account.is_postable:\n        raise InvalidFinancialReferenceError(\n            "counter_account_id debe ser una cuenta registrable; las cuentas agrupadoras no admiten remesas"\n        )\n    expected_account_type = {\n        "CAPITAL_CONTRIBUTION": "EQUITY",\n        "FINANCING": "LIABILITY",\n        "OTHER_INCOME": "REVENUE",\n    }.get(origin_type)\n    if expected_account_type is None:\n        raise InvalidFinancialReferenceError("origin_type de remesa no soportado")\n    if counter_account.account_type != expected_account_type:\n        raise InvalidFinancialReferenceError(\n            f"La naturaleza {origin_type} requiere una cuenta {expected_account_type}; "\n            f"la contrapartida seleccionada es {counter_account.account_type}"\n        )\n\n    base_amount = (original_amount * fx_rate).quantize(Decimal("0.01"))\n''',
)
replace_once(
    "backend/app/services/treasury_service.py",
    '''def register_general_expense(\n    db: Session,\n    *,\n    company_id: uuid.UUID,\n    treasury_account_id: uuid.UUID,\n    expense_account_id: uuid.UUID,\n    category: str,\n''',
    '''def register_general_expense(\n    db: Session,\n    *,\n    company_id: uuid.UUID,\n    treasury_account_id: uuid.UUID,\n    expense_account_id: uuid.UUID,\n    scope: str = "GENERAL",\n    project_id: uuid.UUID | None = None,\n    category: str,\n''',
)
replace_once(
    "backend/app/services/treasury_service.py",
    '''    """Siempre scope=GENERAL, project_id=None. NO consume Project Budget;\n    se paga de inmediato contra Treasury (orden maestra §28)."""\n    if amount <= 0:\n        raise InvalidFinancialReferenceError("El gasto requiere amount > 0")\n''',
    '''    """Salida inmediata de Tesorería. Puede ser GENERAL (sin proyecto) o\n    PROJECT (atribuible a una obra). El proyecto nunca posee el dinero: solo\n    dimensiona el gasto en el documento/línea contable."""\n    if scope not in ("GENERAL", "PROJECT"):\n        raise InvalidFinancialReferenceError(\n            "Los gastos inmediatos solo admiten scope GENERAL o PROJECT"\n        )\n    assert_operation_scope(scope, project_id)\n    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)\n    if amount <= 0:\n        raise InvalidFinancialReferenceError("El gasto requiere amount > 0")\n''',
)
replace_once(
    "backend/app/services/treasury_service.py",
    '''        document_type_code="GGE",\n        scope="GENERAL",\n        project_id=None,\n        currency_code=currency_code,\n        lines=[\n            JournalLineInput(account_id=expense_account_id, debit_amount=amount, description=description),\n''',
    '''        document_type_code="GGE",\n        scope=scope,\n        project_id=project_id,\n        currency_code=currency_code,\n        lines=[\n            JournalLineInput(\n                account_id=expense_account_id,\n                debit_amount=amount,\n                project_id=project_id,\n                description=description,\n            ),\n''',
)

replace_once(
    "backend/app/models/treasury.py",
    '''class GeneralExpense(UUIDPrimaryKeyMixin, TimestampMixin, Base):\n    """Siempre scope=GENERAL, project_id=NULL. NO consume Project Budget\n    (orden maestra §28) -- se paga de inmediato contra Treasury."""\n''',
    '''class GeneralExpense(UUIDPrimaryKeyMixin, TimestampMixin, Base):\n    """Salida inmediata pagada desde Treasury. Su alcance/proyecto vive en el\n    AccountingDocument y JournalLine asociados; TreasuryAccount sigue siendo\n    estrictamente central y nunca pertenece a un proyecto."""\n''',
)

# ---------------------------------------------------------------------------
# Frontend service payloads
# ---------------------------------------------------------------------------
replace_once(
    "frontend/src/services/treasuryService.ts",
    '''  treasuryAccountId: string\n  counterAccountId: string\n  sender: string\n''',
    '''  treasuryAccountId: string\n  counterAccountId: string\n  originType: 'CAPITAL_CONTRIBUTION' | 'FINANCING' | 'OTHER_INCOME'\n  sender: string\n''',
)
replace_once(
    "frontend/src/services/treasuryService.ts",
    '''  treasuryAccountId: string\n  expenseAccountId: string\n  category: string\n''',
    '''  treasuryAccountId: string\n  expenseAccountId: string\n  scope: 'GENERAL' | 'PROJECT'\n  projectId?: string | null\n  category: string\n''',
)

# ---------------------------------------------------------------------------
# Treasury UI: categorized remittances + project-aware immediate expenses
# ---------------------------------------------------------------------------
replace_once(
    "frontend/src/features/treasury/TreasuryPage.tsx",
    '''import { masterDataService } from '../../services/masterDataService'\n''',
    '''import { masterDataService } from '../../services/masterDataService'\nimport { projectService } from '../../services/projectService'\n''',
)
replace_once(
    "frontend/src/features/treasury/TreasuryPage.tsx",
    '''const TREASURY_KIND_LABELS: Record<TreasuryAccount['kind'], string> = {\n  BANK: 'Banco',\n  CASH: 'Caja',\n  OTHER: 'Otra',\n}\n''',
    '''const TREASURY_KIND_LABELS: Record<TreasuryAccount['kind'], string> = {\n  BANK: 'Banco',\n  CASH: 'Caja',\n  OTHER: 'Otra',\n}\n\ntype RemittanceOriginType = 'CAPITAL_CONTRIBUTION' | 'FINANCING' | 'OTHER_INCOME'\nconst REMITTANCE_ORIGIN_LABELS: Record<RemittanceOriginType, string> = {\n  CAPITAL_CONTRIBUTION: 'Aporte de capital — Patrimonio',\n  FINANCING: 'Préstamo / financiamiento — Pasivo',\n  OTHER_INCOME: 'Otro ingreso — Ingreso',\n}\nconst REMITTANCE_ORIGIN_ACCOUNT_TYPES: Record<RemittanceOriginType, string> = {\n  CAPITAL_CONTRIBUTION: 'EQUITY',\n  FINANCING: 'LIABILITY',\n  OTHER_INCOME: 'REVENUE',\n}\n''',
)
replace_once(
    "frontend/src/features/treasury/TreasuryPage.tsx",
    '''  const remittanceCounterAccounts = glAccounts.filter(\n    (account) => account.isPostable && !assignedGlAccountIds.has(account.id),\n  )\n''',
    '''  const remittanceCounterAccounts = glAccounts.filter(\n    (account) =>\n      account.isPostable &&\n      !assignedGlAccountIds.has(account.id) &&\n      ['EQUITY', 'LIABILITY', 'REVENUE'].includes(account.accountType),\n  )\n''',
)

new_remittance_modal = r'''function RemittanceModal({
  companyId,
  treasuryAccounts,
  counterAccounts,
  onClose,
}: {
  companyId: string
  treasuryAccounts: TreasuryAccount[]
  counterAccounts: Account[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [treasuryAccountId, setTreasuryAccountId] = useState(treasuryAccounts[0]?.id ?? '')
  const [originType, setOriginType] = useState<RemittanceOriginType>('CAPITAL_CONTRIBUTION')
  const initialCounter = counterAccounts.find(
    (account) => account.accountType === REMITTANCE_ORIGIN_ACCOUNT_TYPES.CAPITAL_CONTRIBUTION,
  )
  const [counterAccountId, setCounterAccountId] = useState(initialCounter?.id ?? '')
  const [sender, setSender] = useState('')
  const [provider, setProvider] = useState('')
  const [channel, setChannel] = useState('TRANSFER')
  const [reference, setReference] = useState('')
  const [notes, setNotes] = useState('')
  const [remittanceDate, setRemittanceDate] = useState(new Date().toISOString().slice(0, 10))
  const [amount, setAmount] = useState<number | null>(null)
  const [fxRate, setFxRate] = useState(1)

  const selectedTreasuryAccount = treasuryAccounts.find((account) => account.id === treasuryAccountId)
  const selectedCurrency = selectedTreasuryAccount?.currencyCode ?? 'HNL'
  const eligibleCounterAccounts = counterAccounts.filter(
    (account) => account.accountType === REMITTANCE_ORIGIN_ACCOUNT_TYPES[originType],
  )

  const mutation = useMutation({
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: CreateRemittancePayload
      idempotencyKey: string
    }) => treasuryService.createRemittance(payload, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'remittances'] })
      onClose()
    },
  })

  if (treasuryAccounts.length === 0 || counterAccounts.length === 0) {
    return (
      <Modal open title="Registrar remesa" onClose={onClose}>
        <EmptyState
          title="Faltan cuentas para registrar la remesa"
          description="Configura una cuenta de Tesorería y una cuenta registrable de Patrimonio, Pasivo o Ingreso antes de continuar."
        />
      </Modal>
    )
  }

  return (
    <Modal open title="Registrar remesa" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate({
            payload: {
              companyId,
              treasuryAccountId,
              counterAccountId,
              originType,
              sender,
              provider: provider || null,
              channel: channel || null,
              reference: reference || null,
              currencyCode: selectedCurrency,
              originalAmount: String(amount ?? 0),
              fxRate: String(selectedCurrency === 'HNL' ? 1 : fxRate),
              remittanceDate,
              notes: notes || null,
            },
            idempotencyKey: crypto.randomUUID(),
          })
        }}
      >
        <p className="nx-field__hint">
          Las remesas son entradas de Tesorería CENTRAL y nunca piden proyecto. Cobros de clientes se registran en Cuentas por cobrar y movimientos entre bancos en Transferencia entre cuentas.
        </p>
        <Select
          name="treasuryAccountId"
          label="Cuenta receptora"
          value={treasuryAccountId}
          onChange={(event) => {
            setTreasuryAccountId(event.target.value)
            setFxRate(1)
          }}
          required
        >
          {treasuryAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name} — {account.currencyCode}
            </option>
          ))}
        </Select>
        <Select
          name="originType"
          label="Origen / naturaleza de la entrada"
          value={originType}
          onChange={(event) => {
            const next = event.target.value as RemittanceOriginType
            setOriginType(next)
            const firstMatching = counterAccounts.find(
              (account) => account.accountType === REMITTANCE_ORIGIN_ACCOUNT_TYPES[next],
            )
            setCounterAccountId(firstMatching?.id ?? '')
          }}
          required
        >
          {Object.entries(REMITTANCE_ORIGIN_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select
          name="counterAccountId"
          label="Cuenta contable de origen"
          value={counterAccountId}
          onChange={(event) => setCounterAccountId(event.target.value)}
          required
        >
          {eligibleCounterAccounts.length === 0 ? (
            <option value="">No hay cuentas compatibles configuradas</option>
          ) : null}
          {eligibleCounterAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.code} · {account.name}
            </option>
          ))}
        </Select>
        <label className="nx-field">
          <span className="nx-field__label">Fecha</span>
          <input
            className="nx-input"
            type="date"
            value={remittanceDate}
            onChange={(event) => setRemittanceDate(event.target.value)}
            required
          />
        </label>
        <label className="nx-field">
          <span className="nx-field__label">Documento / referencia</span>
          <input
            className="nx-input"
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            placeholder="Ej. transferencia o comprobante bancario"
          />
        </label>
        <label className="nx-field">
          <span className="nx-field__label">Remitente</span>
          <input
            className="nx-input"
            value={sender}
            onChange={(event) => setSender(event.target.value)}
            required
          />
        </label>
        <label className="nx-field">
          <span className="nx-field__label">Banco / proveedor del envío</span>
          <input
            className="nx-input"
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
            placeholder="Opcional"
          />
        </label>
        <Select
          name="channel"
          label="Método / canal"
          value={channel}
          onChange={(event) => setChannel(event.target.value)}
        >
          <option value="TRANSFER">Transferencia</option>
          <option value="CASH">Efectivo</option>
          <option value="CHECK">Cheque</option>
          <option value="OTHER">Otro</option>
        </Select>
        <MoneyInput label={`Monto (${selectedCurrency})`} value={amount} onChange={setAmount} />
        {selectedCurrency !== 'HNL' ? (
          <label className="nx-field">
            <span className="nx-field__label">Tipo de cambio a HNL</span>
            <input
              className="nx-input"
              type="number"
              min="0.000001"
              step="0.000001"
              value={fxRate}
              onChange={(event) => setFxRate(Number(event.target.value))}
              required
            />
          </label>
        ) : null}
        <label className="nx-field">
          <span className="nx-field__label">Notas</span>
          <input
            className="nx-input"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Opcional"
          />
        </label>
        {eligibleCounterAccounts.length === 0 ? (
          <p className="nx-field__error">
            Crea primero una cuenta registrable compatible con la naturaleza seleccionada.
          </p>
        ) : null}
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={
            !treasuryAccountId ||
            !counterAccountId ||
            !sender.trim() ||
            !remittanceDate ||
            !amount ||
            amount <= 0 ||
            (selectedCurrency !== 'HNL' && fxRate <= 0)
          }
        >
          Registrar remesa
        </Button>
      </form>
    </Modal>
  )
}'''
regex_once(
    "frontend/src/features/treasury/TreasuryPage.tsx",
    r"function RemittanceModal\(\{.*?\n\}\n\nfunction GeneralExpenseModal\(",
    new_remittance_modal + "\n\nfunction GeneralExpenseModal(",
)

new_general_expense_modal = r'''function GeneralExpenseModal({
  companyId,
  treasuryAccounts,
  expenseAccounts,
  onClose,
}: {
  companyId: string
  treasuryAccounts: TreasuryAccount[]
  expenseAccounts: { id: string; name: string }[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [scope, setScope] = useState<'GENERAL' | 'PROJECT'>('GENERAL')
  const [projectId, setProjectId] = useState('')
  const [treasuryAccountId, setTreasuryAccountId] = useState(treasuryAccounts[0]?.id ?? '')
  const [expenseAccountId, setExpenseAccountId] = useState(expenseAccounts[0]?.id ?? '')
  const [category, setCategory] = useState('administracion')
  const [description, setDescription] = useState('')
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10))
  const [amount, setAmount] = useState<number | null>(null)

  const projectsQuery = useQuery({
    queryKey: ['projects', companyId],
    queryFn: () => projectService.list(companyId),
  })
  const projects = Array.isArray(projectsQuery.data) ? projectsQuery.data : []
  const selectedTreasuryAccount = treasuryAccounts.find((account) => account.id === treasuryAccountId)
  const selectedCurrency = selectedTreasuryAccount?.currencyCode ?? 'HNL'

  const mutation = useMutation({
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: CreateGeneralExpensePayload
      idempotencyKey: string
    }) => treasuryService.createGeneralExpense(payload, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      onClose()
    },
  })

  if (expenseAccounts.length === 0 || treasuryAccounts.length === 0) {
    return (
      <Modal open title="Registrar salida / gasto" onClose={onClose}>
        <EmptyState title="Falta una cuenta de Tesorería o una cuenta registrable de gasto." />
      </Modal>
    )
  }

  return (
    <Modal open title="Registrar salida / gasto" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate({
            payload: {
              companyId,
              treasuryAccountId,
              expenseAccountId,
              scope,
              projectId: scope === 'PROJECT' ? projectId : null,
              category,
              amount: String(amount ?? 0),
              currencyCode: selectedCurrency,
              expenseDate,
              description,
            },
            idempotencyKey: crypto.randomUUID(),
          })
        }}
      >
        <Select
          name="expenseScope"
          label="Alcance del gasto"
          value={scope}
          onChange={(event) => {
            const next = event.target.value as 'GENERAL' | 'PROJECT'
            setScope(next)
            if (next !== 'PROJECT') setProjectId('')
          }}
          required
        >
          <option value="GENERAL">General — Sin proyecto</option>
          <option value="PROJECT">Proyecto — Atribuible a una obra</option>
        </Select>
        {scope === 'PROJECT' ? (
          <Select
            name="projectId"
            label="Proyecto"
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            required
          >
            <option value="">Selecciona un proyecto…</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.code ? `${project.code} — ` : ''}{project.name}
              </option>
            ))}
          </Select>
        ) : null}
        <Select
          name="treasuryAccountId"
          label="Cuenta pagadora"
          value={treasuryAccountId}
          onChange={(event) => setTreasuryAccountId(event.target.value)}
          required
        >
          {treasuryAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name} — {account.currencyCode}
            </option>
          ))}
        </Select>
        <Select
          name="expenseAccountId"
          label="Cuenta de gasto"
          value={expenseAccountId}
          onChange={(event) => setExpenseAccountId(event.target.value)}
          required
        >
          {expenseAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <Select
          name="category"
          label="Categoría"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          required
        >
          <option value="combustible">Combustible / gasolina</option>
          <option value="alimentacion">Alimentación / comida</option>
          <option value="materiales">Materiales / compras menores</option>
          <option value="mano_de_obra">Mano de obra</option>
          <option value="honorarios">Honorarios / servicios personales</option>
          <option value="transporte">Transporte</option>
          <option value="herramientas">Herramientas</option>
          <option value="administracion">Administración</option>
          <option value="otros">Otros gastos</option>
        </Select>
        <label className="nx-field">
          <span className="nx-field__label">Fecha</span>
          <input
            className="nx-input"
            type="date"
            value={expenseDate}
            onChange={(event) => setExpenseDate(event.target.value)}
            required
          />
        </label>
        <label className="nx-field">
          <span className="nx-field__label">Descripción</span>
          <input
            className="nx-input"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            required
          />
        </label>
        <MoneyInput label={`Monto (${selectedCurrency})`} value={amount} onChange={setAmount} />
        <p className="nx-field__hint">
          Retiros de socios, préstamos y reembolsos no deben clasificarse automáticamente como gasto: usa el flujo y la cuenta contable que corresponda a su naturaleza.
        </p>
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={
            !amount ||
            amount <= 0 ||
            !description.trim() ||
            !expenseDate ||
            !treasuryAccountId ||
            !expenseAccountId ||
            (scope === 'PROJECT' && !projectId)
          }
        >
          Registrar salida
        </Button>
      </form>
    </Modal>
  )
}'''
regex_once(
    "frontend/src/features/treasury/TreasuryPage.tsx",
    r"function GeneralExpenseModal\(\{.*?\n\}\n\nfunction TransferModal\(",
    new_general_expense_modal + "\n\nfunction TransferModal(",
)

# Keep the dashboard action label aligned with the expanded scope.
replace_once(
    "frontend/src/features/treasury/TreasuryPage.tsx",
    '''            Registrar gasto general\n''',
    '''            Registrar salida / gasto\n''',
)

# ---------------------------------------------------------------------------
# Accounts Payable: explicit treasury account + amount + date on payment
# ---------------------------------------------------------------------------
replace_once(
    "frontend/src/features/treasury/AccountsPayablePage.tsx",
    '''import { formatMoney } from '../../utils/currency'\n''',
    '''import { formatMoney } from '../../utils/currency'\nimport type { TreasuryAccount } from '../../types/treasury'\n''',
)
replace_once(
    "frontend/src/features/treasury/AccountsPayablePage.tsx",
    '''            <PaySupplierInvoiceButton\n              invoiceId={row.id}\n              treasuryAccountId={treasuryAccounts[0].id}\n              remaining={row.amount + row.taxAmount - row.amountPaid}\n            />\n''',
    '''            <PaySupplierInvoiceButton\n              invoiceId={row.id}\n              treasuryAccounts={treasuryAccounts}\n              currencyCode={row.currencyCode}\n              remaining={row.amount + row.taxAmount - row.amountPaid}\n            />\n''',
)
new_pay_button = r'''function PaySupplierInvoiceButton({
  invoiceId,
  treasuryAccounts,
  currencyCode,
  remaining,
}: {
  invoiceId: string
  treasuryAccounts: TreasuryAccount[]
  currencyCode: string
  remaining: number
}) {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const eligibleTreasuryAccounts = treasuryAccounts.filter(
    (account) => account.status === 'ACTIVE' && account.currencyCode === currencyCode,
  )
  const [open, setOpen] = useState(false)
  const [treasuryAccountId, setTreasuryAccountId] = useState(eligibleTreasuryAccounts[0]?.id ?? '')
  const [amount, setAmount] = useState<number | null>(remaining)
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10))

  const mutation = useMutation({
    mutationFn: async ({
      payload,
      idempotencyKey,
    }: {
      payload: Record<string, unknown>
      idempotencyKey: string
    }) => {
      await apService.pay(invoiceId, payload, idempotencyKey)
      return apService.getInvoice(invoiceId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices'] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      setOpen(false)
    },
    onError: (error) => handleMutationError(error, 'Pagar factura de proveedor'),
  })

  return (
    <>
      <Button
        variant="ghost"
        onClick={() => setOpen(true)}
        disabled={eligibleTreasuryAccounts.length === 0}
      >
        Pagar saldo ({remaining.toFixed(2)})
      </Button>
      {open ? (
        <Modal open title="Pagar factura de proveedor" onClose={() => setOpen(false)}>
          <form
            className="nx-treasury__form"
            onSubmit={(event) => {
              event.preventDefault()
              mutation.mutate({
                payload: {
                  treasuryAccountId,
                  amount: String(amount ?? 0),
                  paymentDate,
                },
                idempotencyKey: crypto.randomUUID(),
              })
            }}
          >
            <Select
              name="paymentTreasuryAccountId"
              label="Cuenta pagadora"
              value={treasuryAccountId}
              onChange={(event) => setTreasuryAccountId(event.target.value)}
              required
            >
              {eligibleTreasuryAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name} — {account.currencyCode}
                </option>
              ))}
            </Select>
            <MoneyInput label={`Monto a pagar (${currencyCode})`} value={amount} onChange={setAmount} />
            <label className="nx-field">
              <span className="nx-field__label">Fecha de pago</span>
              <input
                className="nx-input"
                type="date"
                value={paymentDate}
                onChange={(event) => setPaymentDate(event.target.value)}
                required
              />
            </label>
            <p className="nx-field__hint">
              El proyecto ya viene de la factura; aquí solo eliges desde qué banco o caja sale el dinero.
            </p>
            {mutation.isError ? (
              <p className="nx-field__error">{(mutation.error as Error).message}</p>
            ) : null}
            <Button
              type="submit"
              loading={mutation.isPending}
              disabled={!treasuryAccountId || !amount || amount <= 0 || amount > remaining || !paymentDate}
            >
              Confirmar pago
            </Button>
          </form>
        </Modal>
      ) : null}
    </>
  )
}'''
regex_once(
    "frontend/src/features/treasury/AccountsPayablePage.tsx",
    r"function PaySupplierInvoiceButton\(\{.*\Z",
    new_pay_button + "\n",
)

# ---------------------------------------------------------------------------
# Accounts Receivable: explicit treasury account + amount + date on collection
# ---------------------------------------------------------------------------
replace_once(
    "frontend/src/features/treasury/AccountsReceivablePage.tsx",
    '''import { formatMoney } from '../../utils/currency'\n''',
    '''import { formatMoney } from '../../utils/currency'\nimport type { TreasuryAccount } from '../../types/treasury'\n''',
)
replace_once(
    "frontend/src/features/treasury/AccountsReceivablePage.tsx",
    '''            <CollectButton\n              invoiceId={row.id}\n              treasuryAccountId={treasuryAccounts[0].id}\n              remaining={row.amount - row.amountCollected}\n            />\n''',
    '''            <CollectButton\n              invoiceId={row.id}\n              treasuryAccounts={treasuryAccounts}\n              currencyCode={row.currencyCode}\n              remaining={row.amount - row.amountCollected}\n            />\n''',
)
new_collect_button = r'''function CollectButton({
  invoiceId,
  treasuryAccounts,
  currencyCode,
  remaining,
}: {
  invoiceId: string
  treasuryAccounts: TreasuryAccount[]
  currencyCode: string
  remaining: number
}) {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const eligibleTreasuryAccounts = treasuryAccounts.filter(
    (account) => account.status === 'ACTIVE' && account.currencyCode === currencyCode,
  )
  const [open, setOpen] = useState(false)
  const [treasuryAccountId, setTreasuryAccountId] = useState(eligibleTreasuryAccounts[0]?.id ?? '')
  const [amount, setAmount] = useState<number | null>(remaining)
  const [receiptDate, setReceiptDate] = useState(new Date().toISOString().slice(0, 10))

  const mutation = useMutation({
    mutationFn: async ({
      payload,
      idempotencyKey,
    }: {
      payload: Record<string, unknown>
      idempotencyKey: string
    }) => {
      await arService.collect(invoiceId, payload, idempotencyKey)
      return arService.getInvoice(invoiceId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ar', 'customer-invoices'] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      setOpen(false)
    },
    onError: (error) => handleMutationError(error, 'Cobrar factura de cliente'),
  })

  return (
    <>
      <Button
        variant="ghost"
        onClick={() => setOpen(true)}
        disabled={eligibleTreasuryAccounts.length === 0}
      >
        Cobrar saldo ({remaining.toFixed(2)})
      </Button>
      {open ? (
        <Modal open title="Registrar cobro de cliente" onClose={() => setOpen(false)}>
          <form
            className="nx-treasury__form"
            onSubmit={(event) => {
              event.preventDefault()
              mutation.mutate({
                payload: {
                  treasuryAccountId,
                  amount: String(amount ?? 0),
                  receiptDate,
                },
                idempotencyKey: crypto.randomUUID(),
              })
            }}
          >
            <Select
              name="collectionTreasuryAccountId"
              label="Cuenta receptora"
              value={treasuryAccountId}
              onChange={(event) => setTreasuryAccountId(event.target.value)}
              required
            >
              {eligibleTreasuryAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name} — {account.currencyCode}
                </option>
              ))}
            </Select>
            <MoneyInput label={`Monto a cobrar (${currencyCode})`} value={amount} onChange={setAmount} />
            <label className="nx-field">
              <span className="nx-field__label">Fecha de cobro</span>
              <input
                className="nx-input"
                type="date"
                value={receiptDate}
                onChange={(event) => setReceiptDate(event.target.value)}
                required
              />
            </label>
            <p className="nx-field__hint">
              El alcance/proyecto ya viene de la factura; selecciona el banco o caja donde realmente entró el dinero.
            </p>
            {mutation.isError ? (
              <p className="nx-field__error">{(mutation.error as Error).message}</p>
            ) : null}
            <Button
              type="submit"
              loading={mutation.isPending}
              disabled={!treasuryAccountId || !amount || amount <= 0 || amount > remaining || !receiptDate}
            >
              Confirmar cobro
            </Button>
          </form>
        </Modal>
      ) : null}
    </>
  )
}'''
regex_once(
    "frontend/src/features/treasury/AccountsReceivablePage.tsx",
    r"function CollectButton\(\{.*\Z",
    new_collect_button + "\n",
)

# ---------------------------------------------------------------------------
# Update one legacy test that used an EXPENSE account as a fake remittance
# counter-account. That is precisely what the new origin invariant forbids.
# ---------------------------------------------------------------------------
replace_once(
    "backend/tests/test_treasury.py",
    '''    company, bank, _cash, _contributions, expense = _setup(client)\n\n    client.post(\n        "/api/treasury/remittances",\n        json={\n            "companyId": company["id"],\n            "treasuryAccountId": bank["id"],\n            "counterAccountId": expense["id"],\n            "sender": "Aporte inicial",\n''',
    '''    company, bank, _cash, contributions, expense = _setup(client)\n\n    client.post(\n        "/api/treasury/remittances",\n        json={\n            "companyId": company["id"],\n            "treasuryAccountId": bank["id"],\n            "counterAccountId": contributions["id"],\n            "originType": "CAPITAL_CONTRIBUTION",\n            "sender": "Aporte inicial",\n''',
)

# ---------------------------------------------------------------------------
# Backend regression coverage for the new invariants
# ---------------------------------------------------------------------------
backend_test = r'''from tests.helpers import create_account, create_company, create_treasury_account, login_admin


def _setup_financial_accounts(client):
    company = create_company(client)
    bank_gl = create_account(
        client, company_id=company["id"], code="1102", name="Banco Atlántida — HNL", account_type="ASSET"
    )
    bank = create_treasury_account(
        client, company_id=company["id"], gl_account_id=bank_gl["id"], name="Banco Atlántida HNL"
    )
    equity = create_account(
        client, company_id=company["id"], code="3101", name="Capital y aportaciones", account_type="EQUITY"
    )
    liability = create_account(
        client, company_id=company["id"], code="2201", name="Préstamos recibidos", account_type="LIABILITY"
    )
    revenue = create_account(
        client, company_id=company["id"], code="4201", name="Otros ingresos", account_type="REVENUE"
    )
    expense = create_account(
        client, company_id=company["id"], code="5101", name="Costos directos de construcción", account_type="EXPENSE"
    )
    return company, bank, equity, liability, revenue, expense


def test_remittance_origin_type_restricts_counter_account(client):
    login_admin(client)
    company, bank, equity, liability, revenue, expense = _setup_financial_accounts(client)

    valid_cases = [
        ("CAPITAL_CONTRIBUTION", equity["id"]),
        ("FINANCING", liability["id"]),
        ("OTHER_INCOME", revenue["id"]),
    ]
    for index, (origin_type, counter_account_id) in enumerate(valid_cases, start=1):
        response = client.post(
            "/api/treasury/remittances",
            json={
                "companyId": company["id"],
                "treasuryAccountId": bank["id"],
                "counterAccountId": counter_account_id,
                "originType": origin_type,
                "sender": f"Entrada válida {index}",
                "currencyCode": "HNL",
                "originalAmount": "100.00",
                "remittanceDate": "2026-08-27",
            },
        )
        assert response.status_code == 201, response.text

    invalid = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": expense["id"],
            "originType": "CAPITAL_CONTRIBUTION",
            "sender": "Entrada inválida",
            "currencyCode": "HNL",
            "originalAmount": "100.00",
            "remittanceDate": "2026-08-27",
        },
    )
    assert invalid.status_code == 422, invalid.text
    assert invalid.json()["error"]["code"] == "NXR-FINANCIAL-001"


def test_project_immediate_expense_posts_project_dimension(client):
    login_admin(client)
    company, bank, equity, _liability, _revenue, expense = _setup_financial_accounts(client)
    project_response = client.post(
        "/api/projects",
        json={
            "companyId": company["id"],
            "name": "Cerco Perimetral",
            "code": "PRJ-CERCO",
            "currencyCode": "HNL",
        },
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()

    funding = client.post(
        "/api/treasury/remittances",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "counterAccountId": equity["id"],
            "originType": "CAPITAL_CONTRIBUTION",
            "sender": "Aporte inicial",
            "currencyCode": "HNL",
            "originalAmount": "5000.00",
            "remittanceDate": "2026-08-27",
        },
    )
    assert funding.status_code == 201, funding.text

    response = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "expenseAccountId": expense["id"],
            "scope": "PROJECT",
            "projectId": project["id"],
            "category": "combustible",
            "amount": "750.00",
            "currencyCode": "HNL",
            "expenseDate": "2026-08-27",
            "description": "Gasolina para Cerco Perimetral",
        },
    )
    assert response.status_code == 201, response.text

    document = client.get(
        f"/api/accounting/journal-entries/{response.json()['accountingDocumentId']}"
    )
    assert document.status_code == 200, document.text
    body = document.json()
    assert body["scope"] == "PROJECT"
    assert body["projectId"] == project["id"]


def test_project_immediate_expense_requires_project_id(client):
    login_admin(client)
    company, bank, _equity, _liability, _revenue, expense = _setup_financial_accounts(client)
    response = client.post(
        "/api/treasury/general-expenses",
        json={
            "companyId": company["id"],
            "treasuryAccountId": bank["id"],
            "expenseAccountId": expense["id"],
            "scope": "PROJECT",
            "category": "combustible",
            "amount": "100.00",
            "currencyCode": "HNL",
            "expenseDate": "2026-08-27",
            "description": "Debe exigir proyecto",
        },
    )
    assert response.status_code == 422, response.text
'''
write("backend/tests/test_treasury_financial_flows.py", backend_test)

# ---------------------------------------------------------------------------
# Frontend regression coverage for the four UI corrections.
# ---------------------------------------------------------------------------
frontend_test = r'''import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const company = {
  id: 'c1',
  name: 'NEXORA GROUP',
  code: null,
  legalName: null,
  functionalCurrencyCode: 'HNL',
  country: null,
  fiscalId: null,
}
const treasuryAccounts = [
  {
    id: 't-atl', companyId: 'c1', name: 'Banco Atlántida HNL', kind: 'BANK', institution: 'Banco Atlántida', accountReference: null, currencyCode: 'HNL', glAccountId: 'a-bank-1', status: 'ACTIVE', balance: '1000.00',
  },
  {
    id: 't-bac', companyId: 'c1', name: 'Banco BAC HNL', kind: 'BANK', institution: 'BAC', accountReference: null, currencyCode: 'HNL', glAccountId: 'a-bank-2', status: 'ACTIVE', balance: '500.00',
  },
]

function authResponse() {
  return { id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }
}

function baseResponse(url: string) {
  if (url.includes('/auth/me')) return authResponse()
  if (url.includes('/master-data/companies')) return [company]
  if (url.includes('/treasury/accounts')) return treasuryAccounts
  if (url.includes('/projects?company_id=c1')) {
    return [{ id: 'p1', companyId: 'c1', name: 'Cerco Perimetral', code: 'CERCO', currencyCode: 'HNL', status: 'PLANNING' }]
  }
  return undefined
}

describe('Treasury financial flow corrections', () => {
  it('classifies remittances and never asks for a project', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      const base = baseResponse(url)
      if (base !== undefined) return Promise.resolve({ ok: true, status: 200, json: async () => base } as Response)
      if (url.includes('/master-data/accounts')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [
          { id: 'a-bank-1', code: '1102', name: 'Banco Atlántida — HNL', accountType: 'ASSET', parentId: null, isPostable: true },
          { id: 'a-bank-2', code: '1104', name: 'Banco BAC — HNL', accountType: 'ASSET', parentId: null, isPostable: true },
          { id: 'eq', code: '3101', name: 'Capital y aportaciones', accountType: 'EQUITY', parentId: null, isPostable: true },
          { id: 'liab', code: '2201', name: 'Préstamos recibidos', accountType: 'LIABILITY', parentId: null, isPostable: true },
          { id: 'rev', code: '4201', name: 'Otros ingresos', accountType: 'REVENUE', parentId: null, isPostable: true },
          { id: 'exp', code: '6101', name: 'Gastos administrativos', accountType: 'EXPENSE', parentId: null, isPostable: true },
        ] } as Response)
      }
      if (url.includes('/treasury/remittances')) return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }))

    render(renderApp('/finanzas/tesoreria'))
    await userEvent.click(await screen.findByRole('button', { name: /registrar remesa/i }))

    expect(screen.getByLabelText(/origen \/ naturaleza de la entrada/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/^proyecto$/i)).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: /3101 · Capital y aportaciones/i })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /Gastos administrativos/i })).not.toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText(/origen \/ naturaleza/i), 'FINANCING')
    expect(screen.getByRole('option', { name: /2201 · Préstamos recibidos/i })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /3101 · Capital/i })).not.toBeInTheDocument()
  })

  it('requires a project only when an immediate expense is project-attributable', async () => {
    let posted: Record<string, unknown> | null = null
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const base = baseResponse(url)
      if (base !== undefined) return Promise.resolve({ ok: true, status: 200, json: async () => base } as Response)
      if (url.includes('/master-data/accounts')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [
          { id: 'a-bank-1', code: '1102', name: 'Banco Atlántida — HNL', accountType: 'ASSET', parentId: null, isPostable: true },
          { id: 'a-bank-2', code: '1104', name: 'Banco BAC — HNL', accountType: 'ASSET', parentId: null, isPostable: true },
          { id: 'exp', code: '5101', name: 'Costos directos de construcción', accountType: 'EXPENSE', parentId: null, isPostable: true },
        ] } as Response)
      }
      if (url.includes('/treasury/remittances')) return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      if (url.includes('/treasury/general-expenses') && init?.method === 'POST') {
        posted = JSON.parse(String(init.body))
        return Promise.resolve({ ok: true, status: 201, json: async () => ({ id: 'g1', accountingDocumentId: 'doc1' }) } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }))

    render(renderApp('/finanzas/tesoreria'))
    await userEvent.click(await screen.findByRole('button', { name: /registrar salida \/ gasto/i }))
    expect(screen.queryByLabelText(/^proyecto$/i)).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText(/alcance del gasto/i), 'PROJECT')
    await userEvent.selectOptions(await screen.findByLabelText(/^proyecto$/i), 'p1')
    await userEvent.type(screen.getByLabelText(/descripción/i), 'Gasolina de la obra')
    await userEvent.type(screen.getByLabelText(/monto/i), '750')
    await userEvent.click(screen.getByRole('button', { name: /registrar salida/i }))

    await waitFor(() => expect(posted).toMatchObject({ scope: 'PROJECT', projectId: 'p1', treasuryAccountId: 't-atl' }))
  })

  it('lets the user choose the actual bank when paying a supplier invoice', async () => {
    let paymentPayload: Record<string, unknown> | null = null
    const invoice = { id: 'ap1', supplierId: 's1', invoiceNumber: 'FAC-P-1', scope: 'PROJECT', projectId: 'p1', currencyCode: 'HNL', amount: 1000, taxAmount: 0, amountPaid: 0, dueDate: '2026-09-01', status: 'APPROVED' }
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const base = baseResponse(url)
      if (base !== undefined) return Promise.resolve({ ok: true, status: 200, json: async () => base } as Response)
      if (url.includes('/master-data/accounts')) return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      if (url.includes('/procurement/suppliers')) return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 's1', companyId: 'c1', legalName: 'Proveedor', status: 'ACTIVE' }] } as Response)
      if (url.includes('/ap/supplier-invoices/ap1/pay')) {
        paymentPayload = JSON.parse(String(init?.body))
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
      }
      if (url.includes('/ap/supplier-invoices/ap1')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ ...invoice, status: 'PAID', amountPaid: 1000 }) } as Response)
      if (url.includes('/ap/supplier-invoices')) return Promise.resolve({ ok: true, status: 200, json: async () => [invoice] } as Response)
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }))

    render(renderApp('/finanzas/cuentas-por-pagar'))
    await userEvent.click(await screen.findByRole('button', { name: /pagar saldo/i }))
    await userEvent.selectOptions(screen.getByLabelText(/cuenta pagadora/i), 't-bac')
    await userEvent.click(screen.getByRole('button', { name: /confirmar pago/i }))
    await waitFor(() => expect(paymentPayload).toMatchObject({ treasuryAccountId: 't-bac', amount: '1000' }))
  })

  it('lets the user choose the actual bank when collecting a customer invoice', async () => {
    let collectionPayload: Record<string, unknown> | null = null
    const invoice = { id: 'ar1', customerId: 'cu1', invoiceNumber: 'FAC-C-1', scope: 'PROJECT', projectId: 'p1', currencyCode: 'HNL', amount: 800, amountCollected: 0, dueDate: '2026-09-01', status: 'APPROVED' }
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const base = baseResponse(url)
      if (base !== undefined) return Promise.resolve({ ok: true, status: 200, json: async () => base } as Response)
      if (url.includes('/master-data/accounts')) return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      if (url.includes('/crm/customers')) return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 'cu1', companyId: 'c1', legalName: 'Cliente', status: 'ACTIVE' }] } as Response)
      if (url.includes('/ar/customer-invoices/ar1/collect')) {
        collectionPayload = JSON.parse(String(init?.body))
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
      }
      if (url.includes('/ar/customer-invoices/ar1')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ ...invoice, status: 'COLLECTED', amountCollected: 800 }) } as Response)
      if (url.includes('/ar/customer-invoices')) return Promise.resolve({ ok: true, status: 200, json: async () => [invoice] } as Response)
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }))

    render(renderApp('/finanzas/cuentas-por-cobrar'))
    await userEvent.click(await screen.findByRole('button', { name: /cobrar saldo/i }))
    await userEvent.selectOptions(screen.getByLabelText(/cuenta receptora/i), 't-bac')
    await userEvent.click(screen.getByRole('button', { name: /confirmar cobro/i }))
    await waitFor(() => expect(collectionPayload).toMatchObject({ treasuryAccountId: 't-bac', amount: '800' }))
  })
})
'''
write("frontend/tests/TreasuryFinancialFlows.test.tsx", frontend_test)

# Remove the temporary patch artifacts in the same commit that carries the real fix.
for temporary in (
    ROOT / "scripts/apply_financial_flow_fixes.py",
    ROOT / ".github/workflows/apply-financial-flow-fixes.yml",
):
    if temporary.exists():
        temporary.unlink()

print("Treasury financial flow corrections applied successfully")
