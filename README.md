# Optirutas Jalapa

**Sistema inteligente de optimización de rutas de reparto** para distribuidores de cemento en Jalapa, Guatemala.

Optirutas utiliza algoritmos avanzados de optimización (Google OR-Tools) para calcular las rutas más eficientes, reduciendo tiempo de viaje, costos de combustible y mejorando la satisfacción del cliente.

## Características principales

- **Optimización de rutas** mediante Google OR-Tools
- **Gestión de pedidos** y asignación automática a vehículos
- **Visualización en mapa** con Leaflet en tiempo real
- **Control de usuarios** con autenticación JWT y roles RBAC
- **Datos geoespaciales** con PostGIS para cálculos de distancia precisos
- **Interfaz responsiva** con diseño moderno (Tailwind CSS)
- **Modo claro y oscuro** con selector persistente en la navegación
- **Deploy simplificado** con Docker Compose

## Requisitos del sistema

- **Docker** 20.10+ y **Docker Compose** 2.0+
- **Python** 3.10+ (para desarrollo local)
- **Node.js** 16+ (para desarrollo frontend)
- **PostgreSQL** 15 (incluido en Docker Compose)
- **4GB RAM** mínimo

## Instalación rápida

### Opción 1: Con Docker Compose (Recomendado)

```bash
# 1. Clonar el repositorio
git clone <repo-url> && cd optirutas-jalapa

# 2. Configurar variables de entorno
cp .env.example .env

# 3. Levantar contenedores
docker compose up --build

# 4. Acceder a la aplicación
# Frontend:  http://localhost:5173
# API Docs:  http://localhost:8000/docs
# API Health: http://localhost:8000/health
```

### Opción 2: Desarrollo local (BD local por defecto)

Usa el PostgreSQL instalado en tu sistema (no Docker). El archivo
`backend/.env` ya apunta a `localhost`:

```bash
# 1. Preparar la base de datos local (solo la primera vez)
sudo -u postgres psql -c "CREATE USER optirutas WITH PASSWORD 'optirutas_secret' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE optirutas_jalapa OWNER optirutas;"

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Frontend (en otra terminal)
cd frontend
npm install
npm run dev
```

Al arrancar, el backend crea automáticamente las tablas y el usuario
`admin`. No es necesario levantar el contenedor `db` de Docker.

## Datos de demostración (seed)

El sistema arranca creando automáticamente el usuario `admin`. Para cargar un
set de datos realistas de Jalapa (4 usuarios por rol, ~30 clientes, 5
vehículos, ~100 pedidos y 20 rutas optimizadas) y poder ver el dashboard del
Gerente desde el primer arranque, ejecuta:

```bash
cd backend
source venv/bin/activate  # o venv\Scripts\activate en Windows
python -m app.seed
```

El seed es **idempotente**: correrlo varias veces no duplica datos.

Credenciales de demostración:

| Rol | Email | Contraseña |
|-----|-------|------------|
| Administrador | `admin@optirutas.com` | `Admin123!` |
| Planificador | `planificador@optirutas.com` | `Planif123!` |
| Conductor | `conductor@optirutas.com` | `Conduc123!` |
| Gerente | `gerente@optirutas.com` | `Gerente123!` |

## Estructura del proyecto

```
optirutas-jalapa/
├── backend/                       # API FastAPI
│   ├── app/
│   │   ├── auth/                 # Autenticación JWT y RBAC
│   │   ├── models/               # Modelos SQLAlchemy
│   │   │   ├── user.py           #   usuarios y roles
│   │   │   ├── client.py         #   clientes
│   │   │   ├── order.py          #   pedidos, ventanas de tiempo y notas
│   │   │   ├── vehicle.py        #   flota
│   │   │   ├── depot.py          #   depósitos
│   │   │   ├── route.py          #   rutas, geometría e instrucciones
│   │   │   ├── route_stop.py     #   paradas de una ruta
│   │   │   └── audit_log.py      #   bitácora
│   │   ├── schemas/              # Validación Pydantic
│   │   ├── routers/              # Endpoints API
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── orders.py
│   │   │   ├── vehicles.py
│   │   │   ├── depots.py
│   │   │   ├── clients.py
│   │   │   ├── routes.py
│   │   │   ├── route_stops.py
│   │   │   ├── dashboard.py
│   │   │   ├── geocoding.py
│   │   │   └── audit.py
│   │   ├── services/             # Lógica de negocio
│   │   │   ├── optimizer.py      # OR-Tools: VRP con capacidad y ventanas
│   │   │   ├── ors_client.py     # OpenRouteService (distancias + geometría)
│   │   │   ├── osrm_client.py    # Respaldo sin API key
│   │   │   ├── geo.py            # Haversine y corrección de calles
│   │   │   ├── metrics.py        # Ahorro de combustible
│   │   │   └── audit.py
│   │   ├── seed.py               # Datos de demostración
│   │   ├── config.py             # Configuración
│   │   ├── database.py           # Conexión DB
│   │   └── main.py               # Aplicación principal
│   ├── alembic/                  # Migraciones de base de datos
│   ├── scripts/
│   │   └── backfill_routes_geometry.py  # Regenera geometría de rutas
│   ├── tests/                    # Pruebas de API y del solver
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md                 # Detalles del backend
├── frontend/                      # Aplicación React + Vite
│   ├── src/
│   │   ├── components/           # Componentes reutilizables
│   │   │   ├── MapView.jsx
│   │   │   ├── Navbar.jsx
│   │   │   ├── StatCard.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── context/              # Context API
│   │   │   ├── AuthContext.jsx
│   │   │   └── ThemeContext.jsx
│   │   ├── pages/                # Páginas
│   │   │   ├── LoginPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── OrdersPage.jsx
│   │   │   ├── RoutesPage.jsx
│   │   │   ├── MapPage.jsx
│   │   │   ├── MyRoutePage.jsx
│   │   │   ├── VehiclesPage.jsx
│   │   │   ├── DepotsPage.jsx
│   │   │   ├── ManagerDashboardPage.jsx
│   │   │   └── ...
│   │   ├── services/             # API client
│   │   │   └── api.js
│   │   ├── index.css
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── scripts/                  # Utilidades de mantenimiento del tema
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── README.md                 # Detalles del frontend
├── data/                         # Datos de prueba
│   └── pedidos_jalapa.csv
├── docker-compose.yml
├── .env.example
├── README.md
└── .gitignore
```

## Optimización de rutas (Sprint 3)

El motor de optimización (`backend/app/services/optimizer.py`) resuelve un
**VRP con capacidad y ventanas de tiempo** (CVRP + Time Windows) usando
Google OR-Tools. A diferencia del TSP de un solo vehículo original, ahora:

- Se asignan pedidos a **varios vehículos** respetando la capacidad en kg.
- Se respetan las **ventanas de tiempo** de entrega de cada pedido.
- Si un pedido no cabe por capacidad u horario, **no rompe la ruta**: se
  devuelve en `unassigned_order_ids` para que el usuario vea qué falló
  (respuesta HTTP 200, no un 500).
- Todas las rutas arrancan y terminan en el **depósito principal** del sistema
  (el registro de `depots` con `is_default = true`), que es el único punto de
  partida. El modelo usa un solo nodo de depósito, sin importar el `depot_id`
  de cada vehículo.
- La geometría por calle cubre el viaje completo **depósito → paradas →
  depósito**, para que el mapa dibuje también el regreso.

### Depósito principal

El depósito marcado como principal se puede cambiar desde la interfaz
(Pantalla de Depósitos) o con `PUT /api/depots/{id}/set-default`. La API
garantiza que solo uno esté marcado: al activar uno, desmarca los demás.

Las rutas ya existentes pueden tener `depot_id` nulo o apuntar a un depósito
borrado, así que la resolución de coordenadas cae al depósito principal y, en
último caso, a la coordenada de configuración. Para regenerar la geometría de
esas rutas con el viaje completo de ida y vuelta:

```bash
cd backend && source venv/bin/activate
python scripts/backfill_routes_geometry.py
```

### Decisión técnica: OSRM vs Haversine corregido

Para calcular distancias se usa **distancia Haversine (línea recta)
multiplicada por un factor de corrección de calles** (por defecto `× 1.3`),
configurable vía `ROAD_DISTANCE_FACTOR`. Se eligió esta opción por:

- **Simplicidad de despliegue**: no requiere levantar un servidor OSRM.
- **Alcance de tesis**: es suficiente y defendible para zonas urbanas.
- **Determinismo**: reproducible en pruebas sin dependencia de red.

Si hay clave de **OpenRouteService** (`ORS_API_KEY`), el sistema la usa para
obtener distancias reales y la geometría por calle con instrucciones de
manejo. Si la clave falta, no es válida o el perfil `driving-hgv` exige un plan
de pago, cae a **OSRM** (`router.project-osrm.org`) y, en último caso, a
Haversine. El origen de las distancias de cada ruta queda registrado en
`routes.distance_source` (`haversine`, `osrm` u `ors`).

La configuración relacionada vive en `app/config.py` (velocidad promedio, hora
de salida, costo por km, etc.).

### Endpoint de optimización

Se mantiene **`POST /api/routes/optimize`** (más RESTful que `/api/optimize`).
Solicitud:

```json
{ "order_ids": [1, 2, 3], "vehicle_ids": [1, 2] }
```

Respuesta: lista de rutas (una por vehículo usado), `unassigned_order_ids`,
`success`, `message` y `metrics` (distancias antes/después, % de reducción y
ahorro estimado de combustible).

### Persistencia de paradas

Las paradas se persisten en la tabla **`route_stops`** (una fila por parada
en una ruta), consultables desde la relación `Route.stops`. La columna
`routes.stops` (JSON) se conserva como *snapshot* por compatibilidad con el
frontend antiguo y se eliminará en Sprint 4.

### Rendimiento del solver (PG-25)

El objetivo del criterio de aceptación es **resolver 50 pedidos en menos de
5 segundos**. Se mide el tiempo real del endpoint `POST /api/routes/optimize`
(incluyendo latencia HTTP y persistencia en BD), no solo el `time_limit` interno.

Configuración del solver (`backend/app/services/optimizer.py`):

- `search_parameters.first_solution_strategy = PATH_CHEAPEST_ARC`
- `search_parameters.time_limit.seconds = 10` (límite superior de seguridad,
  se alcanza raramente en las cargas típicas)

**Mediciones reales** (pruebas marcadas `@pytest.mark.performance` en
`backend/tests/test_performance.py`, excluidas de la corrida normal de CI):

| Escenario | Pedidos | Vehículos | Tiempo real | ¿Objetivo <5s? |
|-----------|---------|-----------|-------------|----------------|
| Carga pequeña | 50 | 5 | ~0.2 s | ✅ |
| Carga grande | 100 | 10 | ~1.0 s | ✅ |

Para reproducirlas localmente:

```bash
cd backend && source venv/bin/activate
pytest tests/test_performance.py -m performance -v
```

Hardware / entorno donde se midieron: desarrollo local, Python 3.12, sin
limitaciones de contenedor. Los tiempos pueden variar según la máquina; el
`time_limit.seconds = 10` actúa como tope de seguridad para la búsqueda de
mejora.

## Autenticación y Roles (RBAC)

| Rol | Descripción | Permisos principales |
|-----|-------------|----------------------|
| **admin** | Administrador system | CRUD completo, gestión de usuarios, configuración |
| **planificador** | Planificador de rutas | Crear/editar pedidos, optimizar rutas, ver analytics |
| **conductor** | Conductor del vehículo | Ver rutas asignadas, actualizar estado de entrega |
| **gerente** | Gerente de operaciones | Ver dashboards, reportes, listar usuarios |

## Modo oscuro

Toda la interfaz funciona en tema claro y oscuro, con un selector en la barra de
navegación.

- La elección se guarda en `localStorage` y se respeta entre visitas. En la
  primera carga, si el usuario nunca ha elegido, se sigue la preferencia del
  sistema (`prefers-color-scheme`).
- Las 13 páginas, sus componentes y el layout raíz tienen sus variantes `dark:`,
  incluidas tablas, formularios, modales y estados vacíos.
- El **mapa** se adapta sin cambiar de proveedor: se mantiene OpenStreetMap
  (que no pide API key) y se oscurece la capa de tiles con un filtro CSS, de
  modo que los marcadores y las polilíneas conservan sus colores. Los popups y
  los controles de zoom siguen el tema.

Detalle de implementación, tabla de traducción de colores y los scripts para
aplicar el tema a vistas nuevas: [frontend/README.md](./frontend/README.md).

## Pedidos: ventanas de entrega y notas

- Las ventanas de entrega se capturan en la interfaz como **HH:MM** y se
  guardan en la base de datos en **minutos desde las 00:00** (14:00 → 840),
  que es lo que consume el solver. La API acota el rango a 0-1440 y rechaza
  ventanas cuyo fin no sea posterior al inicio.
- Las **notas de entrega** (instrucciones de acceso, contacto, etc.) se escriben
  al crear el pedido y se muestran en la lista de pedidos, en la ruta del
  conductor y en el popup del mapa.

## Stack tecnológico

| Aspecto | Tecnologías |
|--------|------------|
| **Backend API** | FastAPI, Uvicorn, Pydantic |
| **ORM & BD** | SQLAlchemy, GeoAlchemy2, PostgreSQL 15, PostGIS |
| **Optimización** | Google OR-Tools, Python 3.10+ |
| **Rutas por calle** | OpenRouteService (opcional), OSRM como respaldo |
| **Migraciones** | Alembic |
| **Frontend** | React 18, Vite 5 |
| **Estilos** | Tailwind CSS 3, PostCSS |
| **Navegación** | React Router 6 |
| **Mapeo** | Leaflet.js, react-leaflet |
| **Gráficas** | Chart.js, react-chartjs-2 |
| **API Client** | Axios |
| **Seguridad** | JWT (access + refresh), bcrypt |
| **Infra** | Docker Compose, Docker |

## Endpoints principales de API

Todos cuelgan de `/api`. La referencia completa e interactiva está en
http://localhost:8000/docs (Swagger UI).

### Autenticación
- `POST /api/auth/login` - Iniciar sesión
- `POST /api/auth/register` - Registro de usuario
- `POST /api/auth/refresh` - Refrescar token
- `POST /api/auth/logout` - Cerrar sesión

### Usuarios
- `GET /api/users` - Listar usuarios
- `GET /api/users/me` - Usuario de la sesión actual
- `GET /api/users/{user_id}` - Obtener usuario
- `PUT /api/users/{user_id}` - Actualizar usuario
- `PATCH /api/users/{user_id}/status` - Activar / desactivar
- `DELETE /api/users/{user_id}` - Eliminar usuario

### Pedidos
- `GET /api/orders` - Listar pedidos
- `POST /api/orders` - Crear pedido
- `POST /api/orders/upload` - Carga masiva (CSV)
- `GET /api/orders/{order_id}` - Obtener pedido
- `PUT /api/orders/{order_id}` - Actualizar pedido
- `DELETE /api/orders/{order_id}` - Eliminar pedido

### Rutas & Optimización
- `GET /api/routes` - Listar rutas
- `GET /api/routes/my-route` - Ruta asignada al conductor
- `POST /api/routes/optimize` - Optimizar rutas (OR-Tools)
- `GET /api/routes/{route_id}` - Obtener ruta con sus paradas
- `PUT /api/routes/{route_id}/assign-driver` - Asignar conductor
- `PUT /api/route-stops/{stop_id}/status` - Marcar parada como entregada

### Vehículos, depósitos y clientes
- `GET|POST /api/vehicles` - Listar / crear vehículo
- `PUT|DELETE /api/vehicles/{vehicle_id}` - Actualizar / eliminar
- `GET|POST /api/depots` - Listar / crear depósito
- `PUT /api/depots/{depot_id}/set-default` - Marcar el depósito principal
- `GET /api/clients` - Listar clientes
- `GET /api/clients/nearby` - Clientes cercanos a un punto
- `GET /api/geocode/` - Geocodificar una dirección

### Dashboard y auditoría
- `GET /api/dashboard/summary` - Resumen operativo
- `GET /api/dashboard/kpis` - KPIs del gerente
- `GET /api/dashboard/kpis/timeseries` - Series temporales
- `GET /api/dashboard/export` - Descargar reporte (`format=xlsx|pdf`)
- `GET /api/logs` - Bitácora de acciones

## Variables de entorno

El punto de partida es `.env.example`. Copiar a `.env` y configurar:

```env
# Base de datos (docker compose)
DATABASE_URL=postgresql://optirutas:optirutas_secret@db:5432/optirutas_jalapa
POSTGRES_USER=optirutas
POSTGRES_PASSWORD=optirutas_secret
POSTGRES_DB=optirutas_jalapa

# Seguridad JWT
SECRET_KEY=cambia-este-secreto-en-produccion
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7

# App y CORS
DEBUG=true
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000

# OpenRouteService (opcional) y su respaldo sin clave
ORS_API_KEY=
ORS_BASE_URL=https://api.openrouteservice.org
ORS_PROFILE=driving-hgv
OSRM_BASE_URL=https://router.project-osrm.org

# Optimizador / geografía
DEPOT_LAT=14.6347
DEPOT_LNG=-89.9889
DEPOT_DEPARTURE=08:00
ROAD_DISTANCE_FACTOR=1.3
```

> **Nota**: hay dos archivos de entorno con propósitos distintos. El de la
> **raíz** es el que usa Docker Compose; el **backend** lee `backend/.env`
> (también lo usa Alembic en local). En desarrollo local
> `backend/.env` debe apuntar a `localhost`, no a `db`, y es el que necesita la
> `ORS_API_KEY` para que las distancias salgan reales.

> `SECRET_KEY` y `ALGORITHM` son los nombres reales que lee `app/config.py`. Si
> tu `.env` los tiene como `JWT_SECRET_KEY` o `JWT_ALGORITHM`, no se están
> usando y la app arranca con los valores de desarrollo.

La lista completa de variables está en
[backend/README.md](./backend/README.md#variables-de-entorno).

> **Frontend**: no hay variables de entorno que configurar. La URL de la API es
> fija (`/api`) y en desarrollo la resuelve el proxy de `vite.config.js` contra
> `http://localhost:8000`.

## Testing

```bash
# Backend (los tests de rendimiento están excluidos por defecto)
cd backend
source venv/bin/activate
pytest

# Tests de rendimiento del solver, opcionalmente
pytest tests/test_performance.py -m performance -v
```

El frontend no tiene suite de pruebas automatizadas ni script de lint: se
verifica compilando con `npm run build`.

## Troubleshooting

### Error de conexión a PostgreSQL
```
Solución: Verificar que docker compose está corriendo
docker compose ps
docker compose logs postgres
```

### Puerto 8000 ya en uso
```bash
# Cambiar puerto en docker-compose.yml o
lsof -i :8000  # Encontrar proceso
kill -9 <PID>
```

### Frontend no se conecta al backend

- Confirmar que el backend está corriendo: `curl http://localhost:8000/health`
- El cliente HTTP usa `baseURL: '/api'` y el proxy de `vite.config.js` lo
  redirige a `http://localhost:8000`. **No** agregues `/api` a mano en las rutas
  de las páginas, o la petición terminará en `/api/api/...`
- Si cambiaste el puerto del backend, actualiza el `target` del proxy
- Revisar CORS en `backend/app/main.py` (variable `FRONTEND_ORIGINS`)

### Las distancias salen en línea recta aunque configuraste OpenRouteService

Casi siempre es que la clave está en el `.env` de la raíz (Docker) y no en
`backend/.env`, que es el que lee la app en local:

```bash
grep ORS_API_KEY backend/.env
```

Consulta `routes.distance_source` para ver qué proveedor se usó en cada ruta.

### El mapa pide una API key o se ve en blanco

Los tiles son de OpenStreetMap y **no requieren clave**. Si aparece un aviso de
API key, se está usando un proveedor de mapas de pago: el modo oscuro ya no
cambia de proveedor justamente para evitarlo. Revisa que `MapView.jsx` siga
usando `tile.openstreetmap.org`.

### La interfaz se ve clara en modo oscuro tras recargar

La clase `dark` debe aplicarse en `<html>` antes de montar React. Si alguien
movió esa lógica a un `useEffect`, la primera pintura sale en tema claro: vuelve
a ponerla en `main.jsx`, antes de `createRoot(...).render(...)`.

## Documentación adicional

- [API Docs Swagger](http://localhost:8000/docs) - Documentación interactiva
- [Backend README](./backend/README.md) - Detalles de configuración backend
- [Frontend README](./frontend/README.md) - Detalles de configuración frontend

## Contribución

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/xx`)
3. Commit tus cambios (`git commit -m 'Add some xx'`)
4. Push a la rama (`git push origin feature/xx`)
5. Abrir un Pull Request


