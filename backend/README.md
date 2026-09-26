# Backend — Optirutas Jalapa

API REST del sistema de optimización de rutas de reparto. FastAPI + SQLAlchemy
sobre PostgreSQL/PostGIS, con el solver de Google OR-Tools para el VRP con
capacidad y ventanas de tiempo.

Para la vista general del proyecto, la instalación con Docker y los roles, ver
el [README principal](../README.md).

## Requisitos

- **Python** 3.10+ (probado en 3.12)
- **PostgreSQL** 15 con la extensión **PostGIS** (los modelos usan `Geography`)
- Opcional: clave de **OpenRouteService** para distancias y geometría reales

## Instalación y arranque local

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # y ajusta POSTGRES_HOST=localhost
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger UI:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

Al arrancar, `app/main.py` crea las tablas si no existen y siembra el usuario
`admin`. No hace falta levantar el contenedor `db` de Docker si usas el
PostgreSQL local.

## Datos de demostración

```bash
source venv/bin/activate
python -m app.seed
```

El seed es **idempotente** (puede correrse varias veces sin duplicar datos) y
genera usuarios de los cuatro roles, clientes en Jalapa, vehículos, pedidos y
rutas ya optimizadas, para poder ver el dashboard del gerente desde el primer
arranque.

| Rol | Email | Contraseña |
|-----|-------|------------|
| Administrador | `admin@optirutas.com` | `Admin123!` |
| Planificador | `planificador@optirutas.com` | `Planif123!` |
| Conductor | `conductor@optirutas.com` | `Conduc123!` |
| Gerente | `gerente@optirutas.com` | `Gerente123!` |

## Estructura

```
backend/
├── app/
│   ├── main.py              # App FastAPI, CORS, creación de tablas y admin
│   ├── config.py            # Settings (pydantic-settings) leídos de .env
│   ├── database.py          # Motor SQLAlchemy y sesión
│   ├── seed.py              # Datos de demostración (idempotente)
│   ├── auth/                # Hash de contraseñas, JWT y dependencias RBAC
│   ├── models/              # Modelos SQLAlchemy
│   │   ├── user.py          #   usuarios y roles
│   │   ├── client.py        #   clientes (con geocodificación)
│   │   ├── order.py         #   pedidos, ventanas de tiempo y notas
│   │   ├── vehicle.py       #   flota
│   │   ├── depot.py         #   depósitos (uno marcado is_default)
│   │   ├── route.py         #   rutas, geometría e instrucciones
│   │   ├── route_stop.py    #   paradas de una ruta
│   │   └── audit_log.py     #   bitácora de acciones
│   ├── schemas/             # Validación de entrada/salida con Pydantic
│   ├── routers/             # Endpoints agrupados por módulo
│   ├── services/
│   │   ├── optimizer.py     # VRP con OR-Tools
│   │   ├── ors_client.py    # OpenRouteService (distancias + geometría)
│   │   ├── osrm_client.py   # Respaldo sin clave cuando ORS no está disponible
│   │   ├── geo.py           # Haversine y factor de corrección de calles
│   │   ├── metrics.py       # Ahorro de combustible y costo
│   │   └── audit.py         # Registro de auditoría
├── alembic/                 # Migraciones
├── scripts/
│   └── backfill_routes_geometry.py   # Regenera la geometría de rutas existentes
├── tests/                   # Pruebas de la API y del solver
├── alembic.ini
├── pytest.ini
├── requirements.txt
└── Dockerfile
```

## Depósito principal (único)

Todas las rutas arrancan y terminan en el **depósito principal**, que es el
registro de `depots` con `is_default = true`. Es el único punto de partida del
sistema: el modelo de OR-Tools usa un solo nodo de depósito como inicio y fin de
todas las rutas, sin importar el `depot_id` de cada vehículo.

La API garantiza que solo un depósito esté marcado como principal: al dar de
alta o editar un depósito con `is_default`, se desmarcan los demás
(`routers/depots.py`). Las rutas ya existentes pueden tener `depot_id` nulo o
apuntar a un depósito borrado, por lo que la resolución de coordenadas cae al
depósito principal y, en último caso, a `DEPOT_LAT`/`DEPOT_LNG` de la
configuración (`_resolve_depot_coords` en `routers/routes.py`).

Si borras el depósito principal, primero marca otro como principal con
`PUT /api/depots/{id}/set-default`: sin uno, el optimizador responde con
`success: false` en lugar de fallar.

## Optimización de rutas

`POST /api/routes/optimize` resuelve un **VRP con capacidad y ventanas de
tiempo** (CVRP + Time Windows) con OR-Tools:

- Asigna pedidos a varios vehículos respetando la capacidad en kg.
- Respeta la ventana de tiempo de cada pedido.
- Un pedido que no cabe por capacidad u horario no rompe la ejecución: se
  devuelve en `unassigned_order_ids` con respuesta **HTTP 200**, no un 500.

```json
// Solicitud
{ "order_ids": [1, 2, 3], "vehicle_ids": [1, 2] }
```

La respuesta trae las rutas generadas (una por vehículo usado),
`unassigned_order_ids`, `success`, `message` y `metrics` con la distancia antes
y después, el porcentaje de reducción y el ahorro estimado.

### Distancias: ORS, OSRM o Haversine

Las distancias entre paradas se resuelven en este orden:

1. **OpenRouteService** si `ORS_API_KEY` tiene valor. Aporta distancias reales y
   la geometría por calle con instrucciones de manejo.
2. **OSRM** (`router.project-osrm.org`) como respaldo sin clave, por ejemplo
   cuando el perfil `driving-hgv` de ORS exige un plan de pago.
3. **Haversine × `ROAD_DISTANCE_FACTOR`** (1.3 por defecto) si ninguna
   llamada externa responde. Es la opción con la que corren las pruebas, para
   que sean deterministas y no dependan de la red.

El perfil de ruta es `driving-hgv` (camión) y se configura con `ORS_PROFILE`.

### Geometría de ida y vuelta

La geometría que se guarda en `routes.route_geometry` cubre el viaje completo
**depósito → paradas → depósito**, no solo el tramo de salida, para que el mapa
dibuje también el regreso. `routes.steps` guarda las instrucciones de manejo y
`routes.distance_source` registra de qué proveedor vinieron las distancias
(`haversine`, `osrm` u `ors`).

Las rutas guardadas antes de este cambio solo tienen el tramo de salida. Para
regenerarlas:

```bash
source venv/bin/activate
python scripts/backfill_routes_geometry.py
```

### Rendimiento del solver

- `search_parameters.first_solution_strategy = PATH_CHEAPEST_ARC`
- `search_parameters.time_limit.seconds = 10` (tope de seguridad; en cargas
  típicas no se alcanza)

Las pruebas de rendimiento están marcadas con `@pytest.mark.performance` y se
excluyen de la corrida normal (ver `pytest.ini`):

```bash
pytest tests/test_performance.py -m performance -v
```

## Endpoints

Todos cuelgan de `/api`. El prefijo lo define cada router, así que en el
cliente se llaman **sin** `/api` duplicado (ver el `baseURL` del frontend).

| Módulo | Prefijo | Endpoints principales |
|--------|---------|----------------------|
| Autenticación | `/api/auth` | `POST /login`, `POST /register`, `POST /refresh`, `POST /logout` |
| Usuarios | `/api/users` | `GET /`, `GET /me`, `POST /`, `GET/PUT/PATCH/DELETE /{id}`, `PATCH /{id}/status` |
| Pedidos | `/api/orders` | `GET /`, `GET/PUT/DELETE /{id}`, `POST /`, `POST /upload` |
| Vehículos | `/api/vehicles` | `GET /`, `GET/POST /`, `GET/PUT/DELETE /{id}` |
| Depósitos | `/api/depots` | `GET /`, `POST /`, `PUT/DELETE /{id}`, `PUT /{id}/set-default` |
| Clientes | `/api/clients` | `GET /`, `GET /nearby`, `GET/POST /`, `GET/PUT/DELETE /{id}` |
| Rutas | `/api/routes` | `GET /`, `GET /my-route`, `GET /{id}`, `POST /optimize`, `PUT /{id}/assign-driver` |
| Paradas | `/api/route-stops` | `PUT /{id}/status` |
| Dashboard | `/api/dashboard` | `GET /summary`, `GET /kpis`, `GET /kpis/timeseries`, `GET /export` |
| Geocoding | `/api/geocode` | `GET /` |
| Auditoría | `/api/logs` | `GET /` |

`GET /api/dashboard/export` acepta `format=xlsx|pdf` más `date_from` y
`date_to`, y responde un archivo binario con `Content-Disposition`.

La referencia completa e interactiva está en `/docs`.

## Ventanas de tiempo y notas de los pedidos

Las ventanas de entrega se guardan en **minutos desde las 00:00** (p. ej.
14:00 → 840) porque es lo que consume el solver. El rango válido es 0-1440 y
`OrderCreate` valida además que la ventana termine después de empezar: una
ventana invertida se rechaza en la API en lugar de llegar al solver.

Las notas de entrega se guardan en `orders.notes` y además se exponen en cada
parada de la ruta (`RouteStop.notes` → `RouteStopOut.notes`) para que el
conductor las lea en su app sin una petición extra. Un pedido sin notas
devuelve cadena vacía, nunca `null`.

## Variables de entorno

El backend lee **`backend/.env`** (no el de la raíz, que es el de Docker). Los
nombres exactos son los campos de `app/config.py`:

```env
# Base de datos
DATABASE_URL=postgresql://optirutas:optirutas_secret@localhost:5432/optirutas_jalapa

# JWT
SECRET_KEY=cambia-este-secreto-en-produccion
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7

# App y CORS (orígenes separados por coma; nunca "*" con credenciales)
DEBUG=true
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000

# OpenRouteService (opcional) y su respaldo
ORS_API_KEY=
ORS_BASE_URL=https://api.openrouteservice.org
ORS_PROFILE=driving-hgv
ORS_TIMEOUT_SECONDS=15.0
OSRM_BASE_URL=https://router.project-osrm.org

# Optimizador / geografía
DEPOT_LAT=14.6347
DEPOT_LNG=-89.9889
DEPOT_DEPARTURE=08:00
AVERAGE_SPEED_KMH=30.0
ROAD_DISTANCE_FACTOR=1.3
MAX_TIME_PER_VEHICLE_MIN=1440
COST_PER_KM_GTQ=12.0

# Ahorro estimado
FUEL_CONSUMPTION_KM_PER_LITER=8.0
FUEL_PRICE_GTQ_PER_LITER=28.0
DRIVER_COST_GTQ_PER_HOUR=35.0
```

> `SECRET_KEY` y `ALGORITHM` son los nombres reales. Si tu `.env` los tiene como
> `JWT_SECRET_KEY` o `JWT_ALGORITHM`, no se están leyendo y la app arranca con
> los valores por defecto de desarrollo.

## Migraciones

```bash
source venv/bin/activate
alembic revision --autogenerate -m "descripcion del cambio"
alembic upgrade head
```

## Pruebas

```bash
source venv/bin/activate
pytest              # excluye las de rendimiento por defecto (pytest.ini)
pytest -v tests/test_routes.py
```

| Archivo | Cubre |
|---------|-------|
| `test_optimizer.py` | Solver: capacidad, ventanas de tiempo, depósito principal |
| `test_routes.py` | Optimización de extremo a extremo, paradas, notas, mi ruta |
| `test_vehicles.py` / `test_depots.py` | Flota y depósitos (incluido el principal) |
| `test_orders_upload.py` | Carga masiva de pedidos |
| `test_dashboard.py` | KPIs, series temporales y exportación |
| `test_clients.py` / `test_geocoding.py` | Clientes y geocodificación |
| `test_auth.py` / `test_users.py` | Login, refresh, RBAC |
| `test_audit.py` | Bitácora |
| `test_e2e_flow.py` | Flujo completo pedido → ruta → entrega |
| `test_performance.py` | Tiempos del solver (marca `performance`) |

## Troubleshooting

### Las distancias salen como `haversine` aunque configuraste ORS

Lo más común es tener la clave en el `.env` de la raíz (el de Docker) y no en
`backend/.env`, que es el que lee la app en local:

```bash
grep ORS_API_KEY backend/.env
```

Comprueba también que el perfil no exija plan de pago: `driving-hgv` en ORS
suele requerirlo, y en ese caso el sistema cae a OSRM. Fíjate en
`routes.distance_source` para saber qué proveedor se usó en cada ruta.

### `ModuleNotFoundError` al arrancar

Activa el entorno virtual antes de cualquier comando:
`source venv/bin/activate`. Los `python` del sistema no tienen las
dependencias.

### Error de conexión a PostgreSQL

```bash
# Docker
docker compose ps
docker compose logs db
# Local
pg_isready -h localhost -p 5432
```

En local, `DATABASE_URL` debe apuntar a `localhost`, no a `db` (ese hostname es
solo de la red de Docker).

### La extensión PostGIS no existe

```bash
psql -d optirutas_jalapa -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

### `OrsError` al crear una ruta

No es fatal: `routers/routes.py` captura el fallo y guarda la geometría en
línea recta para que la ruta se cree igual. Revisa los logs para ver si fue un
problema de cuota, de timeout (`ORS_TIMEOUT_SECONDS`) o de clave inválida.
