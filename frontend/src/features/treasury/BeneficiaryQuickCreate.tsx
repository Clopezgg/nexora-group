import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button, Input, Modal, Select } from '../../design-system'
import { useMutationError } from '../../hooks/useMutationError'
import { crmService } from '../../services/crmService'
import { procurementService } from '../../services/procurementService'
import { workforceService } from '../../services/workforceService'

type BeneficiaryType = 'SUPPLIER' | 'WORKER' | 'CUSTOMER'

const TYPE_LABELS: Record<BeneficiaryType, string> = {
  SUPPLIER: 'Proveedor',
  WORKER: 'Trabajador',
  CUSTOMER: 'Cliente',
}

/**
 * "Buscar o crear" beneficiario sin salir del flujo del comprobante
 * (ORDEN MAESTRA §30). Crea la entidad REAL (Proveedor / Trabajador / Cliente)
 * — nunca una tabla paralela `voucher_beneficiaries` — y devuelve la clave
 * `${tipo}:${id}` para autoseleccionarla.
 */
export function BeneficiaryQuickCreate({
  companyId,
  onCreated,
}: {
  companyId: string
  onCreated: (beneficiaryKey: string) => void
}) {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const [open, setOpen] = useState(false)
  const [type, setType] = useState<BeneficiaryType>('SUPPLIER')
  const [name, setName] = useState('')
  const [taxId, setTaxId] = useState('')

  const reset = () => {
    setName('')
    setTaxId('')
    setType('SUPPLIER')
  }

  const create = useMutation({
    mutationFn: async (): Promise<{ key: string }> => {
      if (type === 'SUPPLIER') {
        const supplier = await procurementService.createSupplier({
          companyId,
          legalName: name.trim(),
          taxId: taxId.trim() || undefined,
        })
        return { key: `SUPPLIER:${supplier.id}` }
      }
      if (type === 'CUSTOMER') {
        const customer = await crmService.createCustomer({
          companyId,
          legalName: name.trim(),
          taxId: taxId.trim() || undefined,
        })
        return { key: `CUSTOMER:${customer.id}` }
      }
      const worker = await workforceService.createWorker({
        companyId,
        fullName: name.trim(),
        standardHourlyRate: '0',
      })
      return { key: `WORKER:${worker.id}` }
    },
    onSuccess: ({ key }) => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'beneficiaries', companyId] })
      queryClient.invalidateQueries({ queryKey: ['procurement', 'suppliers', companyId] })
      onCreated(key)
      setOpen(false)
      reset()
    },
    onError: (error) => handleMutationError(error, 'Crear beneficiario'),
  })

  return (
    <>
      <Button variant="ghost" onClick={() => setOpen(true)}>
        + Crear beneficiario
      </Button>
      {open ? (
        <Modal open title="Nuevo beneficiario" onClose={() => setOpen(false)}>
          <form
            className="nx-treasury__form"
            onSubmit={(event) => {
              event.preventDefault()
              create.mutate()
            }}
          >
            <Select
              label="Tipo"
              value={type}
              onChange={(event) => setType(event.target.value as BeneficiaryType)}
            >
              {(Object.keys(TYPE_LABELS) as BeneficiaryType[]).map((key) => (
                <option key={key} value={key}>
                  {TYPE_LABELS[key]}
                </option>
              ))}
            </Select>
            <Input
              label={type === 'WORKER' ? 'Nombre completo' : 'Razón social'}
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
            {type !== 'WORKER' ? (
              <Input
                label="RTN / Tax ID (opcional)"
                value={taxId}
                onChange={(event) => setTaxId(event.target.value)}
              />
            ) : null}
            {create.isError ? (
              <p className="nx-field__error" role="alert">
                {(create.error as Error).message}
              </p>
            ) : null}
            <Button type="submit" loading={create.isPending} disabled={!name.trim()}>
              Crear y seleccionar
            </Button>
          </form>
        </Modal>
      ) : null}
    </>
  )
}
