# PR #152 — criterios comprobables de cierre

Esta nota delimita la comprobación del PR de reparación visual y de invariantes críticos; **no constituye certificación de producción**.

## Cambios que requieren regresión

- SAP Workstation importa su hoja estructural y no depende de geometría histórica de `AppLayout.css`.
- La navegación y el contenido principal son columnas de la **misma fila 1 del grid interno** `.nx-sap-workarea`; no confundirla con la fila 4 del grid exterior. La prueba visual mide alineación vertical y ausencia de superposición horizontal en escritorio.
- El lema del sidebar SAP usa el color de texto del sidebar y mantiene contraste en cada variante.
- El menú SAP móvil mide 40 px y el command row 88 px para alojar dos filas reales (toolbar 40 px y búsqueda 48 px). La prueba compara rectángulos DOM y exige que menú, command row y Topbar no se superpongan en 360, 390 y 768 px.
- La matriz visual y las pruebas de accesibilidad recorren navegaciones y tamaños reales, sin sustituir fallos con exclusiones.
- El recorrido de reversión AP obtiene una capacidad Protected Edit nueva antes de comprobar que un segundo reversal recibe el conflicto de negocio `409`; un `428` sin capacidad válida es la protección correcta y no debe eliminarse.
- La consulta del dashboard recibe una señal AbortSignal para cancelarse cuando la vista se desmonta y AuthProvider cancela consultas al cerrar sesión; validar WebKit sin filtrar errores de página.
- Project Setup: decisión `COMPLETED` y auditoría se realizan con la misma fila bloqueada. La prueba de dos sesiones concurrentes exige un solo proyecto y un solo `project.setup.complete` para el mismo run.
- Activos fijos: generación de depreciación y baja usan bloqueo exclusivo de la misma fila antes de comprobar el estado y sumar depreciaciones. La prueba con sesión obsoleta comprueba que no se emite DEP después de una transición terminal confirmada por otra sesión.

## Condiciones de aceptación

La revisión solo puede considerarse integrada después de comprobar los resultados del CI en el SHA exacto del PR, las capturas móviles y desktop, el merge seguro a `main`, el CI/deploy del SHA de `main` y el smoke y navegación productivos. Si falta alguna evidencia, registrarla como pendiente, sin llamar completo al sistema.
