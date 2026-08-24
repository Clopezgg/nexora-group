# Projects / WBS — contrato (Track B)

## Jerarquía

`Company → Project → WBSNode` (árbol arbitrario vía `parent_id` + `level`
calculado al crear, 0 = raíz). Ejemplo real soportado:

```
TORRE NEXORA (project)
├── 01 PRELIMINARES (level 0)
│   └── 01.01 TRAZO Y NIVELACIÓN (level 1)
├── 02 CIMENTACIÓN (level 0)
│   ├── 02.01 EXCAVACIÓN (level 1)
│   ├── 02.02 ZAPATAS (level 1)
│   └── 02.03 LOSAS (level 1)
```

## INV-TRE-002 — Project nunca posee dinero

`Project.__table__` no tiene, deliberadamente, ninguna columna de saldo/
cash/balance. Verificado por introspección real del esquema en
`tests/test_project_control.py::test_project_has_no_money_column` — no es
solo una convención de nombres, es una prueba automatizada que falla si
alguien agrega una columna así en el futuro.

## Planning

`Task`/`Milestone` (`app/models/planning.py`) cuelgan de `Project` y
opcionalmente de un `WBSNode`. `Task.depends_on_task_id` permite
dependencias simples (no es un motor CPM completo). Suficiente para una
vista de planeación usable, no para reemplazar MS Project.

## Progress

`ProgressRecord` (`app/models/progress.py`): planned%/actual% por
project/WBS/fecha. `evidence_ref` es una referencia libre (URL/id) hasta
que el track de Document Management (Azure Blob, orden maestra §68-70)
aterrice la entidad `Document` real — deuda intencional documentada aquí,
no oculta.

## API

```
GET/POST   /api/projects?company_id=...
GET        /api/projects/{id}
GET/POST   /api/projects/{id}/wbs
GET/POST   /api/projects/{id}/tasks
GET/POST   /api/projects/{id}/milestones
GET/POST   /api/projects/{id}/progress
```

Ver `docs/BUDGET_CONTROLLING.md` para Budget/Forecast/ChangeOrders.

## Pendiente (fuera de alcance de este track)

- Customer real en `Project.customer_ref` (hoy texto libre) — lo resuelve
  Track E cuando aterrice el modelo `Customer`.
- Gantt visual completo — el frontend de este track solo lista tasks/
  milestones; una vista de línea de tiempo más rica es responsabilidad de
  Track F (Experience) si se decide invertir en ella.
