import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Select } from '../../design-system'
import { projectService } from '../../services/projectService'
import { RequiresActiveProject } from './RequiresActiveProject'

function WBSTree({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [parentId, setParentId] = useState('')

  const wbsQuery = useQuery({
    queryKey: ['wbs', projectId],
    queryFn: () => projectService.listWbs(projectId),
  })

  const createNode = useMutation({
    mutationFn: () =>
      projectService.createWbs(projectId, { code, name, parentId: parentId || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wbs', projectId] })
      setCode('')
      setName('')
      setParentId('')
    },
  })

  if (wbsQuery.isLoading) return <LoadingState label="Cargando WBS…" />
  if (wbsQuery.isError) {
    return <ErrorState description="No se pudo cargar el WBS." onRetry={() => wbsQuery.refetch()} />
  }

  const nodes = wbsQuery.data ?? []

  return (
    <div>
      <Card title="Nuevo nodo de WBS">
        <Input label="Código" value={code} onChange={(event) => setCode(event.target.value)} placeholder="02.01" />
        <Input label="Nombre" value={name} onChange={(event) => setName(event.target.value)} placeholder="EXCAVACIÓN" />
        <Select label="Nodo padre (opcional)" value={parentId} onChange={(event) => setParentId(event.target.value)}>
          <option value="">— Raíz —</option>
          {nodes.map((node) => (
            <option key={node.id} value={node.id}>
              {node.code} — {node.name}
            </option>
          ))}
        </Select>
        <Button disabled={!code || !name || createNode.isPending} loading={createNode.isPending} onClick={() => createNode.mutate()}>
          Agregar nodo
        </Button>
      </Card>

      {nodes.length === 0 ? (
        <EmptyState icon="🧩" title="Sin WBS todavía" description="Agrega el primer nodo de la estructura de desglose de trabajo." />
      ) : (
        <ul className="nx-field__label" style={{ listStyle: 'none', padding: 0 }}>
          {nodes.map((node) => (
            <li key={node.id} style={{ paddingLeft: `${node.level * 24}px`, padding: '8px 0' }}>
              <strong>{node.code}</strong> — {node.name} <Badge>{node.status}</Badge>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function WBSPage() {
  return (
    <div>
      <h1 className="nx-dashboard__title">WBS — Estructura de Desglose de Trabajo</h1>
      <RequiresActiveProject>{(projectId) => <WBSTree projectId={projectId} />}</RequiresActiveProject>
    </div>
  )
}
