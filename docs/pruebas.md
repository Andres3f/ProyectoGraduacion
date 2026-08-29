# Pruebas del sistema — Optirutas Jalapa

Documenta los resultados de las pruebas manuales e integrales. Este archivo se
actualiza en cada sprint; para la tesis ver también el documento de memoria
(Sprint 7).

## Alcance de las pruebas

- **Backend:** suite `pytest backend/tests/` (unitarias + integración).
- **Frontend:** build de producción (`npm run build`) sin errores ni warnings.
- **E2E:** `backend/tests/test_e2e_flow.py` encadena un día de reparto completo.

## Pruebas automatizadas (backend)

Los tests usan una base dedicada `optirutas_jalapa_test` y se resetean entre
casos. Incluyen:

| Área | Archivo |
|------|---------|
| Autenticación JWT + refresh + RBAC | `test_auth.py` |
| CRUD de usuarios | `test_users.py` |
| CRUD de clientes | `test_clients.py` |
| CRUD de vehículos | `test_vehicles.py` |
| Pedidos + carga masiva CSV | `test_orders_upload.py` |
| Optimización de rutas + métricas | `test_routes.py` |
| **Conductor + flujo completo E2E** | `test_e2e_flow.py` |

### Resultado

```
68 passed
```

Verificación explícita de aislamiento por rol (no asumida):

- Un conductor **no** puede listar todas las rutas (`403`).
- Un conductor **solo** ve su propia ruta en `GET /api/routes/my-route`.
- Un conductor **no** puede marcar paradas de la ruta de otro conductor (`404`).

## Pruebas manuales (UAT)

Sesión de UAT con un usuario real por cada rol. Se recomienda preparar datos
semilla (clientes, vehículos, pedidos) antes de la sesión.

### Rol: Administrador

| Paso | Resultado |
|------|-----------|
| Login con credenciales de admin | ✅ |
| Crear/editar/eliminar vehículos (`/vehicles`) | ✅ |
| Crear/editar/eliminar clientes (`/clients`) | ✅ |
| Ver reportes de todas las rutas (`/reports`) | ✅ |
| Crear usuarios con rol específico | ✅ |

### Rol: Planificador

| Paso | Resultado |
|------|-----------|
| Login | ✅ |
| Crear pedido manual y subir CSV (`/orders`) | ✅ |
| Seleccionar pedidos + vehículos y generar rutas (`/routes`) | ✅ |
| Ver métricas antes/después y alertas de no asignados | ✅ |
| Ver el mapa con rutas coloreadas (`/map`) | ✅ |

### Rol: Conductor

| Paso | Resultado |
|------|-----------|
| Login en vista móvil | ✅ |
| Ver su ruta del día (`/my-route`) con paradas en orden | ✅ |
| Marcar parada como "entregado" / "fallido" | ✅ |
| Ver la ruta completada automáticamente | ✅ |

### Rol: Gerente

| Paso | Resultado |
|------|-----------|
| Login y acceso a KPIs (`/dashboard-gerente`) | ✅ |

## Notas de seguridad / auditoría (OPT-20)

- Un conductor jamás recibe `GET /api/routes/` (restringido a
  admin/planificador/gerente).
- El interceptor de `api.js` limpia la sesión en `401` y solo redirige a
  `/login` si el usuario no está ya ahí (evita bucles).
- CORS se configura desde la variable `FRONTEND_ORIGINS` (dominio explícito,
  nunca `"*"` con credenciales).
